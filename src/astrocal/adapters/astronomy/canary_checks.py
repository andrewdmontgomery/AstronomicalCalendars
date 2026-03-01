"""Small reusable canary checks for astronomy source validation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


def required_fields(sample: Mapping[str, object], fields: Iterable[str]) -> str | None:
    missing = sorted(set(fields) - set(sample))
    if missing:
        return f"missing required fields: {', '.join(missing)}"
    return None


def non_empty_records(records: list[object], label: str) -> str | None:
    if records:
        return None
    return f"{label} missing"
