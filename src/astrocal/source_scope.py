"""Helpers for limiting orchestration to the sources a manifest actually uses."""

from __future__ import annotations

from collections.abc import Mapping

from .models import CalendarManifest


def select_manifest_adapters(
    manifest: CalendarManifest,
    adapters: Mapping[str, object],
) -> dict[str, object]:
    if not manifest.source_names:
        return dict(adapters)

    selected: dict[str, object] = {}
    for source_name in manifest.source_names:
        adapter = adapters.get(source_name)
        if adapter is None:
            raise KeyError(f"Manifest {manifest.name} references unknown source: {source_name}")
        selected[source_name] = adapter
    return selected


def manifest_source_names(
    manifest: CalendarManifest,
    available_source_names: list[str],
) -> list[str]:
    if manifest.source_names:
        return [name for name in available_source_names if name in manifest.source_names]
    return list(available_source_names)
