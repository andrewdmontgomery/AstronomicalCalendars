from __future__ import annotations

from pathlib import Path

from icalendar import Calendar

from astrocal.models import AcceptedRecord, CalendarManifest
from astrocal.repositories import CatalogStore, ReportStore, SequenceStore
from astrocal.services.build_ics_service import build_calendar


def test_build_calendar_writes_ics_and_sequence_state(tmp_path) -> None:
    catalog_store = CatalogStore(base_dir=tmp_path / "accepted")
    sequence_store = SequenceStore(base_dir=tmp_path / "sequences")
    report_store = ReportStore(base_dir=tmp_path / "reports")
    manifest = CalendarManifest(
        name="astronomy-all",
        output=str(tmp_path / "astronomical-events.ics"),
        calendar_name="Astronomical Events",
        calendar_description="Moon phases, equinoxes and solstices, and eclipses",
        variant_policy="default",
        source_types=["astronomy"],
    )

    catalog_store.save(
        "astronomy",
        2026,
        "moon-phases",
        [_accepted_record("moon-default", event_type="moon-phase", end=None, is_default=True)],
    )
    catalog_store.save(
        "astronomy",
        2026,
        "seasons",
        [_accepted_record("season-default", event_type="season", end=None, is_default=True)],
    )
    catalog_store.save(
        "astronomy",
        2026,
        "eclipses",
        [
            _accepted_record(
                "eclipse-default",
                event_type="eclipse",
                start="2026-03-03T09:33:00Z",
                end="2026-03-03T13:54:00Z",
                variant="default",
                is_default=True,
            ),
            _accepted_record(
                "eclipse-totality",
                event_type="eclipse",
                start="2026-03-03T10:00:00Z",
                end="2026-03-03T10:22:00Z",
                variant="totality",
                is_default=False,
            ),
        ],
    )

    report, written_paths = build_calendar(
        manifest=manifest,
        catalog_store=catalog_store,
        sequence_store=sequence_store,
        report_store=report_store,
        run_timestamp="2026-03-01T12-00-00Z",
    )

    calendar = Calendar.from_ical(Path(report.output_path).read_bytes())
    events = [component for component in calendar.walk() if component.name == "VEVENT"]

    assert report.event_count == 3
    assert report.sequence_path is not None
    assert Path(report.output_path).exists()
    assert len(events) == 3
    assert any(str(event["UID"]) == "moon-default" for event in events)
    moon_event = next(event for event in events if str(event["UID"]) == "moon-default")
    eclipse_event = next(event for event in events if str(event["UID"]) == "eclipse-default")
    assert moon_event.get("DTEND") is None
    assert eclipse_event.get("DTEND") is not None
    assert int(moon_event["SEQUENCE"]) == 0
    assert len(written_paths) == 3


def test_build_calendar_respects_variant_policy_and_sequence_changes(tmp_path) -> None:
    catalog_store = CatalogStore(base_dir=tmp_path / "accepted")
    sequence_store = SequenceStore(base_dir=tmp_path / "sequences")
    report_store = ReportStore(base_dir=tmp_path / "reports")
    manifest = CalendarManifest(
        name="astronomy-eclipses",
        output=str(tmp_path / "eclipses.ics"),
        calendar_name="Eclipses",
        calendar_description="Solar and lunar eclipses with exact astronomical timing",
        variant_policy="default",
        source_types=["astronomy"],
        event_types=["eclipse"],
    )
    default_record = _accepted_record(
        "eclipse-default",
        event_type="eclipse",
        start="2026-03-03T09:33:00Z",
        end="2026-03-03T13:54:00Z",
        variant="default",
        is_default=True,
        content_hash="sha256:one",
    )
    totality_record = _accepted_record(
        "eclipse-totality",
        event_type="eclipse",
        start="2026-03-03T10:00:00Z",
        end="2026-03-03T10:22:00Z",
        variant="totality",
        is_default=False,
        content_hash="sha256:two",
    )
    catalog_store.save("astronomy", 2026, "eclipses", [default_record, totality_record])

    report, _ = build_calendar(
        manifest=manifest,
        catalog_store=catalog_store,
        sequence_store=sequence_store,
        report_store=report_store,
        variant_policy="totality-only",
        run_timestamp="2026-03-01T12-00-00Z",
    )
    calendar = Calendar.from_ical(Path(report.output_path).read_bytes())
    events = [component for component in calendar.walk() if component.name == "VEVENT"]
    assert [str(event["UID"]) for event in events] == ["eclipse-totality"]
    assert int(events[0]["SEQUENCE"]) == 0

    changed_totality = _accepted_record(
        "eclipse-totality",
        event_type="eclipse",
        start="2026-03-03T10:01:00Z",
        end="2026-03-03T10:22:00Z",
        variant="totality",
        is_default=False,
        content_hash="sha256:changed",
        revision=2,
    )
    catalog_store.save("astronomy", 2026, "eclipses", [default_record, changed_totality])
    second_report, _ = build_calendar(
        manifest=manifest,
        catalog_store=catalog_store,
        sequence_store=sequence_store,
        report_store=report_store,
        variant_policy="totality-only",
        run_timestamp="2026-03-02T12-00-00Z",
    )
    second_calendar = Calendar.from_ical(Path(second_report.output_path).read_bytes())
    second_events = [component for component in second_calendar.walk() if component.name == "VEVENT"]

    assert [str(event["UID"]) for event in second_events] == ["eclipse-totality"]
    assert int(second_events[0]["SEQUENCE"]) == 1


def test_build_eclipse_manifest_ignores_unrelated_accepted_sources(tmp_path) -> None:
    catalog_store = CatalogStore(base_dir=tmp_path / "accepted")
    sequence_store = SequenceStore(base_dir=tmp_path / "sequences")
    report_store = ReportStore(base_dir=tmp_path / "reports")
    manifest = CalendarManifest(
        name="astronomy-eclipses",
        output=str(tmp_path / "eclipses.ics"),
        calendar_name="Eclipses",
        calendar_description="Solar and lunar eclipses with exact astronomical timing",
        variant_policy="default",
        source_types=["astronomy"],
        source_names=["eclipses"],
        event_types=["eclipse"],
    )
    catalog_store.save(
        "astronomy",
        2026,
        "moon-phases",
        [_accepted_record("moon-default", event_type="moon-phase", end=None, is_default=True)],
    )
    catalog_store.save(
        "astronomy",
        2026,
        "eclipses",
        [
            _accepted_record(
                "eclipse-default",
                event_type="eclipse",
                start="2026-03-03T09:33:00Z",
                end="2026-03-03T13:54:00Z",
                variant="default",
                is_default=True,
            ),
        ],
    )

    report, _ = build_calendar(
        manifest=manifest,
        catalog_store=catalog_store,
        sequence_store=sequence_store,
        report_store=report_store,
        run_timestamp="2026-03-01T12-00-00Z",
    )

    calendar = Calendar.from_ical(Path(report.output_path).read_bytes())
    events = [component for component in calendar.walk() if component.name == "VEVENT"]

    assert [str(event["UID"]) for event in events] == ["eclipse-default"]


def test_build_calendar_resolves_relative_output_against_project_root(tmp_path, monkeypatch) -> None:
    catalog_store = CatalogStore(base_dir=tmp_path / "accepted")
    sequence_store = SequenceStore(base_dir=tmp_path / "sequences")
    report_store = ReportStore(base_dir=tmp_path / "reports")
    manifest = CalendarManifest(
        name="astronomy-all",
        output="calendars/astronomical-events.ics",
        calendar_name="Astronomical Events",
        calendar_description="Moon phases, equinoxes and solstices, and eclipses",
        variant_policy="default",
        source_types=["astronomy"],
    )
    catalog_store.save(
        "astronomy",
        2026,
        "moon-phases",
        [_accepted_record("moon-default", event_type="moon-phase", end=None, is_default=True)],
    )

    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir()
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr("astrocal.services.build_ics_service.PROJECT_ROOT", tmp_path)

    report, written_paths = build_calendar(
        manifest=manifest,
        catalog_store=catalog_store,
        sequence_store=sequence_store,
        report_store=report_store,
        run_timestamp="2026-03-01T12-00-00Z",
    )

    expected_output = tmp_path / "calendars" / "astronomical-events.ics"
    assert report.output_path == "calendars/astronomical-events.ics"
    assert written_paths[0] == expected_output
    assert expected_output.exists()


def _accepted_record(
    occurrence_id: str,
    *,
    event_type: str,
    start: str = "2026-01-01T00:00:00Z",
    end: str | None,
    variant: str = "default",
    is_default: bool = True,
    content_hash: str = "sha256:abc123",
    revision: int = 1,
) -> AcceptedRecord:
    payload = {
        "group_id": occurrence_id,
        "occurrence_id": occurrence_id,
        "source_type": "astronomy",
        "body": "moon" if event_type == "moon-phase" else "earth",
        "event_type": event_type,
        "variant": variant,
        "is_default": is_default,
        "title": occurrence_id,
        "summary": occurrence_id,
        "description": f"{occurrence_id} description",
        "start": start,
        "end": end,
        "all_day": False,
        "timezone": "UTC",
        "categories": ["Astronomy"],
        "tags": [event_type],
        "detail_url": f"https://example.com/{occurrence_id}",
        "source_adapter": "adapter-v1",
        "source_validation": {
            "status": "passed",
            "validated_at": "2026-03-01T00:00:00Z",
            "reason": None,
            "checks": ["reachable"],
            "detail_url_ok": True,
        },
        "content_hash": content_hash,
        "first_seen_at": "2026-03-01T00:00:00Z",
        "last_seen_at": "2026-03-01T00:00:00Z",
        "candidate_status": "accepted",
        "accepted_revision": revision,
        "timing_source": {
            "name": "source",
            "url": f"https://example.com/{occurrence_id}",
        },
        "validation_sources": [],
        "metadata": {},
        "raw_ref": "data/raw/example.json",
    }
    return AcceptedRecord(
        occurrence_id=occurrence_id,
        revision=revision,
        status="active",
        accepted_at="2026-03-01T00:00:00Z",
        superseded_at=None,
        change_reason="Initial acceptance",
        content_hash=content_hash,
        source_adapter="adapter-v1",
        detail_url=payload["detail_url"],
        record=payload,
    )
