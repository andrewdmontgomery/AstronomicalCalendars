from __future__ import annotations

from pathlib import Path

import pytest

from astrocal.models import RawFetchResult, ValidationReport
from astrocal.repositories import DiagnosticStore, ReportStore
from astrocal.services.fetch_service import fetch_source_family
from astrocal.services.normalize_service import normalize_source_family
from astrocal.services.validation_service import validate_source_family


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
            canary_ok=False,
            source_url="https://example.com/eclipses",
        )


class BrokenNormalizeAdapter(PassingAdapter):
    def normalize(self, year: int, raw_result: RawFetchResult) -> list[object]:
        raise ValueError("unexpected payload shape")


def test_validate_source_family_writes_json_reports(tmp_path) -> None:
    report_store = ReportStore(base_dir=tmp_path)

    exit_code, reports = validate_source_family(
        "astronomy",
        2026,
        adapters={"moon-phases": PassingAdapter()},
        report_store=report_store,
        run_timestamp="2026-03-01T12-00-00Z",
    )

    json_report = tmp_path / "2026-03-01T12-00-00Z" / "validate.moon-phases.2026.json"
    assert exit_code == 0
    assert len(reports) == 1
    assert json_report.exists()
    assert reports[0].canary_ok is True


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
    assert reports[0].canary_ok is False


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
                    canary_ok=False,
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
                canary_ok=True,
                source_url="https://example.com/moon-phases",
            )
        ],
    )

    assert len(results) == 1
    assert results[0].raw_ref.endswith("response.json")


def test_normalize_source_family_writes_summary_diagnostics(tmp_path) -> None:
    results = normalize_source_family(
        "astronomy",
        2026,
        adapters={"moon-phases": PassingAdapter()},
        raw_results=[
            RawFetchResult(
                source_name="moon-phases",
                year=2026,
                fetched_at="2026-03-01T00:01:00Z",
                raw_ref="data/raw/astronomy/2026/moon-phases/response.json",
                source_url="https://example.com/moon-phases",
            )
        ],
        diagnostic_store=DiagnosticStore(base_dir=tmp_path / "diagnostics"),
    )

    summary_path = tmp_path / "diagnostics" / "astronomy" / "2026" / "moon-phases" / "normalize-summary.json"
    assert len(results) == 1
    assert summary_path.exists()
    summary_text = summary_path.read_text(encoding="utf-8")
    assert '"candidate_count": 0' in summary_text
    assert '"canary_ok": true' in summary_text
    assert '"metadata_keys": []' in summary_text
    assert '"titles_sample": []' in summary_text


def test_normalize_source_family_writes_failure_diagnostics(tmp_path) -> None:
    with pytest.raises(ValueError, match="unexpected payload shape"):
        normalize_source_family(
            "astronomy",
            2026,
            adapters={"moon-phases": BrokenNormalizeAdapter()},
            raw_results=[
                RawFetchResult(
                    source_name="moon-phases",
                    year=2026,
                    fetched_at="2026-03-01T00:01:00Z",
                    raw_ref="data/raw/astronomy/2026/moon-phases/response.json",
                    source_url="https://example.com/moon-phases",
                )
            ],
            diagnostic_store=DiagnosticStore(base_dir=tmp_path / "diagnostics"),
        )

    failure_path = tmp_path / "diagnostics" / "astronomy" / "2026" / "moon-phases" / "normalize-failure.json"
    assert failure_path.exists()
    failure_text = failure_path.read_text(encoding="utf-8")
    assert '"failure_stage": "normalize"' in failure_text
    assert '"reason": "unexpected payload shape"' in failure_text
