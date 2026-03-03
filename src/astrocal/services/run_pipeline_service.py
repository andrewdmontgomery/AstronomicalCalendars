"""Shared structured orchestration for the end-to-end calendar pipeline."""

from __future__ import annotations

import importlib
import os
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

from ..adapters import ASTRONOMY_ADAPTERS
from ..models import CalendarManifest, RunPipelineResult, SourceNormalizationSummary
from ..paths import PROJECT_ROOT
from ..repositories import CandidateStore, CatalogStore, DiagnosticStore, ReportStore, SequenceStore
from ..source_scope import select_manifest_adapters
from .build_ics_service import build_calendar
from .fetch_service import fetch_source_family
from .normalize_service import normalize_source_family
from .reconcile_service import reconcile_calendar
from .validation_service import validate_source_family


def run_calendar_pipeline(
    *,
    manifest: CalendarManifest,
    year: int,
    adapters: Mapping[str, object] | None = None,
    report_store: ReportStore | None = None,
    diagnostic_store: DiagnosticStore | None = None,
    candidate_store: CandidateStore | None = None,
    catalog_store: CatalogStore | None = None,
    sequence_store: SequenceStore | None = None,
    variant_policy: str | None = None,
    run_timestamp: str | None = None,
) -> RunPipelineResult:
    source_family = "astronomy"
    selected_adapters = select_manifest_adapters(manifest, adapters or _default_adapters())
    run_timestamp = run_timestamp or _run_timestamp()
    report_store = report_store or ReportStore()
    diagnostic_store = diagnostic_store or DiagnosticStore()
    candidate_store = candidate_store or CandidateStore()
    catalog_store = catalog_store or CatalogStore()
    sequence_store = sequence_store or SequenceStore()

    validate_exit, validation_reports = validate_source_family(
        source_family,
        year,
        adapters=selected_adapters,
        report_store=report_store,
        diagnostic_store=diagnostic_store,
        run_timestamp=run_timestamp,
    )

    written_paths = _validation_report_paths(report_store, run_timestamp, validation_reports)
    if validate_exit:
        return RunPipelineResult(
            calendar_name=manifest.name,
            year=year,
            generated_at=run_timestamp,
            report_dir=str(report_store._base_dir),
            validation_reports=validation_reports,
            reconciliation_report=None,
            stopped_for_review=False,
            written_paths=written_paths,
        )

    raw_results = fetch_source_family(
        year,
        adapters=selected_adapters,
        validation_reports=validation_reports,
        diagnostic_store=diagnostic_store,
    )
    written_paths.extend(_resolve_path_str(result.raw_ref) for result in raw_results)

    normalized_results = normalize_source_family(
        source_family,
        year,
        adapters=selected_adapters,
        raw_results=raw_results,
        candidate_store=candidate_store,
        diagnostic_store=diagnostic_store,
    )
    written_paths.extend(
        str(candidate_store.path_for(source_family, year, source_name))
        for source_name, _ in normalized_results
    )
    normalization_summaries = [
        SourceNormalizationSummary(source_name=source_name, candidate_count=len(candidates))
        for source_name, candidates in normalized_results
    ]

    reconciliation_report, reconcile_paths = reconcile_calendar(
        manifest=manifest,
        year=year,
        candidate_store=candidate_store,
        catalog_store=catalog_store,
        report_store=report_store,
        run_timestamp=run_timestamp,
    )
    written_paths.extend(str(path) for path in reconcile_paths)

    if reconciliation_report.review_report_path:
        return RunPipelineResult(
            calendar_name=manifest.name,
            year=year,
            generated_at=run_timestamp,
            report_dir=str(report_store._base_dir),
            validation_reports=validation_reports,
            raw_results=raw_results,
            normalized_results=normalization_summaries,
            reconciliation_report=reconciliation_report,
            build_report=None,
            stopped_for_review=True,
            written_paths=_unique_paths(written_paths),
        )

    build_report, build_paths = build_calendar(
        manifest=manifest,
        catalog_store=catalog_store,
        sequence_store=sequence_store,
        report_store=report_store,
        variant_policy=variant_policy or manifest.variant_policy,
        run_timestamp=run_timestamp,
    )
    written_paths.extend(str(path) for path in build_paths)

    return RunPipelineResult(
        calendar_name=manifest.name,
        year=year,
        generated_at=run_timestamp,
        report_dir=str(report_store._base_dir),
        validation_reports=validation_reports,
        raw_results=raw_results,
        normalized_results=normalization_summaries,
        reconciliation_report=reconciliation_report,
        build_report=build_report,
        stopped_for_review=False,
        written_paths=_unique_paths(written_paths),
    )


def _validation_report_paths(
    report_store: ReportStore,
    run_timestamp: str,
    reports: list,
) -> list[str]:
    return [
        str(report_store.run_dir(run_timestamp) / f"validate.{report.source_name}.{report.year}.json")
        for report in reports
    ]


def _resolve_path_str(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str(PROJECT_ROOT / path)


def _unique_paths(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _run_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _default_adapters() -> Mapping[str, object]:
    factory_spec = os.environ.get("ASTROCAL_ADAPTERS_FACTORY")
    if not factory_spec:
        return ASTRONOMY_ADAPTERS

    module_name, function_name = factory_spec.split(":", 1)
    module = importlib.import_module(module_name)
    factory = getattr(module, function_name)
    return factory()
