"""Top-level orchestration for the `run` command."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from ..adapters import ASTRONOMY_ADAPTERS
from ..manifests import load_manifest
from ..repositories import ReportStore
from .build_ics_service import build_calendar
from .fetch_service import fetch_source_family
from .normalize_service import normalize_source_family
from .reconcile_service import reconcile_calendar
from .stub_service import _print_validation_reports, _report_dir_value
from .validation_service import validate_source_family


def run_command(args: argparse.Namespace) -> int:
    source_family = "astronomy"
    manifest = load_manifest(args.calendar)
    run_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    report_dir = _report_dir_value(args.report_dir)
    report_store = ReportStore(base_dir=args.report_dir) if args.report_dir else ReportStore()

    print(f"validate {source_family} year={args.year}")
    validate_exit, reports = validate_source_family(
        source_family,
        args.year,
        adapters=ASTRONOMY_ADAPTERS,
        report_store=report_store,
        run_timestamp=run_timestamp,
    )
    _print_validation_reports(reports, args.year)
    if validate_exit:
        return validate_exit

    print(f"fetch {source_family} year={args.year}")
    raw_results = fetch_source_family(
        args.year,
        adapters=ASTRONOMY_ADAPTERS,
        validation_reports=reports,
    )
    for result in raw_results:
        print(f"fetch {result.source_name} raw_ref={result.raw_ref} year={args.year}")

    print(f"normalize {source_family} year={args.year}")
    normalized_results = normalize_source_family(
        source_family,
        args.year,
        adapters=ASTRONOMY_ADAPTERS,
        raw_results=raw_results,
    )
    for source_name, candidates in normalized_results:
        print(f"normalize {source_name} candidates={len(candidates)} year={args.year}")

    reconcile_report, _ = reconcile_calendar(
        manifest=manifest,
        year=args.year,
        report_store=report_store,
        run_timestamp=run_timestamp,
    )
    print(
        f"reconcile {manifest.name} year={args.year} report_dir={report_dir} "
        f"new={len(reconcile_report.new_occurrences)} "
        f"changed={len(reconcile_report.changed_occurrences)} "
        f"removed={len(reconcile_report.suspected_removals)}"
    )

    build_report, _ = build_calendar(
        manifest=manifest,
        report_store=report_store,
        variant_policy=args.variant_policy or manifest.variant_policy,
        run_timestamp=run_timestamp,
    )
    print(
        f"build {manifest.name} variant_policy={args.variant_policy or manifest.variant_policy} "
        f"report_dir={report_dir} events={build_report.event_count}"
    )
    return 0
