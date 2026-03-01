"""Astronomy source adapter registrations."""

from __future__ import annotations

from .protocol import SourceAdapter
from .usno_moon_phases import MoonPhasesAdapter

ASTRONOMY_ADAPTERS: dict[str, SourceAdapter] = {
    "moon-phases": MoonPhasesAdapter(),
}

__all__ = ["ASTRONOMY_ADAPTERS", "MoonPhasesAdapter", "SourceAdapter"]
