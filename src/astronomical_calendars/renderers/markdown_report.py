"""Markdown report rendering helpers."""

from __future__ import annotations

from ..models import BuildReport, ValidationReport


def render_validation_report(report: ValidationReport) -> str:
    lines = [
        f"# Validation Report: {report.source_name}",
        "",
        f"- Year: {report.year}",
        f"- Status: {report.status}",
        f"- Validated at: {report.validated_at}",
    ]

    if report.source_url:
        lines.append(f"- Source URL: {report.source_url}")
    if report.reason:
        lines.append(f"- Reason: {report.reason}")

    lines.extend(["", "## Checks"])
    for check in report.checks:
        lines.append(f"- {check}")

    return "\n".join(lines) + "\n"


def render_build_report(report: BuildReport) -> str:
    lines = [
        f"# Build Report: {report.calendar_name}",
        "",
        f"- Generated at: {report.generated_at}",
        f"- Output path: {report.output_path}",
        f"- Event count: {report.event_count}",
    ]
    if report.sequence_path:
        lines.append(f"- Sequence path: {report.sequence_path}")
    if report.staged_paths:
        lines.append(f"- Staged paths: {len(report.staged_paths)}")
    return "\n".join(lines) + "\n"
