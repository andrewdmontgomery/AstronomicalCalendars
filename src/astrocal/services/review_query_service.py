"""Read-only helpers for persisted eclipse review bundles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..jsonio import read_json
from ..models import ReviewBundle, ReviewBundleEntry
from ..paths import PROJECT_ROOT


@dataclass(slots=True)
class PendingReview:
    report_path: Path
    bundle: ReviewBundle


def list_pending_reviews(report_dir: Path | None = None) -> list[PendingReview]:
    base_dir = _resolve_report_dir(report_dir)
    pending: list[PendingReview] = []
    for path in sorted(base_dir.glob("*/review.*.json")):
        pending.append(PendingReview(report_path=path, bundle=load_review_bundle(path)))
    return pending


def load_review_bundle(report_path: Path) -> ReviewBundle:
    resolved_path = _resolve_path(report_path)
    payload = read_json(resolved_path)
    return ReviewBundle.from_dict(payload)


def render_review_bundle(bundle: ReviewBundle, *, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(bundle.to_dict(), indent=2, sort_keys=True)

    lines = [
        f"Review bundle: {bundle.calendar_name}",
        f"Year: {bundle.year}",
        f"Generated at: {bundle.generated_at}",
        f"Entries: {len(bundle.entries)}",
        "",
    ]
    for entry in bundle.entries:
        lines.extend(_render_entry(entry))
    return "\n".join(lines).rstrip()


def _render_entry(entry: ReviewBundleEntry) -> list[str]:
    title = ""
    if entry.candidate is not None:
        title = str(entry.candidate.get("title", ""))
    elif entry.accepted is not None:
        accepted_record = entry.accepted.get("record", {})
        if isinstance(accepted_record, dict):
            title = str(accepted_record.get("title", ""))
    lines = [
        f"- {entry.occurrence_id}",
        f"  status={entry.status} group_id={entry.group_id}",
    ]
    if title:
        lines.append(f"  title={title}")
    lines.append(f"  allowed_actions={', '.join(entry.allowed_actions)}")
    return lines + [""]


def _resolve_report_dir(report_dir: Path | None) -> Path:
    if report_dir is None:
        return PROJECT_ROOT / "data" / "catalog" / "reports"
    return _resolve_path(report_dir)


def _resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path
