from __future__ import annotations

from pathlib import Path

from astrocal.models import CalendarManifest
from astrocal.repositories import CandidateStore, CatalogStore, ReportStore
from astrocal.services.reconcile_service import reconcile_calendar
from tests.test_repositories import build_candidate


def build_manifest() -> CalendarManifest:
    return CalendarManifest(
        name="astronomy-all",
        output="calendars/astronomical-events.ics",
        calendar_name="Astronomical Events",
        calendar_description="Moon phases, equinoxes and solstices, and eclipses",
        variant_policy="default",
        source_validation_policy="strict",
        reconciliation_mode="verify",
        correction_mode="apply-working-tree",
        stop_on_source_failure=True,
        stop_on_conflict=True,
        source_types=["astronomy"],
        event_types=[],
        bodies=[],
        tags=[],
    )


def test_reconcile_adds_new_record(tmp_path: Path) -> None:
    candidate_store = CandidateStore(base_dir=tmp_path / "normalized")
    catalog_store = CatalogStore(base_dir=tmp_path / "accepted")
    report_store = ReportStore(base_dir=tmp_path / "reports")
    candidate = build_candidate()
    candidate_store.save("astronomy", 2026, "moon-phases", [candidate])

    report, _ = reconcile_calendar(
        manifest=build_manifest(),
        year=2026,
        candidate_store=candidate_store,
        catalog_store=catalog_store,
        report_store=report_store,
        run_timestamp="2026-03-01T12-00-00Z",
    )

    saved = catalog_store.load("astronomy", 2026, "moon-phases")
    assert len(saved) == 1
    assert saved[0].revision == 1
    assert saved[0].status == "active"
    assert report.new_occurrences == [candidate.occurrence_id]


def test_reconcile_leaves_unchanged_record_untouched(tmp_path: Path) -> None:
    candidate_store = CandidateStore(base_dir=tmp_path / "normalized")
    catalog_store = CatalogStore(base_dir=tmp_path / "accepted")
    report_store = ReportStore(base_dir=tmp_path / "reports")
    candidate = build_candidate()
    candidate_store.save("astronomy", 2026, "moon-phases", [candidate])
    catalog_store.save(
        "astronomy",
        2026,
        "moon-phases",
        [
            _accepted_from_candidate(
                candidate,
                revision=1,
                status="active",
                accepted_at="2026-03-01T12:00:00Z",
                change_reason="Initial acceptance",
            )
        ],
    )

    report, _ = reconcile_calendar(
        manifest=build_manifest(),
        year=2026,
        candidate_store=candidate_store,
        catalog_store=catalog_store,
        report_store=report_store,
        run_timestamp="2026-03-02T12-00-00Z",
    )

    saved = catalog_store.load("astronomy", 2026, "moon-phases")
    assert len(saved) == 1
    assert report.unchanged_occurrences == [candidate.occurrence_id]


def test_reconcile_creates_new_revision_for_changed_record(tmp_path: Path) -> None:
    candidate_store = CandidateStore(base_dir=tmp_path / "normalized")
    catalog_store = CatalogStore(base_dir=tmp_path / "accepted")
    report_store = ReportStore(base_dir=tmp_path / "reports")
    candidate = build_candidate()
    candidate.summary = "Updated New Moon"
    candidate.content_hash = "sha256:updated"
    candidate_store.save("astronomy", 2026, "moon-phases", [candidate])

    previous = build_candidate()
    catalog_store.save(
        "astronomy",
        2026,
        "moon-phases",
        [
            _accepted_from_candidate(
                previous,
                revision=1,
                status="active",
                accepted_at="2026-03-01T12:00:00Z",
                change_reason="Initial acceptance",
            )
        ],
    )

    report, _ = reconcile_calendar(
        manifest=build_manifest(),
        year=2026,
        candidate_store=candidate_store,
        catalog_store=catalog_store,
        report_store=report_store,
        run_timestamp="2026-03-02T12-00-00Z",
    )

    saved = catalog_store.load("astronomy", 2026, "moon-phases")
    assert len(saved) == 2
    assert saved[0].status == "superseded"
    assert saved[1].revision == 2
    assert report.changed_occurrences == [candidate.occurrence_id]


def test_reconcile_marks_missing_candidate_as_suspected_removed(tmp_path: Path) -> None:
    catalog_store = CatalogStore(base_dir=tmp_path / "accepted")
    report_store = ReportStore(base_dir=tmp_path / "reports")
    candidate = build_candidate()
    catalog_store.save(
        "astronomy",
        2026,
        "moon-phases",
        [
            _accepted_from_candidate(
                candidate,
                revision=1,
                status="active",
                accepted_at="2026-03-01T12:00:00Z",
                change_reason="Initial acceptance",
            )
        ],
    )

    report, _ = reconcile_calendar(
        manifest=build_manifest(),
        year=2026,
        candidate_store=CandidateStore(base_dir=tmp_path / "normalized"),
        catalog_store=catalog_store,
        report_store=report_store,
        run_timestamp="2026-03-02T12-00-00Z",
    )

    saved = catalog_store.load("astronomy", 2026, "moon-phases")
    assert saved[0].status == "suspected-removed"
    assert report.suspected_removals == [candidate.occurrence_id]


def test_reconcile_writes_catalog_and_reports_without_staging(tmp_path: Path) -> None:
    candidate_store = CandidateStore(base_dir=tmp_path / "normalized")
    catalog_store = CatalogStore(base_dir=tmp_path / "accepted")
    report_store = ReportStore(base_dir=tmp_path / "reports")
    candidate = build_candidate()
    candidate_store.save("astronomy", 2026, "moon-phases", [candidate])

    report, written_paths = reconcile_calendar(
        manifest=build_manifest(),
        year=2026,
        candidate_store=candidate_store,
        catalog_store=catalog_store,
        report_store=report_store,
        run_timestamp="2026-03-02T12-00-00Z",
    )

    assert report.new_occurrences == [candidate.occurrence_id]
    assert any(path.name == "moon-phases.json" for path in written_paths)
    assert any(path.name == "reconcile.astronomy-all.json" for path in written_paths)
    assert all(path.exists() for path in written_paths)


def test_reconcile_stops_before_catalog_writes_on_validation_failure(tmp_path: Path) -> None:
    candidate_store = CandidateStore(base_dir=tmp_path / "normalized")
    catalog_store = CatalogStore(base_dir=tmp_path / "accepted")
    report_store = ReportStore(base_dir=tmp_path / "reports")

    valid_candidate = build_candidate()
    failed_candidate = build_candidate()
    failed_candidate.occurrence_id = "astronomy/eclipse/2026-03-03/total-lunar-eclipse/default"
    failed_candidate.group_id = "astronomy/eclipse/2026-03-03/total-lunar-eclipse"
    failed_candidate.source_adapter = "timeanddate-eclipses-v1"
    failed_candidate.source_validation.status = "failed"
    failed_candidate.source_validation.reason = "required timing fields missing"

    candidate_store.save("astronomy", 2026, "moon-phases", [valid_candidate])
    candidate_store.save("astronomy", 2026, "eclipses", [failed_candidate])

    report, written_paths = reconcile_calendar(
        manifest=build_manifest(),
        year=2026,
        candidate_store=candidate_store,
        catalog_store=catalog_store,
        report_store=report_store,
        run_timestamp="2026-03-02T12-00-00Z",
    )

    assert report.validation_failures == ["eclipses"]
    assert catalog_store.load("astronomy", 2026, "moon-phases") == []
    assert catalog_store.load("astronomy", 2026, "eclipses") == []
    assert len(written_paths) == 1
    assert all(path.name.startswith("reconcile.astronomy-all") for path in written_paths)
    assert all(path.exists() for path in written_paths)


def _accepted_from_candidate(candidate, *, revision, status, accepted_at, change_reason):
    from astrocal.models import AcceptedRecord

    return AcceptedRecord(
        occurrence_id=candidate.occurrence_id,
        revision=revision,
        status=status,
        accepted_at=accepted_at,
        superseded_at=None,
        change_reason=change_reason,
        content_hash=candidate.content_hash,
        source_adapter=candidate.source_adapter,
        detail_url=candidate.detail_url,
        record=candidate.to_dict(),
    )
