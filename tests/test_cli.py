from __future__ import annotations

from astronomical_calendars.cli import main
from astronomical_calendars.models import RawFetchResult, ValidationReport


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
        "astronomical_calendars.services.stub_service.ASTRONOMY_ADAPTERS",
        {"moon-phases": CliAdapter()},
    )
    exit_code = main(["run", "--calendar", "astronomy-all", "--year", "2026"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "validate astronomy year=2026" in captured.out
    assert "reconcile astronomy-all year=2026" in captured.out
    assert "build astronomy-all variant_policy=default" in captured.out


def test_build_command_uses_manifest_default_variant_policy(capsys) -> None:
    exit_code = main(["build", "--calendar", "astronomy-eclipses"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "build astronomy-eclipses variant_policy=default" in captured.out
