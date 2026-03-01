"""Markdown report rendering helpers."""

from __future__ import annotations

from ..models import ValidationReport


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
