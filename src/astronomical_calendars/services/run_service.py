"""Top-level orchestration for the `run` command."""

from __future__ import annotations

import argparse
from types import SimpleNamespace

from .stub_service import (
    build_command,
    fetch_command,
    normalize_command,
    reconcile_command,
    validate_command,
)


def run_command(args: argparse.Namespace) -> int:
    source_family = "astronomy"
    validate_exit = validate_command(
        SimpleNamespace(
            source_family=source_family,
            year=args.year,
            report_dir=args.report_dir,
        )
    )
    if validate_exit:
        return validate_exit

    fetch_exit = fetch_command(
        SimpleNamespace(
            source_family=source_family,
            year=args.year,
            report_dir=args.report_dir,
        )
    )
    if fetch_exit:
        return fetch_exit

    normalize_exit = normalize_command(
        SimpleNamespace(
            source_family=source_family,
            year=args.year,
            report_dir=args.report_dir,
        )
    )
    if normalize_exit:
        return normalize_exit

    reconcile_exit = reconcile_command(
        SimpleNamespace(
            calendar=args.calendar,
            year=args.year,
            report_dir=args.report_dir,
            no_stage=args.no_stage,
        )
    )
    if reconcile_exit:
        return reconcile_exit

    return build_command(
        SimpleNamespace(
            calendar=args.calendar,
            variant_policy=args.variant_policy,
            report_dir=args.report_dir,
        )
    )
