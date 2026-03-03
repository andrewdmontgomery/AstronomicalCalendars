"""CLI presentation for the `run` command."""

from __future__ import annotations

import argparse

from ..manifests import load_manifest
from ..repositories import ReportStore
from .run_pipeline_service import run_calendar_pipeline
from .stub_service import _print_validation_reports, _report_dir_value


def run_command(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.calendar)
    report_store = ReportStore(base_dir=args.report_dir) if args.report_dir else ReportStore()
    result = run_calendar_pipeline(
        manifest=manifest,
        year=args.year,
        report_store=report_store,
        variant_policy=args.variant_policy or manifest.variant_policy,
    )
    report_dir = _report_dir_value(args.report_dir)

    print(f"validate astronomy year={args.year}")
    for report in result.validation_reports:
        print(f"validate {report.source_name} start year={args.year}")
    _print_validation_reports(result.validation_reports, args.year)
    if result.reconciliation_report is None:
        return 1

    print(f"fetch astronomy year={args.year}")
    for raw_result in result.raw_results:
        print(f"fetch {raw_result.source_name} raw_ref={raw_result.raw_ref} year={args.year}")

    print(f"normalize astronomy year={args.year}")
    for normalized_result in result.normalized_results:
        print(
            f"normalize {normalized_result.source_name} "
            f"candidates={normalized_result.candidate_count} year={args.year}"
        )

    reconcile_report = result.reconciliation_report
    review_suffix = ""
    if reconcile_report.review_report_path:
        review_suffix += f" review_report={reconcile_report.review_report_path}"
    if reconcile_report.review_bundle_path:
        review_suffix += f" review_bundle={reconcile_report.review_bundle_path}"
    print(
        f"reconcile {manifest.name} year={args.year} report_dir={report_dir} "
        f"new={len(reconcile_report.new_occurrences)} "
        f"changed={len(reconcile_report.changed_occurrences)} "
        f"removed={len(reconcile_report.suspected_removals)}{review_suffix}"
    )
    if result.stopped_for_review or result.build_report is None:
        return 0

    build_report = result.build_report
    print(
        f"build {manifest.name} variant_policy={args.variant_policy or manifest.variant_policy} "
        f"report_dir={report_dir} events={build_report.event_count}"
    )
    return 0
