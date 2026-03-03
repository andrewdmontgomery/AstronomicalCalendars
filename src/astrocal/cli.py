"""Command-line interface for the astronomical calendars pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from .services.run_service import run_command
from .services.stub_service import (
    build_command,
    fetch_command,
    list_pending_reviews_command,
    normalize_command,
    reconcile_command,
    show_review_command,
    validate_command,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="astrocal")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, handler in {
        "validate": validate_command,
        "fetch": fetch_command,
        "normalize": normalize_command,
    }.items():
        command_parser = subparsers.add_parser(name)
        command_parser.add_argument("source_family", choices=["astronomy"])
        command_parser.add_argument("--year", type=int, required=True)
        command_parser.add_argument("--report-dir", type=Path)
        command_parser.set_defaults(handler=handler)

    reconcile_parser = subparsers.add_parser("reconcile")
    reconcile_parser.add_argument("--calendar", required=True)
    reconcile_parser.add_argument("--year", type=int, required=True)
    reconcile_parser.add_argument("--report-dir", type=Path)
    reconcile_parser.set_defaults(handler=reconcile_command)

    list_pending_reviews_parser = subparsers.add_parser("list-pending-reviews")
    list_pending_reviews_parser.add_argument("--report-dir", type=Path)
    list_pending_reviews_parser.set_defaults(handler=list_pending_reviews_command)

    show_review_parser = subparsers.add_parser("show-review")
    show_review_parser.add_argument("--report", type=Path, required=True)
    show_review_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    show_review_parser.set_defaults(handler=show_review_command)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--calendar", required=True)
    build_parser.add_argument(
        "--variant-policy",
        choices=["default", "totality-only", "both"],
    )
    build_parser.add_argument("--report-dir", type=Path)
    build_parser.set_defaults(handler=build_command)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--calendar", required=True)
    run_parser.add_argument("--year", type=int, required=True)
    run_parser.add_argument(
        "--variant-policy",
        choices=["default", "totality-only", "both"],
    )
    run_parser.add_argument("--report-dir", type=Path)
    run_parser.set_defaults(handler=run_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))
