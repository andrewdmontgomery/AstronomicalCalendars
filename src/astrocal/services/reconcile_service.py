"""Reconciliation between normalized candidates and accepted catalog records."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..adapters import ASTRONOMY_ADAPTERS
from ..models import (
    AcceptedRecord,
    CalendarManifest,
    CandidateRecord,
    DESCRIPTION_PROVENANCE_KEY,
    DESCRIPTION_REVIEW_KEY,
    GENERATED_CONTENT_HASH_KEY,
    ReconciliationReport,
    ReviewBundle,
    ReviewBundleEntry,
)
from ..repositories import CandidateStore, CatalogStore, ReportStore
from ..source_scope import manifest_source_names
from .review_report_service import render_review_report


@dataclass(slots=True)
class SourceReconciliation:
    reconciled_records: list[AcceptedRecord]
    new_candidates: list[CandidateRecord] = field(default_factory=list)
    unchanged_occurrence_ids: list[str] = field(default_factory=list)
    changed_pairs: list[tuple[AcceptedRecord, CandidateRecord]] = field(default_factory=list)
    suspected_removals: list[AcceptedRecord] = field(default_factory=list)


def reconcile_calendar(
    *,
    manifest: CalendarManifest,
    year: int,
    candidate_store: CandidateStore | None = None,
    catalog_store: CatalogStore | None = None,
    report_store: ReportStore | None = None,
    run_timestamp: str | None = None,
) -> tuple[ReconciliationReport, list[Path]]:
    candidate_store = candidate_store or CandidateStore()
    catalog_store = catalog_store or CatalogStore()
    report_store = report_store or ReportStore()
    run_timestamp = run_timestamp or _run_timestamp()

    candidates_by_source = _load_relevant_candidates(
        manifest=manifest,
        year=year,
        candidate_store=candidate_store,
    )
    filtered_candidates_by_source = {
        source_name: _filter_candidates(manifest, candidates)
        for source_name, candidates in candidates_by_source.items()
    }

    report = ReconciliationReport(
        calendar_name=manifest.name,
        year=year,
        generated_at=run_timestamp,
    )
    validation_failures = [
        source_name
        for source_name, candidates in filtered_candidates_by_source.items()
        if _has_validation_failure(candidates)
    ]
    report.validation_failures.extend(validation_failures)

    if validation_failures:
        report_name = f"reconcile.{manifest.name}"
        json_path = report_store.write_json_report(run_timestamp, report_name, report.to_dict())
        return report, [json_path]

    catalog_paths: list[Path] = []
    eclipse_new_candidates: list[CandidateRecord] = []
    eclipse_changed_pairs: list[tuple[AcceptedRecord, CandidateRecord]] = []
    eclipse_suspected_removals: list[AcceptedRecord] = []

    for source_name, candidates in filtered_candidates_by_source.items():
        accepted_records = catalog_store.load("astronomy", year, source_name)
        reconciliation = _reconcile_source_records(
            candidates=candidates,
            accepted_records=accepted_records,
            accepted_at=run_timestamp,
        )
        report.new_occurrences.extend(
            candidate.occurrence_id for candidate in reconciliation.new_candidates
        )
        report.unchanged_occurrences.extend(reconciliation.unchanged_occurrence_ids)
        report.changed_occurrences.extend(
            candidate.occurrence_id for _, candidate in reconciliation.changed_pairs
        )
        report.suspected_removals.extend(
            record.occurrence_id for record in reconciliation.suspected_removals
        )

        if source_name == "eclipses":
            eclipse_new_candidates.extend(reconciliation.new_candidates)
            eclipse_changed_pairs.extend(reconciliation.changed_pairs)
            eclipse_suspected_removals.extend(reconciliation.suspected_removals)
            continue

        saved_path = catalog_store.save(
            "astronomy",
            year,
            source_name,
            reconciliation.reconciled_records,
        )
        catalog_paths.append(saved_path)

    written_paths = list(catalog_paths)
    if eclipse_new_candidates or eclipse_changed_pairs or eclipse_suspected_removals:
        review_bundle = _build_review_bundle(
            manifest=manifest,
            year=year,
            new_candidates=eclipse_new_candidates,
            changed_pairs=eclipse_changed_pairs,
            suspected_removals=eclipse_suspected_removals,
            generated_at=run_timestamp,
        )
        review_bundle_path = report_store.write_json_report(
            run_timestamp,
            f"review.{manifest.name}",
            review_bundle.to_dict(),
        )
        review_report = render_review_report(
            manifest=manifest,
            year=year,
            new_candidates=eclipse_new_candidates,
            changed_pairs=eclipse_changed_pairs,
            suspected_removals=eclipse_suspected_removals,
        )
        review_path = report_store.write_text_report(
            run_timestamp,
            f"review.{manifest.name}",
            review_report,
        )
        report.review_report_path = str(review_path)
        report.review_bundle_path = str(review_bundle_path)
        written_paths.append(review_bundle_path)
        written_paths.append(review_path)

    report_name = f"reconcile.{manifest.name}"
    json_path = report_store.write_json_report(run_timestamp, report_name, report.to_dict())
    written_paths.append(json_path)

    return report, written_paths


def _load_relevant_candidates(
    *,
    manifest: CalendarManifest,
    year: int,
    candidate_store: CandidateStore,
) -> dict[str, list[CandidateRecord]]:
    result: dict[str, list[CandidateRecord]] = {}
    if "astronomy" in manifest.source_types or not manifest.source_types:
        for source_name in manifest_source_names(manifest, list(ASTRONOMY_ADAPTERS)):
            result[source_name] = candidate_store.load("astronomy", year, source_name)
    return result


def _filter_candidates(
    manifest: CalendarManifest,
    candidates: list[CandidateRecord],
) -> list[CandidateRecord]:
    filtered = []
    for candidate in candidates:
        if manifest.event_types and candidate.event_type not in manifest.event_types:
            continue
        if manifest.bodies and candidate.body not in manifest.bodies:
            continue
        if manifest.tags and not set(candidate.tags).intersection(manifest.tags):
            continue
        filtered.append(candidate)
    return filtered


def _has_validation_failure(candidates: list[CandidateRecord]) -> bool:
    return any(
        candidate.source_validation is not None
        and candidate.source_validation.status != "passed"
        for candidate in candidates
    )


def _reconcile_source_records(
    *,
    candidates: list[CandidateRecord],
    accepted_records: list[AcceptedRecord],
    accepted_at: str,
) -> SourceReconciliation:
    accepted_records = [AcceptedRecord.from_dict(record.to_dict()) for record in accepted_records]
    accepted_by_occurrence: dict[str, list[AcceptedRecord]] = defaultdict(list)
    for record in accepted_records:
        accepted_by_occurrence[record.occurrence_id].append(record)

    latest_by_occurrence = {
        occurrence_id: max(records, key=lambda record: record.revision)
        for occurrence_id, records in accepted_by_occurrence.items()
    }

    result = SourceReconciliation(reconciled_records=list(accepted_records))
    current_candidate_ids = {candidate.occurrence_id for candidate in candidates}

    for candidate in candidates:
        current = latest_by_occurrence.get(candidate.occurrence_id)
        if current is None:
            result.reconciled_records.append(
                AcceptedRecord(
                    occurrence_id=candidate.occurrence_id,
                    revision=1,
                    status="active",
                    accepted_at=accepted_at,
                    superseded_at=None,
                    change_reason="Initial acceptance",
                    content_hash=candidate.content_hash,
                    source_adapter=candidate.source_adapter,
                    detail_url=candidate.detail_url,
                    record=candidate.to_dict(),
                )
            )
            result.new_candidates.append(candidate)
            continue

        if current.content_hash == candidate.content_hash and current.status == "active":
            result.unchanged_occurrence_ids.append(candidate.occurrence_id)
            continue

        if _matches_reviewed_eclipse_candidate(current, candidate):
            result.unchanged_occurrence_ids.append(candidate.occurrence_id)
            continue

        previous = AcceptedRecord.from_dict(current.to_dict())
        current.status = "superseded"
        current.superseded_at = accepted_at
        new_revision = current.revision + 1
        result.reconciled_records.append(
            AcceptedRecord(
                occurrence_id=candidate.occurrence_id,
                revision=new_revision,
                status="active",
                accepted_at=accepted_at,
                superseded_at=None,
                change_reason=_change_reason(current, candidate),
                content_hash=candidate.content_hash,
                source_adapter=candidate.source_adapter,
                detail_url=candidate.detail_url,
                record=candidate.to_dict(),
            )
        )
        result.changed_pairs.append((previous, candidate))

    for occurrence_id, current in latest_by_occurrence.items():
        if occurrence_id in current_candidate_ids:
            continue
        if current.status != "active":
            continue
        current.status = "suspected-removed"
        current.superseded_at = accepted_at
        current.change_reason = "Missing from current candidate set"
        result.suspected_removals.append(AcceptedRecord.from_dict(current.to_dict()))

    result.reconciled_records = sorted(
        result.reconciled_records,
        key=lambda record: (record.occurrence_id, record.revision),
    )
    return result


def _change_reason(current: AcceptedRecord, candidate: CandidateRecord) -> str:
    changed_fields: list[str] = []
    previous = current.record
    current_record = candidate.to_dict()
    for field in ("start", "end", "title", "summary", "description", "detail_url"):
        if previous.get(field) != current_record.get(field):
            changed_fields.append(field)
    if not changed_fields:
        return "Content hash changed"
    return f"Updated {', '.join(changed_fields)}"


def _build_review_bundle(
    *,
    manifest: CalendarManifest,
    year: int,
    new_candidates: list[CandidateRecord],
    changed_pairs: list[tuple[AcceptedRecord, CandidateRecord]],
    suspected_removals: list[AcceptedRecord],
    generated_at: str,
) -> ReviewBundle:
    entries: list[ReviewBundleEntry] = []
    for candidate in new_candidates:
        entries.append(_review_entry_for_candidate(candidate, status="new"))
    for accepted, candidate in changed_pairs:
        entries.append(_review_entry_for_candidate(candidate, status="changed", accepted=accepted))
    for accepted in suspected_removals:
        entries.append(_review_entry_for_suspected_removal(accepted))
    return ReviewBundle(
        calendar_name=manifest.name,
        year=year,
        generated_at=generated_at,
        entries=entries,
    )


def _review_entry_for_candidate(
    candidate: CandidateRecord,
    *,
    status: str,
    accepted: AcceptedRecord | None = None,
) -> ReviewBundleEntry:
    return ReviewBundleEntry(
        occurrence_id=candidate.occurrence_id,
        group_id=candidate.group_id,
        status=status,
        source_name="eclipses",
        candidate_content_hash=candidate.content_hash,
        generated_content_hash=candidate.content_hash,
        allowed_actions=[
            "approve-as-is",
            "approve-with-prose-edits",
            "approve-with-fact-corrections",
        ],
        candidate=candidate.to_dict(),
        accepted=accepted.to_dict() if accepted is not None else None,
    )


def _review_entry_for_suspected_removal(accepted: AcceptedRecord) -> ReviewBundleEntry:
    group_id = str(accepted.record.get("group_id", accepted.occurrence_id.rsplit("/", 1)[0]))
    return ReviewBundleEntry(
        occurrence_id=accepted.occurrence_id,
        group_id=group_id,
        status="suspected-removed",
        source_name="eclipses",
        candidate_content_hash=None,
        generated_content_hash=_accepted_generated_content_hash(accepted),
        allowed_actions=["review-removal"],
        candidate=None,
        accepted=accepted.to_dict(),
    )


def _accepted_generated_content_hash(accepted: AcceptedRecord) -> str | None:
    metadata = accepted.record.get("metadata", {})
    if not isinstance(metadata, dict):
        return accepted.content_hash
    provenance = metadata.get("description_provenance", {})
    if not isinstance(provenance, dict):
        return accepted.content_hash
    generated_content_hash = provenance.get("generated_content_hash")
    if isinstance(generated_content_hash, str) and generated_content_hash:
        return generated_content_hash
    return accepted.content_hash


def _matches_reviewed_eclipse_candidate(
    current: AcceptedRecord,
    candidate: CandidateRecord,
) -> bool:
    if current.status != "active":
        return False
    if str(current.record.get("event_type")) != "eclipse":
        return False

    accepted_metadata = current.record.get("metadata", {})
    candidate_metadata = candidate.metadata
    if not isinstance(accepted_metadata, dict) or not isinstance(candidate_metadata, dict):
        return False

    review = accepted_metadata.get(DESCRIPTION_REVIEW_KEY, {})
    if not isinstance(review, dict) or review.get("status") != "accepted":
        return False

    accepted_provenance = accepted_metadata.get(DESCRIPTION_PROVENANCE_KEY, {})
    candidate_provenance = candidate_metadata.get(DESCRIPTION_PROVENANCE_KEY, {})
    if not isinstance(accepted_provenance, dict) or not isinstance(candidate_provenance, dict):
        return False

    if accepted_provenance.get(GENERATED_CONTENT_HASH_KEY) != candidate.content_hash:
        return False
    if accepted_provenance.get("facts_hash") != candidate_provenance.get("facts_hash"):
        return False

    accepted_payload = _review_comparison_payload(current.record)
    candidate_payload = _review_comparison_payload(candidate.to_dict())
    return accepted_payload == candidate_payload


def _review_comparison_payload(payload: dict[str, object]) -> dict[str, object]:
    copy = json.loads(json.dumps(payload))
    for field in (
        "title",
        "summary",
        "description",
        "content_hash",
        "candidate_status",
        "accepted_revision",
        "first_seen_at",
        "last_seen_at",
    ):
        if field in copy:
            copy[field] = ""

    source_validation = copy.get("source_validation")
    if isinstance(source_validation, dict):
        source_validation["validated_at"] = ""

    metadata = copy.get("metadata", {})
    if isinstance(metadata, dict):
        metadata.pop(DESCRIPTION_REVIEW_KEY, None)
        provenance = metadata.get(DESCRIPTION_PROVENANCE_KEY)
        if isinstance(provenance, dict):
            provenance["generated_at"] = ""
            provenance.pop(GENERATED_CONTENT_HASH_KEY, None)
    return copy

def _run_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
