"""Fetch orchestration for source families."""

from __future__ import annotations

from collections.abc import Mapping

from ..models import RawFetchResult, ValidationReport


def fetch_source_family(
    year: int,
    adapters: Mapping[str, object],
    validation_reports: list[ValidationReport],
) -> list[RawFetchResult]:
    failed_reports = [report for report in validation_reports if report.status != "passed"]
    if failed_reports:
        reasons = ", ".join(report.source_name for report in failed_reports)
        raise RuntimeError(f"Refusing to fetch after validation failure: {reasons}")

    return [adapter.fetch(year) for adapter in adapters.values()]
