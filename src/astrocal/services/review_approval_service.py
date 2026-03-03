"""Promotion of reviewed eclipse content into the accepted catalog."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..errors import CliUserError
from ..hashing import sha256_text
from ..models import (
    AcceptedRecord,
    CandidateRecord,
    DESCRIPTION_PROVENANCE_KEY,
    DESCRIPTION_REVIEW_KEY,
    GENERATED_CONTENT_HASH_KEY,
)
from ..repositories import CatalogStore
from .review_query_service import load_review_bundle

REVIEW_RESOLUTIONS = {"accepted", "prose-edited", "facts-corrected"}


@dataclass(slots=True)
class ApprovalResult:
    approved_records: list[AcceptedRecord]
    catalog_path: Path


def approve_review(
    *,
    report_path: Path,
    reviewer: str,
    occurrence_ids: list[str] | None = None,
    group_ids: list[str] | None = None,
    resolution: str = "accepted",
    note: str | None = None,
    title: str | None = None,
    summary: str | None = None,
    description: str | None = None,
    catalog_store: CatalogStore | None = None,
    reviewed_at: str | None = None,
) -> ApprovalResult:
    if resolution not in REVIEW_RESOLUTIONS:
        raise CliUserError(f"Unsupported review resolution: {resolution}")

    occurrence_ids = occurrence_ids or []
    group_ids = group_ids or []
    if not occurrence_ids and not group_ids:
        raise CliUserError("Specify at least one occurrence ID or group ID to approve")

    bundle = load_review_bundle(report_path)
    selected_entries = [
        entry
        for entry in bundle.entries
        if entry.occurrence_id in occurrence_ids or entry.group_id in group_ids
    ]
    if not selected_entries:
        raise CliUserError("No matching review entries found")

    if any([title, summary, description]) and len(selected_entries) != 1:
        raise CliUserError("Prose overrides require exactly one selected review entry")
    if any([title, summary, description]) and group_ids:
        raise CliUserError("Group approval does not support per-entry prose overrides")

    reviewed_at = reviewed_at or _reviewed_at()
    catalog_store = catalog_store or CatalogStore()
    source_name = selected_entries[0].source_name
    accepted_records = catalog_store.load("astronomy", bundle.year, source_name)
    approved_records: list[AcceptedRecord] = []

    for entry in selected_entries:
        if entry.candidate is None:
            if entry.status == "suspected-removed":
                raise CliUserError(
                    f"Review entry {entry.occurrence_id} is a suspected removal and "
                    "cannot be approved with approve-review"
                )
            raise CliUserError(
                f"Review entry {entry.occurrence_id} has no candidate payload and "
                "cannot be approved with approve-review"
            )
        if entry.source_name != source_name:
            raise CliUserError("Approving multiple source files in one command is not supported")

        current = _current_active_record(accepted_records, entry.occurrence_id)
        _validate_review_entry_is_current(entry, current)

        if current is not None:
            current.status = "superseded"
            current.superseded_at = reviewed_at
            next_revision = current.revision + 1
        else:
            next_revision = 1

        candidate = CandidateRecord.from_dict(entry.candidate)
        final_payload = candidate.to_dict()
        if title is not None:
            final_payload["title"] = title
        if summary is not None:
            final_payload["summary"] = summary
        if description is not None:
            final_payload["description"] = description

        final_payload["accepted_revision"] = next_revision
        final_payload["candidate_status"] = "accepted"
        metadata = final_payload.setdefault("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
            final_payload["metadata"] = metadata
        provenance = metadata.get(DESCRIPTION_PROVENANCE_KEY, {})
        if not isinstance(provenance, dict):
            provenance = {}
        provenance[GENERATED_CONTENT_HASH_KEY] = candidate.content_hash
        metadata[DESCRIPTION_PROVENANCE_KEY] = provenance
        metadata[DESCRIPTION_REVIEW_KEY] = {
            "status": "accepted",
            "reviewed_at": reviewed_at,
            "reviewer": reviewer,
            "edited": any(value is not None for value in (title, summary, description)),
            "resolution": resolution,
            "note": note,
        }

        content_hash = _accepted_content_hash(final_payload)
        final_payload["content_hash"] = content_hash
        approved_record = AcceptedRecord(
            occurrence_id=candidate.occurrence_id,
            revision=next_revision,
            status="active",
            accepted_at=reviewed_at,
            superseded_at=None,
            change_reason=_approval_change_reason(current is None, resolution),
            content_hash=content_hash,
            source_adapter=candidate.source_adapter,
            detail_url=candidate.detail_url,
            record=final_payload,
        )
        accepted_records.append(approved_record)
        approved_records.append(approved_record)

    accepted_records.sort(key=lambda record: (record.occurrence_id, record.revision))
    catalog_path = catalog_store.save("astronomy", bundle.year, source_name, accepted_records)
    return ApprovalResult(approved_records=approved_records, catalog_path=catalog_path)


def _current_active_record(
    accepted_records: list[AcceptedRecord],
    occurrence_id: str,
) -> AcceptedRecord | None:
    active = [
        record
        for record in accepted_records
        if record.occurrence_id == occurrence_id and record.status == "active"
    ]
    if not active:
        return None
    return max(active, key=lambda record: record.revision)


def _validate_review_entry_is_current(
    entry,
    current: AcceptedRecord | None,
) -> None:
    if entry.accepted is None:
        if current is not None:
            raise CliUserError(f"Review entry {entry.occurrence_id} is stale")
        return

    if current is None:
        raise CliUserError(f"Review entry {entry.occurrence_id} is stale")
    accepted_revision = entry.accepted.get("revision")
    accepted_hash = entry.accepted.get("content_hash")
    if current.revision != accepted_revision or current.content_hash != accepted_hash:
        raise CliUserError(f"Review entry {entry.occurrence_id} is stale")


def _accepted_content_hash(payload: dict[str, object]) -> str:
    copy = json.loads(json.dumps(payload))
    copy["content_hash"] = ""
    metadata = copy.get("metadata", {})
    if isinstance(metadata, dict):
        provenance = metadata.get(DESCRIPTION_PROVENANCE_KEY)
        if isinstance(provenance, dict):
            provenance["generated_at"] = ""
        review = metadata.get(DESCRIPTION_REVIEW_KEY)
        if isinstance(review, dict):
            review["reviewed_at"] = ""
    return sha256_text(json.dumps(copy, sort_keys=True))


def _approval_change_reason(is_new: bool, resolution: str) -> str:
    if is_new:
        return "Accepted after review"
    if resolution == "prose-edited":
        return "Approved reviewed prose edits"
    if resolution == "facts-corrected":
        return "Approved corrected review facts"
    return "Approved reviewed content"


def _reviewed_at() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
