from __future__ import annotations

from pathlib import Path

import pytest

from astronomical_calendars.models import RawFetchResult, ValidationReport
from astronomical_calendars.repositories import ReportStore
from astronomical_calendars.services.fetch_service import fetch_source_family
from astronomical_calendars.services.validation_service import validate_source_family


class PassingAdapter:
    source_name = "moon-phases"
    source_type = "astronomy"

    def validate(self, year: int) -> ValidationReport:
        return ValidationReport(
            source_name=self.source_name,
            year=year,
            status="passed",
            validated_at="2026-03-01T00:00:00Z",
            checks=["reachable", "fields present"],
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


class FailingAdapter(PassingAdapter):
    source_name = "eclipses"

    def validate(self, year: int) -> ValidationReport:
        return ValidationReport(
            source_name=self.source_name,
            year=year,
            status="failed",
            validated_at="2026-03-01T00:00:00Z",
            checks=["reachable"],
            reason="required timing fields missing",
            source_url="https://example.com/eclipses",
        )


def test_validate_source_family_writes_json_and_markdown_reports(tmp_path) -> None:
    report_store = ReportStore(base_dir=tmp_path)

    exit_code, reports = validate_source_family(
        "astronomy",
        2026,
        adapters={"moon-phases": PassingAdapter()},
        report_store=report_store,
        run_timestamp="2026-03-01T12-00-00Z",
    )

    json_report = tmp_path / "2026-03-01T12-00-00Z" / "validate.moon-phases.2026.json"
    markdown_report = tmp_path / "2026-03-01T12-00-00Z" / "validate.moon-phases.2026.md"

    assert exit_code == 0
    assert len(reports) == 1
    assert json_report.exists()
    assert markdown_report.exists()
    assert "Status: passed" in markdown_report.read_text(encoding="utf-8")


def test_validate_source_family_returns_non_zero_for_failed_validation(tmp_path) -> None:
    exit_code, reports = validate_source_family(
        "astronomy",
        2026,
        adapters={"eclipses": FailingAdapter()},
        report_store=ReportStore(base_dir=tmp_path),
        run_timestamp="2026-03-01T12-00-00Z",
    )

    assert exit_code == 1
    assert reports[0].status == "failed"


def test_fetch_source_family_stops_after_validation_failure() -> None:
    with pytest.raises(RuntimeError, match="Refusing to fetch after validation failure"):
        fetch_source_family(
            2026,
            adapters={"eclipses": FailingAdapter()},
            validation_reports=[
                ValidationReport(
                    source_name="eclipses",
                    year=2026,
                    status="failed",
                    validated_at="2026-03-01T00:00:00Z",
                    checks=["reachable"],
                    reason="required timing fields missing",
                    source_url="https://example.com/eclipses",
                )
            ],
        )


def test_fetch_source_family_returns_raw_results_after_validation_passes() -> None:
    results = fetch_source_family(
        2026,
        adapters={"moon-phases": PassingAdapter()},
        validation_reports=[
            ValidationReport(
                source_name="moon-phases",
                year=2026,
                status="passed",
                validated_at="2026-03-01T00:00:00Z",
                checks=["reachable"],
                source_url="https://example.com/moon-phases",
            )
        ],
    )

    assert len(results) == 1
    assert results[0].raw_ref.endswith("response.json")
