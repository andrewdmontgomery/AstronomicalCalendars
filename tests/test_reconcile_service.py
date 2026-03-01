from __future__ import annotations

import subprocess
from pathlib import Path

from astronomical_calendars.git import GitStager
from astronomical_calendars.models import CalendarManifest
from astronomical_calendars.repositories import CandidateStore, CatalogStore, ReportStore
from astronomical_calendars.services.reconcile_service import reconcile_calendar
from tests.test_repositories import build_candidate


def build_manifest() -> CalendarManifest:
    return CalendarManifest(
        name="astronomy-all",
        output="output/calendars/astronomy-all.ics",
        calendar_name="Astronomical Events",
        calendar_description="Moon phases, seasons, and eclipses",
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
        stage_changes=False,
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
        stage_changes=False,
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
        stage_changes=False,
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
        stage_changes=False,
        run_timestamp="2026-03-02T12-00-00Z",
    )

    saved = catalog_store.load("astronomy", 2026, "moon-phases")
    assert saved[0].status == "suspected-removed"
    assert report.suspected_removals == [candidate.occurrence_id]


def test_reconcile_stages_changed_files_in_manual_mode(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "codex@example.com"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Codex"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )

    candidate_store = CandidateStore(base_dir=repo_root / "data" / "normalized")
    catalog_store = CatalogStore(base_dir=repo_root / "data" / "catalog" / "accepted")
    report_store = ReportStore(base_dir=repo_root / "data" / "catalog" / "reports")
    candidate = build_candidate()
    candidate_store.save("astronomy", 2026, "moon-phases", [candidate])

    report, written_paths = reconcile_calendar(
        manifest=build_manifest(),
        year=2026,
        candidate_store=candidate_store,
        catalog_store=catalog_store,
        report_store=report_store,
        git_stager=GitStager(repo_root=repo_root),
        stage_changes=True,
        run_timestamp="2026-03-02T12-00-00Z",
    )

    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert report.staged_paths
    assert any("moon-phases.json" in path for path in report.staged_paths)
    assert "A  data/catalog/accepted/astronomy/2026/moon-phases.json" in status
    assert "AM data/catalog/reports/2026-03-02T12-00-00Z/reconcile.astronomy-all.json" not in status
    assert "AM data/catalog/reports/2026-03-02T12-00-00Z/reconcile.astronomy-all.md" not in status
    assert any(path.exists() for path in written_paths)


def _accepted_from_candidate(candidate, *, revision, status, accepted_at, change_reason):
    from astronomical_calendars.models import AcceptedRecord

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
