"""Reconciliation between normalized candidates and accepted catalog records."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ..adapters import ASTRONOMY_ADAPTERS
from ..git import GitStager
from ..models import AcceptedRecord, CalendarManifest, CandidateRecord, ReconciliationReport
from ..repositories import CandidateStore, CatalogStore, ReportStore


def reconcile_calendar(
    *,
    manifest: CalendarManifest,
    year: int,
    candidate_store: CandidateStore | None = None,
    catalog_store: CatalogStore | None = None,
    report_store: ReportStore | None = None,
    git_stager: GitStager | None = None,
    stage_changes: bool = True,
    run_timestamp: str | None = None,
) -> tuple[ReconciliationReport, list[Path]]:
    candidate_store = candidate_store or CandidateStore()
    catalog_store = catalog_store or CatalogStore()
    report_store = report_store or ReportStore()
    git_stager = git_stager or GitStager()
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
    written_paths: list[Path] = []

    for source_name, candidates in filtered_candidates_by_source.items():
        if _has_validation_failure(candidates):
            report.validation_failures.append(source_name)
            continue

        accepted_records = catalog_store.load("astronomy", year, source_name)
        reconciled = _reconcile_source_records(
            source_name=source_name,
            candidates=candidates,
            accepted_records=accepted_records,
            report=report,
            accepted_at=run_timestamp,
        )
        saved_path = catalog_store.save("astronomy", year, source_name, reconciled)
        written_paths.append(saved_path)

    report_name = f"reconcile.{manifest.name}"
    json_path = report_store.write_json_report(run_timestamp, report_name, report.to_dict())
    md_path = report_store.write_markdown_report(run_timestamp, report_name, _render_report(report))
    written_paths.extend([json_path, md_path])

    if stage_changes:
        staged = git_stager.stage_paths(written_paths)
        report.staged_paths.extend(staged)
        report_store.write_json_report(run_timestamp, report_name, report.to_dict())
        report_store.write_markdown_report(run_timestamp, report_name, _render_report(report))

    return report, written_paths


def _load_relevant_candidates(
    *,
    manifest: CalendarManifest,
    year: int,
    candidate_store: CandidateStore,
) -> dict[str, list[CandidateRecord]]:
    result: dict[str, list[CandidateRecord]] = {}
    if "astronomy" in manifest.source_types or not manifest.source_types:
        for source_name in ASTRONOMY_ADAPTERS:
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
    source_name: str,
    candidates: list[CandidateRecord],
    accepted_records: list[AcceptedRecord],
    report: ReconciliationReport,
    accepted_at: str,
) -> list[AcceptedRecord]:
    accepted_by_occurrence: dict[str, list[AcceptedRecord]] = defaultdict(list)
    for record in accepted_records:
        accepted_by_occurrence[record.occurrence_id].append(record)

    latest_by_occurrence = {
        occurrence_id: max(records, key=lambda record: record.revision)
        for occurrence_id, records in accepted_by_occurrence.items()
    }

    reconciled = list(accepted_records)
    current_candidate_ids = {candidate.occurrence_id for candidate in candidates}

    for candidate in candidates:
        current = latest_by_occurrence.get(candidate.occurrence_id)
        if current is None:
            reconciled.append(
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
            report.new_occurrences.append(candidate.occurrence_id)
            continue

        if current.content_hash == candidate.content_hash and current.status == "active":
            report.unchanged_occurrences.append(candidate.occurrence_id)
            continue

        current.status = "superseded"
        current.superseded_at = accepted_at
        new_revision = current.revision + 1
        reconciled.append(
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
        report.changed_occurrences.append(candidate.occurrence_id)

    for occurrence_id, current in latest_by_occurrence.items():
        if occurrence_id in current_candidate_ids:
            continue
        if current.status != "active":
            continue
        current.status = "suspected-removed"
        current.superseded_at = accepted_at
        current.change_reason = "Missing from current candidate set"
        report.suspected_removals.append(occurrence_id)

    return sorted(reconciled, key=lambda record: (record.occurrence_id, record.revision))


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


def _render_report(report: ReconciliationReport) -> str:
    lines = [
        f"# Reconciliation Report: {report.calendar_name}",
        "",
        f"- Year: {report.year}",
        f"- Generated at: {report.generated_at}",
        f"- New occurrences: {len(report.new_occurrences)}",
        f"- Unchanged occurrences: {len(report.unchanged_occurrences)}",
        f"- Changed occurrences: {len(report.changed_occurrences)}",
        f"- Suspected removals: {len(report.suspected_removals)}",
        f"- Validation failures: {len(report.validation_failures)}",
    ]
    if report.staged_paths:
        lines.append(f"- Staged paths: {len(report.staged_paths)}")

    for title, values in (
        ("New Occurrences", report.new_occurrences),
        ("Changed Occurrences", report.changed_occurrences),
        ("Suspected Removals", report.suspected_removals),
        ("Validation Failures", report.validation_failures),
    ):
        lines.extend(["", f"## {title}"])
        if values:
            lines.extend(f"- {value}" for value in values)
        else:
            lines.append("- None")

    return "\n".join(lines) + "\n"


def _run_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
