from __future__ import annotations

from pathlib import Path

from astrocal.models import CalendarManifest, RawFetchResult, ValidationReport
from astrocal.repositories import CandidateStore, CatalogStore, DiagnosticStore, ReportStore, SequenceStore
from astrocal.services.run_pipeline_service import run_calendar_pipeline
from tests.test_review_report_service import build_eclipse_candidate


class MoonPhasesAdapter:
    source_name = "moon-phases"
    source_type = "astronomy"

    def validate(self, year: int) -> ValidationReport:
        return ValidationReport(
            source_name=self.source_name,
            year=year,
            status="passed",
            validated_at="2026-03-01T00:00:00Z",
            checks=["reachable"],
            canary_ok=True,
            source_url="https://example.com/moon-phases",
        )

    def fetch(self, year: int) -> RawFetchResult:
        return RawFetchResult(
            source_name=self.source_name,
            year=year,
            fetched_at="2026-03-01T00:01:00Z",
            raw_ref="data/raw/astronomy/2026/moon-phases/response.json",
            source_url="https://example.com/moon-phases",
        )

    def normalize(self, year: int, raw_result: RawFetchResult) -> list[object]:
        return []


class EclipsesAdapter:
    source_name = "eclipses"
    source_type = "astronomy"

    def validate(self, year: int) -> ValidationReport:
        return ValidationReport(
            source_name=self.source_name,
            year=year,
            status="passed",
            validated_at="2026-03-01T00:00:00Z",
            checks=["reachable"],
            canary_ok=True,
            source_url="https://example.com/eclipses",
        )

    def fetch(self, year: int) -> RawFetchResult:
        return RawFetchResult(
            source_name=self.source_name,
            year=year,
            fetched_at="2026-03-01T00:01:00Z",
            raw_ref="data/raw/astronomy/2026/eclipses/response.json",
            source_url="https://example.com/eclipses",
        )

    def normalize(self, year: int, raw_result: RawFetchResult) -> list[object]:
        return [build_eclipse_candidate()]


def build_manifest(name: str, output_path: Path, source_name: str, event_type: str) -> CalendarManifest:
    return CalendarManifest(
        name=name,
        output=str(output_path),
        calendar_name=name,
        calendar_description=f"{name} test calendar",
        variant_policy="default",
        source_types=["astronomy"],
        source_names=[source_name],
        event_types=[event_type],
        bodies=[],
        tags=[],
    )


def test_run_calendar_pipeline_returns_build_result_when_no_review_is_needed(tmp_path: Path) -> None:
    report_store = ReportStore(base_dir=tmp_path / "reports")
    diagnostic_store = DiagnosticStore(base_dir=tmp_path / "diagnostics")
    candidate_store = CandidateStore(base_dir=tmp_path / "normalized")
    catalog_store = CatalogStore(base_dir=tmp_path / "accepted")
    sequence_store = SequenceStore(base_dir=tmp_path / "sequences")
    manifest = build_manifest(
        "astronomy-moon-phases",
        tmp_path / "moon-phases.ics",
        "moon-phases",
        "moon-phase",
    )

    result = run_calendar_pipeline(
        manifest=manifest,
        year=2026,
        adapters={"moon-phases": MoonPhasesAdapter()},
        report_store=report_store,
        diagnostic_store=diagnostic_store,
        candidate_store=candidate_store,
        catalog_store=catalog_store,
        sequence_store=sequence_store,
        run_timestamp="2026-03-01T12-00-00Z",
    )

    assert result.calendar_name == "astronomy-moon-phases"
    assert result.year == 2026
    assert result.generated_at == "2026-03-01T12-00-00Z"
    assert result.report_dir == str(report_store._base_dir)
    assert result.stopped_for_review is False
    assert len(result.validation_reports) == 1
    assert len(result.raw_results) == 1
    assert result.normalized_results[0].source_name == "moon-phases"
    assert result.normalized_results[0].candidate_count == 0
    assert result.reconciliation_report.review_report_path is None
    assert result.build_report is not None
    assert Path(result.build_report.output_path).exists()
    assert any(path.endswith("build.astronomy-moon-phases.json") for path in result.written_paths)
    assert any(path.endswith("moon-phases.ics") for path in result.written_paths)


def test_run_calendar_pipeline_stops_before_build_when_review_is_pending(tmp_path: Path) -> None:
    report_store = ReportStore(base_dir=tmp_path / "reports")
    diagnostic_store = DiagnosticStore(base_dir=tmp_path / "diagnostics")
    candidate_store = CandidateStore(base_dir=tmp_path / "normalized")
    catalog_store = CatalogStore(base_dir=tmp_path / "accepted")
    sequence_store = SequenceStore(base_dir=tmp_path / "sequences")
    manifest = build_manifest(
        "astronomy-eclipses",
        tmp_path / "eclipses.ics",
        "eclipses",
        "eclipse",
    )

    result = run_calendar_pipeline(
        manifest=manifest,
        year=2026,
        adapters={"eclipses": EclipsesAdapter()},
        report_store=report_store,
        diagnostic_store=diagnostic_store,
        candidate_store=candidate_store,
        catalog_store=catalog_store,
        sequence_store=sequence_store,
        run_timestamp="2026-03-01T12-00-00Z",
    )

    assert result.report_dir == str(report_store._base_dir)
    assert result.stopped_for_review is True
    assert result.build_report is None
    assert result.reconciliation_report.review_report_path is not None
    assert result.reconciliation_report.review_bundle_path is not None
    assert any(path.endswith("review.astronomy-eclipses.md") for path in result.written_paths)
    assert any(path.endswith("review.astronomy-eclipses.json") for path in result.written_paths)
    assert not any(path.endswith("eclipses.ics") for path in result.written_paths)
