"""Fetch orchestration for source families."""

from __future__ import annotations

from collections.abc import Mapping

from ..models import RawFetchResult, ValidationReport
from ..repositories import DiagnosticStore


def fetch_source_family(
    year: int,
    adapters: Mapping[str, object],
    validation_reports: list[ValidationReport],
    diagnostic_store: DiagnosticStore | None = None,
) -> list[RawFetchResult]:
    failed_reports = [report for report in validation_reports if report.status != "passed"]
    if failed_reports:
        reasons = ", ".join(report.source_name for report in failed_reports)
        raise RuntimeError(f"Refusing to fetch after validation failure: {reasons}")

    diagnostic_store = diagnostic_store or DiagnosticStore()
    results: list[RawFetchResult] = []
    for adapter in adapters.values():
        try:
            result = adapter.fetch(year)
        except Exception as exc:
            diagnostic_store.write_json(
                getattr(adapter, "source_type", ""),
                year,
                getattr(adapter, "source_name", ""),
                "fetch-failure.json",
                {
                    "source_name": getattr(adapter, "source_name", ""),
                    "source_type": getattr(adapter, "source_type", ""),
                    "year": year,
                    "source_adapter": getattr(adapter, "source_adapter", ""),
                    "source_url": getattr(adapter, "source_url", ""),
                    "failure_stage": "fetch",
                    "reason": str(exc),
                },
            )
            raise
        diagnostic_store.write_json(
            getattr(adapter, "source_type", ""),
            year,
            result.source_name,
            "fetch-summary.json",
            {
                "source_name": result.source_name,
                "source_type": getattr(adapter, "source_type", ""),
                "year": year,
                "source_adapter": getattr(adapter, "source_adapter", ""),
                "source_url": result.source_url,
                "raw_ref": result.raw_ref,
                "fetched_at": result.fetched_at,
                "metadata": result.metadata,
            },
        )
        results.append(result)

    return results
