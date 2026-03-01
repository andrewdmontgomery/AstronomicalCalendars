"""Source validation orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone

from ..models import ValidationReport
from ..repositories import ReportStore


def validate_source_family(
    source_family: str,
    year: int,
    adapters: Mapping[str, object],
    report_store: ReportStore | None = None,
    run_timestamp: str | None = None,
) -> tuple[int, list[ValidationReport]]:
    if source_family != "astronomy":
        raise ValueError(f"Unsupported source family: {source_family}")

    reports: list[ValidationReport] = []
    for adapter in adapters.values():
        report = adapter.validate(year)
        reports.append(report)

    report_store = report_store or ReportStore()
    run_timestamp = run_timestamp or _run_timestamp()
    for report in reports:
        report_name = f"validate.{report.source_name}.{year}"
        report_store.write_json_report(run_timestamp, report_name, report.to_dict())

    exit_code = 0 if all(report.status == "passed" for report in reports) else 1
    return exit_code, reports


def _run_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
