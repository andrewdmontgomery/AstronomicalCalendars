"""Read-only helpers for persisted eclipse review bundles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..jsonio import read_json
from ..models import (
    AcceptedRecord,
    DESCRIPTION_PROVENANCE_KEY,
    DESCRIPTION_REVIEW_KEY,
    GENERATED_CONTENT_HASH_KEY,
    ReviewBundle,
    ReviewBundleEntry,
)
from ..paths import PROJECT_ROOT
from ..repositories import CatalogStore


@dataclass(slots=True)
class PendingReview:
    report_path: Path
    bundle: ReviewBundle


def list_pending_reviews(
    report_dir: Path | None = None,
    catalog_store: CatalogStore | None = None,
) -> list[PendingReview]:
    base_dir = _resolve_report_dir(report_dir)
    catalog_store = catalog_store or CatalogStore()
    pending: list[PendingReview] = []
    active_records_by_source: dict[tuple[int, str], dict[str, AcceptedRecord]] = {}
    for path in sorted(base_dir.glob("*/review.*.json")):
        bundle = load_review_bundle(path)
        pending_entries = [
            entry
            for entry in bundle.entries
            if _is_pending_entry(
                entry=entry,
                year=bundle.year,
                catalog_store=catalog_store,
                active_records_by_source=active_records_by_source,
            )
        ]
        if not pending_entries:
            continue
        pending.append(
            PendingReview(
                report_path=path,
                bundle=ReviewBundle(
                    calendar_name=bundle.calendar_name,
                    year=bundle.year,
                    generated_at=bundle.generated_at,
                    entries=pending_entries,
                ),
            )
        )
    return pending


def load_review_bundle(report_path: Path) -> ReviewBundle:
    resolved_path = _resolve_path(report_path)
    payload = read_json(resolved_path)
    return ReviewBundle.from_dict(payload)


def render_review_bundle(bundle: ReviewBundle, *, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(bundle.to_dict(), indent=2, sort_keys=True)

    lines = [
        f"Review bundle: {bundle.calendar_name}",
        f"Year: {bundle.year}",
        f"Generated at: {bundle.generated_at}",
        f"Entries: {len(bundle.entries)}",
        "",
    ]
    for entry in bundle.entries:
        lines.extend(_render_entry(entry))
    return "\n".join(lines).rstrip()


def _render_entry(entry: ReviewBundleEntry) -> list[str]:
    title = ""
    if entry.candidate is not None:
        title = str(entry.candidate.get("title", ""))
    elif entry.accepted is not None:
        accepted_record = entry.accepted.get("record", {})
        if isinstance(accepted_record, dict):
            title = str(accepted_record.get("title", ""))
    lines = [
        f"- {entry.occurrence_id}",
        f"  status={entry.status}",
        f"  group_id={entry.group_id}",
    ]
    if title:
        lines.append(f"  title={title}")
    lines.append(f"  allowed_actions={', '.join(entry.allowed_actions)}")
    return lines + [""]


def _resolve_report_dir(report_dir: Path | None) -> Path:
    if report_dir is None:
        return PROJECT_ROOT / "data" / "catalog" / "reports"
    return _resolve_path(report_dir)


def _resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _is_pending_entry(
    *,
    entry: ReviewBundleEntry,
    year: int,
    catalog_store: CatalogStore,
    active_records_by_source: dict[tuple[int, str], dict[str, AcceptedRecord]],
) -> bool:
    active_by_occurrence = _active_records_for_source(
        year=year,
        source_name=entry.source_name,
        catalog_store=catalog_store,
        active_records_by_source=active_records_by_source,
    )
    current = active_by_occurrence.get(entry.occurrence_id)

    if entry.status == "suspected-removed":
        return _matches_entry_baseline(entry, current)

    if current is None:
        return entry.accepted is None
    if _entry_is_satisfied(entry, current):
        return False
    if entry.accepted is None:
        return True
    return _matches_entry_baseline(entry, current)


def _active_records_for_source(
    *,
    year: int,
    source_name: str,
    catalog_store: CatalogStore,
    active_records_by_source: dict[tuple[int, str], dict[str, AcceptedRecord]],
) -> dict[str, AcceptedRecord]:
    key = (year, source_name)
    cached = active_records_by_source.get(key)
    if cached is not None:
        return cached

    active = {
        record.occurrence_id: record
        for record in catalog_store.load("astronomy", year, source_name)
        if record.status == "active"
    }
    active_records_by_source[key] = active
    return active


def _entry_is_satisfied(entry: ReviewBundleEntry, current: AcceptedRecord) -> bool:
    if entry.candidate is None:
        return False
    metadata = current.record.get("metadata", {})
    if not isinstance(metadata, dict):
        return False
    review = metadata.get(DESCRIPTION_REVIEW_KEY, {})
    if not isinstance(review, dict) or review.get("status") != "accepted":
        return False
    provenance = metadata.get(DESCRIPTION_PROVENANCE_KEY, {})
    if not isinstance(provenance, dict):
        return False
    generated_content_hash = provenance.get(GENERATED_CONTENT_HASH_KEY)
    return isinstance(generated_content_hash, str) and (
        generated_content_hash == entry.generated_content_hash
    )


def _matches_entry_baseline(entry: ReviewBundleEntry, current: AcceptedRecord | None) -> bool:
    if current is None or entry.accepted is None:
        return False
    return (
        current.revision == entry.accepted.get("revision")
        and current.content_hash == entry.accepted.get("content_hash")
    )
