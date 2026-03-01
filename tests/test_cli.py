from __future__ import annotations

from astronomical_calendars.cli import main
from astronomical_calendars.models import BuildReport, RawFetchResult, ReconciliationReport, ValidationReport


class CliAdapter:
    source_name = "moon-phases"
    source_type = "astronomy"

    def validate(self, year: int) -> ValidationReport:
        return ValidationReport(
            source_name=self.source_name,
            year=year,
            status="passed",
            validated_at="2026-03-01T00:00:00Z",
            checks=["reachable"],
            source_url="https://example.com/moon-phases",
        )

    def fetch(self, year: int) -> RawFetchResult:
        return RawFetchResult(
            source_name=self.source_name,
            year=year,
            fetched_at="2026-03-01T00:00:00Z",
            raw_ref="data/raw/astronomy/2026/usno-moon-phases/response.json",
            source_url="https://example.com/moon-phases",
        )

    def normalize(self, year: int, raw_result: RawFetchResult) -> list[object]:
        return []


def test_run_command_executes_pipeline(capsys, mocker) -> None:
    mocker.patch(
        "astronomical_calendars.services.run_service.ASTRONOMY_ADAPTERS",
        {"moon-phases": CliAdapter()},
    )
    mocker.patch(
        "astronomical_calendars.services.run_service.reconcile_calendar",
        return_value=(
            ReconciliationReport(
                calendar_name="astronomy-all",
                year=2026,
                generated_at="2026-03-01T00:00:00Z",
            ),
            [],
        ),
    )
    mocker.patch(
        "astronomical_calendars.services.run_service.build_calendar",
        return_value=(
            BuildReport(
                calendar_name="astronomy-all",
                generated_at="2026-03-01T00:00:00Z",
                output_path="calendars/astronomical-events.ics",
                event_count=3,
                sequence_path="data/state/sequences/astronomy-all.json",
            ),
            [],
        ),
    )

    exit_code = main(["run", "--calendar", "astronomy-all", "--year", "2026"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "validate astronomy year=2026" in captured.out
    assert "fetch astronomy year=2026" in captured.out
    assert "normalize astronomy year=2026" in captured.out
    assert "reconcile astronomy-all year=2026" in captured.out
    assert "build astronomy-all variant_policy=default" in captured.out
    assert "stage=" not in captured.out


def test_build_command_uses_manifest_default_variant_policy(capsys, mocker) -> None:
    build_mock = mocker.patch(
        "astronomical_calendars.services.stub_service.build_calendar",
        return_value=(
            BuildReport(
                calendar_name="astronomy-eclipses",
                generated_at="2026-03-01T00:00:00Z",
                output_path="calendars/eclipses.ics",
                event_count=2,
                sequence_path="data/state/sequences/astronomy-eclipses.json",
            ),
            [],
        ),
    )

    exit_code = main(["build", "--calendar", "astronomy-eclipses"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "build astronomy-eclipses variant_policy=default" in captured.out
    assert "stage=" not in captured.out
    assert "data/catalog/reports" in str(build_mock.call_args.kwargs["report_store"]._base_dir)


def test_validate_command_writes_reports_only_when_report_dir_is_requested(
    capsys,
    mocker,
    tmp_path,
) -> None:
    mocker.patch(
        "astronomical_calendars.services.stub_service.ASTRONOMY_ADAPTERS",
        {"moon-phases": CliAdapter()},
    )

    exit_code = main(
        [
            "validate",
            "--year",
            "2026",
            "--report-dir",
            str(tmp_path),
            "astronomy",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "validate moon-phases status=passed year=2026" in captured.out
    assert list(tmp_path.glob("*/validate.moon-phases.2026.json"))
    assert list(tmp_path.glob("*/validate.moon-phases.2026.md"))


def test_run_command_uses_repo_report_store_by_default(capsys, mocker) -> None:
    mocker.patch(
        "astronomical_calendars.services.run_service.ASTRONOMY_ADAPTERS",
        {"moon-phases": CliAdapter()},
    )
    reconcile_mock = mocker.patch(
        "astronomical_calendars.services.run_service.reconcile_calendar",
        return_value=(
            ReconciliationReport(
                calendar_name="astronomy-all",
                year=2026,
                generated_at="2026-03-01T00:00:00Z",
            ),
            [],
        ),
    )
    mocker.patch(
        "astronomical_calendars.services.run_service.build_calendar",
        return_value=(
            BuildReport(
                calendar_name="astronomy-all",
                generated_at="2026-03-01T00:00:00Z",
                output_path="calendars/astronomical-events.ics",
                event_count=3,
                sequence_path="data/state/sequences/astronomy-all.json",
            ),
            [],
        ),
    )

    exit_code = main(["run", "--calendar", "astronomy-all", "--year", "2026"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "reconcile astronomy-all year=2026" in captured.out
    assert "data/catalog/reports" in str(reconcile_mock.call_args.kwargs["report_store"]._base_dir)


def test_reconcile_command_returns_non_zero_on_validation_failure(capsys, mocker) -> None:
    mocker.patch(
        "astronomical_calendars.services.stub_service.reconcile_calendar",
        return_value=(
            ReconciliationReport(
                calendar_name="astronomy-all",
                year=2026,
                generated_at="2026-03-01T00:00:00Z",
                validation_failures=["eclipses"],
            ),
            [],
        ),
    )

    exit_code = main(["reconcile", "--calendar", "astronomy-all", "--year", "2026"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "reconcile astronomy-all year=2026" in captured.out
