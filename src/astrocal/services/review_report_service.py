"""Render human-review Markdown for eclipse changes."""

from __future__ import annotations

from ..models import AcceptedRecord, CalendarManifest, CandidateRecord


def render_review_report(
    *,
    manifest: CalendarManifest,
    year: int,
    new_candidates: list[CandidateRecord],
    changed_pairs: list[tuple[AcceptedRecord, CandidateRecord]],
    suspected_removals: list[AcceptedRecord],
) -> str:
    lines = [
        f"# {manifest.name} Eclipse Review",
        "",
        f"Year: {year}",
        "",
    ]

    if new_candidates:
        lines.extend(["## New Events", ""])
        for candidate in new_candidates:
            lines.extend(_candidate_section(candidate))

    if changed_pairs:
        lines.extend(["## Changed Events", ""])
        for accepted, candidate in changed_pairs:
            lines.extend(_candidate_section(candidate, accepted=accepted))

    if suspected_removals:
        lines.extend(["## Suspected Removals", ""])
        for record in suspected_removals:
            lines.extend(
                [
                    f"### {record.record.get('title', record.occurrence_id)}",
                    "",
                    f"- Occurrence ID: `{record.occurrence_id}`",
                    f"- Detail URL: {record.detail_url}",
                    f"- Current status: `{record.status}`",
                    f"- Last accepted description: {record.record.get('description', '')}",
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"


def _candidate_section(
    candidate: CandidateRecord,
    *,
    accepted: AcceptedRecord | None = None,
) -> list[str]:
    facts = candidate.metadata.get("description_generation", {}).get("facts", {})
    identity = facts.get("identity", {}) if isinstance(facts, dict) else {}
    timing = facts.get("timing", {}) if isinstance(facts, dict) else {}
    visibility = facts.get("visibility", {}) if isinstance(facts, dict) else {}
    full_duration = timing.get("full_duration", {}) if isinstance(timing, dict) else {}
    special_phase = timing.get("special_phase", {}) if isinstance(timing, dict) else {}
    partial_regions = visibility.get("partial_regions", []) if isinstance(visibility, dict) else []
    path_countries = visibility.get("path_countries", []) if isinstance(visibility, dict) else []

    lines = [
        f"### {candidate.title}",
        "",
        f"- Occurrence ID: `{candidate.occurrence_id}`",
        f"- Group ID: `{candidate.group_id}`",
        f"- Variant: `{candidate.variant}`",
        f"- Start: `{candidate.start}`",
        f"- End: `{candidate.end}`",
        f"- Detail URL: {candidate.detail_url}",
        f"- Raw snapshot: `{candidate.raw_ref}`",
        f"- Eclipse type: {identity.get('degree', '')} {identity.get('body', '')}".strip(),
        f"- Full duration: {full_duration.get('start', '')} to {full_duration.get('end', '')}",
    ]

    if special_phase:
        lines.append(
            f"- {special_phase.get('kind', 'special phase').capitalize()}: "
            f"{special_phase.get('start', '')} to {special_phase.get('end', '')}"
        )
    if partial_regions:
        lines.append(f"- Visibility regions: {', '.join(str(item) for item in partial_regions)}")
    if path_countries:
        lines.append(f"- Path countries: {', '.join(str(item) for item in path_countries)}")

    lines.extend(["", "Generated description:", "", candidate.description, ""])

    if accepted is not None:
        lines.extend(
            [
                "Previously accepted description:",
                "",
                str(accepted.record.get("description", "")),
                "",
            ]
        )

    return lines
