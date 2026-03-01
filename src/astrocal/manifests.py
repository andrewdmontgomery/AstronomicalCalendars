"""Manifest loading utilities."""

from __future__ import annotations

from pathlib import Path

import tomllib

from .models import CalendarManifest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = PROJECT_ROOT / "config" / "calendars"


def load_manifest(name: str) -> CalendarManifest:
    manifest_path = MANIFEST_DIR / f"{name}.toml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Unknown calendar manifest: {name}")

    with manifest_path.open("rb") as handle:
        data = tomllib.load(handle)

    return CalendarManifest(
        name=data["name"],
        output=data["output"],
        calendar_name=data["calendar_name"],
        calendar_description=data["calendar_description"],
        variant_policy=data["variant_policy"],
        source_validation_policy=data["source_validation_policy"],
        reconciliation_mode=data["reconciliation_mode"],
        correction_mode=data["correction_mode"],
        stop_on_source_failure=data["stop_on_source_failure"],
        stop_on_conflict=data["stop_on_conflict"],
        source_types=list(data.get("source_types", [])),
        event_types=list(data.get("event_types", [])),
        bodies=list(data.get("bodies", [])),
        tags=list(data.get("tags", [])),
    )
