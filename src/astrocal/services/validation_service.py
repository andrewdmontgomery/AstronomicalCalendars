"""Source validation orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Callable

from ..models import ValidationReport
from ..repositories import DiagnosticStore, ReportStore


def validate_source_family(
    source_family: str,
    year: int,
    adapters: Mapping[str, object],
    report_store: ReportStore | None = None,
    diagnostic_store: DiagnosticStore | None = None,
    run_timestamp: str | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> tuple[int, list[ValidationReport]]:
    if source_family != "astronomy":
        raise ValueError(f"Unsupported source family: {source_family}")

    reports: list[ValidationReport] = []
    for adapter in adapters.values():
        if progress_callback is not None:
            progress_callback(adapter.source_name)
        report = adapter.validate(year)
        reports.append(report)

    report_store = report_store or ReportStore()
    diagnostic_store = diagnostic_store or DiagnosticStore()
    run_timestamp = run_timestamp or _run_timestamp()
    for report in reports:
        report_name = f"validate.{report.source_name}.{year}"
        report_store.write_json_report(run_timestamp, report_name, report.to_dict())
        diagnostic_store.write_json(
            source_family,
            year,
            report.source_name,
            "validate-summary.json",
            {
                "source_name": report.source_name,
                "source_type": source_family,
                "year": year,
                "status": report.status,
                "validated_at": report.validated_at,
                "reason": report.reason,
                "canary_ok": report.canary_ok,
                "detail_url_ok": report.detail_url_ok,
                "checks": report.checks,
                "source_url": report.source_url,
            },
        )

    exit_code = 0 if all(report.status == "passed" for report in reports) else 1
    return exit_code, reports


def _run_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
