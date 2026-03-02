from __future__ import annotations

from pathlib import Path

import pytest
from icalendar import Calendar

from astrocal.models import AcceptedRecord, CalendarManifest, RawFetchResult, ValidationReport
from astrocal.repositories import CandidateStore, CatalogStore, DiagnosticStore, ReportStore, SequenceStore
from astrocal.services.build_ics_service import build_calendar
from astrocal.services.fetch_service import fetch_source_family
from astrocal.services.normalize_service import normalize_source_family
from astrocal.services.reconcile_service import reconcile_calendar
from astrocal.services.validation_service import validate_source_family
from tests.test_timeanddate_eclipses import build_adapter


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


class BrokenFetchAdapter(PassingAdapter):
    def fetch(self, year: int) -> RawFetchResult:
        raise ValueError("request timed out")


class BrokenCandidateStore(CandidateStore):
    def save(self, source_type: str, year: int, source_name: str, candidates: list[object]):
        raise OSError("unable to persist candidates")


def test_validate_source_family_writes_json_reports(tmp_path) -> None:
    report_store = ReportStore(base_dir=tmp_path)
    diagnostic_store = DiagnosticStore(base_dir=tmp_path / "diagnostics")

    exit_code, reports = validate_source_family(
        "astronomy",
        2026,
        adapters={"moon-phases": PassingAdapter()},
        report_store=report_store,
        diagnostic_store=diagnostic_store,
        run_timestamp="2026-03-01T12-00-00Z",
    )

    json_report = tmp_path / "2026-03-01T12-00-00Z" / "validate.moon-phases.2026.json"
    diagnostic_summary = (
        tmp_path / "diagnostics" / "astronomy" / "2026" / "moon-phases" / "validate-summary.json"
    )
    assert exit_code == 0
    assert len(reports) == 1
    assert json_report.exists()
    assert diagnostic_summary.exists()
    assert reports[0].canary_ok is True
    assert '"canary_ok": true' in diagnostic_summary.read_text(encoding="utf-8")


def test_validate_source_family_returns_non_zero_for_failed_validation(tmp_path) -> None:
    exit_code, reports = validate_source_family(
        "astronomy",
        2026,
        adapters={"eclipses": FailingAdapter()},
        report_store=ReportStore(base_dir=tmp_path),
        diagnostic_store=DiagnosticStore(base_dir=tmp_path / "diagnostics"),
        run_timestamp="2026-03-01T12-00-00Z",
    )

    diagnostic_summary = (
        tmp_path / "diagnostics" / "astronomy" / "2026" / "eclipses" / "validate-summary.json"
    )
    assert exit_code == 1
    assert reports[0].status == "failed"
    assert reports[0].canary_ok is False
    assert diagnostic_summary.exists()
    assert '"reason": "required timing fields missing"' in diagnostic_summary.read_text(encoding="utf-8")


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


def test_fetch_source_family_writes_fetch_summary_diagnostics(tmp_path) -> None:
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
        diagnostic_store=DiagnosticStore(base_dir=tmp_path / "diagnostics"),
    )

    summary_path = tmp_path / "diagnostics" / "astronomy" / "2026" / "moon-phases" / "fetch-summary.json"
    assert len(results) == 1
    assert summary_path.exists()
    summary_text = summary_path.read_text(encoding="utf-8")
    assert '"raw_ref": "data/raw/astronomy/2026/moon-phases/response.json"' in summary_text


def test_fetch_source_family_writes_failure_diagnostics(tmp_path) -> None:
    with pytest.raises(ValueError, match="request timed out"):
        fetch_source_family(
            2026,
            adapters={"moon-phases": BrokenFetchAdapter()},
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
            diagnostic_store=DiagnosticStore(base_dir=tmp_path / "diagnostics"),
        )

    failure_path = tmp_path / "diagnostics" / "astronomy" / "2026" / "moon-phases" / "fetch-failure.json"
    assert failure_path.exists()
    failure_text = failure_path.read_text(encoding="utf-8")
    assert '"failure_stage": "fetch"' in failure_text
    assert '"reason": "request timed out"' in failure_text


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


def test_eclipse_review_flow_requires_manual_acceptance_before_build(tmp_path) -> None:
    adapter = build_adapter(tmp_path)
    candidate_store = CandidateStore(base_dir=tmp_path / "normalized")
    catalog_store = CatalogStore(base_dir=tmp_path / "accepted")
    report_store = ReportStore(base_dir=tmp_path / "reports")
    sequence_store = SequenceStore(base_dir=tmp_path / "sequences")
    manifest = CalendarManifest(
        name="astronomy-eclipses",
        output=str(tmp_path / "eclipses.ics"),
        calendar_name="Eclipses",
        calendar_description="Solar and lunar eclipses with exact astronomical timing",
        variant_policy="default",
        source_types=["astronomy"],
        event_types=["eclipse"],
    )

    raw_result = adapter.fetch(2026)
    normalized_results = normalize_source_family(
        "astronomy",
        2026,
        adapters={"eclipses": adapter},
        raw_results=[raw_result],
        candidate_store=candidate_store,
        diagnostic_store=DiagnosticStore(base_dir=tmp_path / "diagnostics"),
    )
    candidates = normalized_results[0][1]

    reconcile_report, written_paths = reconcile_calendar(
        manifest=manifest,
        year=2026,
        candidate_store=candidate_store,
        catalog_store=catalog_store,
        report_store=report_store,
        run_timestamp="2026-03-02T12-00-00Z",
    )

    assert reconcile_report.review_report_path is not None
    assert any(path.name == "review.astronomy-eclipses.md" for path in written_paths)
    assert catalog_store.load("astronomy", 2026, "eclipses") == []

    accepted_records = []
    for candidate in candidates:
        accepted_candidate = candidate.to_dict()
        accepted_candidate["metadata"]["description_review"] = {
            "status": "accepted",
            "reviewed_at": "2026-03-02T13:00:00Z",
            "reviewer": "tester",
            "edited": False,
            "resolution": "accepted",
            "note": "Accepted generated copy.",
        }
        accepted_records.append(
            AcceptedRecord(
                occurrence_id=candidate.occurrence_id,
                revision=1,
                status="active",
                accepted_at="2026-03-02T13:00:00Z",
                superseded_at=None,
                change_reason="Accepted after review",
                content_hash=candidate.content_hash,
                source_adapter=candidate.source_adapter,
                detail_url=candidate.detail_url,
                record=accepted_candidate,
            )
        )
    catalog_store.save("astronomy", 2026, "eclipses", accepted_records)

    build_report, _ = build_calendar(
        manifest=manifest,
        catalog_store=catalog_store,
        sequence_store=sequence_store,
        report_store=report_store,
        run_timestamp="2026-03-02T13-30-00Z",
    )

    calendar = Calendar.from_ical(Path(build_report.output_path).read_bytes())
    events = [component for component in calendar.walk() if component.name == "VEVENT"]

    assert build_report.event_count == 3
    assert len(events) == 3
    assert any("At least part of the eclipse is visible across" in str(event["DESCRIPTION"]) for event in events)


def test_normalize_source_family_writes_failure_diagnostics_when_candidate_save_fails(
    tmp_path,
) -> None:
    with pytest.raises(OSError, match="unable to persist candidates"):
        normalize_source_family(
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
            candidate_store=BrokenCandidateStore(base_dir=tmp_path / "normalized"),
            diagnostic_store=DiagnosticStore(base_dir=tmp_path / "diagnostics"),
        )

    summary_path = tmp_path / "diagnostics" / "astronomy" / "2026" / "moon-phases" / "normalize-summary.json"
    failure_path = tmp_path / "diagnostics" / "astronomy" / "2026" / "moon-phases" / "normalize-failure.json"
    candidate_path = tmp_path / "normalized" / "astronomy" / "2026" / "moon-phases.json"

    assert summary_path.exists()
    assert failure_path.exists()
    assert not candidate_path.exists()
    failure_text = failure_path.read_text(encoding="utf-8")
    assert '"reason": "unable to persist candidates"' in failure_text
