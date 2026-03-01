"""Temporary service implementations used while the pipeline is being built."""

from __future__ import annotations

import argparse
import tempfile
from contextlib import contextmanager, nullcontext
from pathlib import Path

from ..adapters import ASTRONOMY_ADAPTERS
from ..manifests import load_manifest
from ..repositories import ReportStore
from ..services.fetch_service import fetch_source_family
from ..services.normalize_service import normalize_source_family
from ..services.validation_service import validate_source_family


def validate_command(args: argparse.Namespace) -> int:
    print(f"validate {args.source_family} year={args.year}")
    with _report_store_context(args.report_dir) as report_store:
        exit_code, reports = validate_source_family(
            args.source_family,
            args.year,
            adapters=ASTRONOMY_ADAPTERS,
            report_store=report_store,
        )
    _print_validation_reports(reports, args.year)
    return exit_code


def fetch_command(args: argparse.Namespace) -> int:
    print(f"fetch {args.source_family} year={args.year}")
    with _report_store_context(args.report_dir) as report_store:
        exit_code, reports = validate_source_family(
            args.source_family,
            args.year,
            adapters=ASTRONOMY_ADAPTERS,
            report_store=report_store,
        )
    _print_validation_reports(reports, args.year)
    if exit_code:
        return exit_code

    raw_results = fetch_source_family(args.year, adapters=ASTRONOMY_ADAPTERS, validation_reports=reports)
    for result in raw_results:
        print(f"fetch {result.source_name} raw_ref={result.raw_ref} year={args.year}")
    return 0


def normalize_command(args: argparse.Namespace) -> int:
    print(f"normalize {args.source_family} year={args.year}")
    with _report_store_context(args.report_dir) as report_store:
        exit_code, reports = validate_source_family(
            args.source_family,
            args.year,
            adapters=ASTRONOMY_ADAPTERS,
            report_store=report_store,
        )
    _print_validation_reports(reports, args.year)
    if exit_code:
        return exit_code

    raw_results = fetch_source_family(args.year, adapters=ASTRONOMY_ADAPTERS, validation_reports=reports)
    normalized_results = normalize_source_family(
        args.source_family,
        args.year,
        adapters=ASTRONOMY_ADAPTERS,
        raw_results=raw_results,
    )
    for source_name, candidates in normalized_results:
        print(f"normalize {source_name} candidates={len(candidates)} year={args.year}")
    return 0


def reconcile_command(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.calendar)
    report_dir = _report_dir_value(args.report_dir)
    print(
        f"reconcile {manifest.name} year={args.year} report_dir={report_dir} "
        f"stage={'no' if args.no_stage else 'yes'}"
    )
    return 0


def build_command(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.calendar)
    report_dir = _report_dir_value(args.report_dir)
    variant_policy = args.variant_policy or manifest.variant_policy
    print(
        f"build {manifest.name} variant_policy={variant_policy} report_dir={report_dir}"
    )
    return 0


def _report_dir_value(report_dir: Path | None) -> str:
    return str(report_dir) if report_dir is not None else "default"


def _print_validation_reports(reports: list, year: int) -> None:
    for report in reports:
        reason_suffix = f" reason={report.reason}" if report.reason else ""
        print(
            f"validate {report.source_name} status={report.status} year={year}{reason_suffix}"
        )


@contextmanager
def _report_store_context(report_dir: Path | None):
    if report_dir is not None:
        with nullcontext(ReportStore(base_dir=report_dir)) as report_store:
            yield report_store
        return

    with tempfile.TemporaryDirectory(prefix="astronomical-calendars-reports-") as temp_dir:
        yield ReportStore(base_dir=Path(temp_dir))
