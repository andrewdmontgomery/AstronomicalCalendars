"""Temporary service implementations used while the pipeline is being built."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..manifests import load_manifest


def validate_command(args: argparse.Namespace) -> int:
    print(f"validate {args.source_family} year={args.year}")
    return 0


def fetch_command(args: argparse.Namespace) -> int:
    print(f"fetch {args.source_family} year={args.year}")
    return 0


def normalize_command(args: argparse.Namespace) -> int:
    print(f"normalize {args.source_family} year={args.year}")
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
