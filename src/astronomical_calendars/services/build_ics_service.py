"""Build ICS output from accepted catalog records."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from icalendar import Calendar, Event

from ..adapters import ASTRONOMY_ADAPTERS
from ..models import AcceptedRecord, BuildReport, CalendarManifest
from ..paths import PROJECT_ROOT
from ..renderers.markdown_report import render_build_report
from ..repositories import CatalogStore, ReportStore, SequenceStore


def build_calendar(
    *,
    manifest: CalendarManifest,
    catalog_store: CatalogStore | None = None,
    sequence_store: SequenceStore | None = None,
    report_store: ReportStore | None = None,
    variant_policy: str | None = None,
    run_timestamp: str | None = None,
) -> tuple[BuildReport, list[Path]]:
    catalog_store = catalog_store or CatalogStore()
    sequence_store = sequence_store or SequenceStore()
    report_store = report_store or ReportStore()
    run_timestamp = run_timestamp or _run_timestamp()
    effective_variant_policy = variant_policy or manifest.variant_policy
    generated_at = _parse_report_timestamp(run_timestamp)

    accepted_records = _load_relevant_records(manifest=manifest, catalog_store=catalog_store)
    active_records = [record for record in accepted_records if record.status == "active"]
    filtered_records = [
        record
        for record in active_records
        if _matches_manifest(manifest, record) and _matches_variant_policy(effective_variant_policy, record)
    ]
    filtered_records.sort(key=lambda record: (record.record.get("start", ""), record.occurrence_id))

    calendar = Calendar()
    calendar.add("prodid", "-//AstronomicalCalendars//EN")
    calendar.add("version", "2.0")
    calendar.add("X-WR-CALNAME", manifest.calendar_name)
    calendar.add("X-WR-CALDESC", manifest.calendar_description)

    sequence_state = sequence_store.load_state(manifest.name)
    next_sequence_state: dict[str, dict[str, int | str]] = {}

    for record in filtered_records:
        event = Event()
        payload = record.record
        sequence = _next_sequence(sequence_state.get(record.occurrence_id), record.content_hash)
        next_sequence_state[record.occurrence_id] = {
            "sequence": sequence,
            "content_hash": record.content_hash,
        }

        event.add("uid", record.occurrence_id)
        event.add("sequence", sequence)
        event.add("summary", payload["title"])
        event.add("description", payload["description"])
        event.add("dtstart", _parse_utc_datetime(payload["start"]))
        event.add("dtstamp", generated_at)
        event.add("url", record.detail_url)
        if payload.get("end"):
            event.add("dtend", _parse_utc_datetime(payload["end"]))
        categories = payload.get("categories", [])
        if categories:
            event.add("categories", categories)
        calendar.add_component(event)

    output_path = PROJECT_ROOT / manifest.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(calendar.to_ical())

    sequence_path = sequence_store.save_state(manifest.name, next_sequence_state)
    report = BuildReport(
        calendar_name=manifest.name,
        generated_at=run_timestamp,
        output_path=str(output_path),
        event_count=len(filtered_records),
        sequence_path=str(sequence_path),
    )
    report_name = f"build.{manifest.name}"
    json_path = report_store.write_json_report(run_timestamp, report_name, report.to_dict())
    md_path = report_store.write_markdown_report(run_timestamp, report_name, render_build_report(report))
    return report, [output_path, sequence_path, json_path, md_path]


def _load_relevant_records(
    *,
    manifest: CalendarManifest,
    catalog_store: CatalogStore,
) -> list[AcceptedRecord]:
    records: list[AcceptedRecord] = []
    if "astronomy" not in manifest.source_types and manifest.source_types:
        return records

    for source_name in ASTRONOMY_ADAPTERS:
        for year in catalog_store.available_years("astronomy", source_name):
            records.extend(catalog_store.load("astronomy", year, source_name))
    return records


def _matches_manifest(manifest: CalendarManifest, record: AcceptedRecord) -> bool:
    payload = record.record
    if manifest.event_types and payload.get("event_type") not in manifest.event_types:
        return False
    if manifest.bodies and payload.get("body") not in manifest.bodies:
        return False
    if manifest.tags and not set(payload.get("tags", [])).intersection(manifest.tags):
        return False
    return True


def _matches_variant_policy(variant_policy: str, record: AcceptedRecord) -> bool:
    payload = record.record
    if variant_policy == "both":
        return True
    if variant_policy == "totality-only":
        return payload.get("variant") == "totality"
    return bool(payload.get("is_default", False))


def _next_sequence(
    previous_state: dict[str, int | str] | None,
    content_hash: str,
) -> int:
    if previous_state is None:
        return 0
    previous_sequence = int(previous_state.get("sequence", 0))
    previous_hash = str(previous_state.get("content_hash", ""))
    if previous_hash == content_hash:
        return previous_sequence
    return previous_sequence + 1


def _parse_utc_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _parse_report_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H-%M-%SZ").replace(tzinfo=timezone.utc)


def _run_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
