"""Astronomy source adapter registrations."""

from __future__ import annotations

from .protocol import SourceAdapter
from .usno_moon_phases import MoonPhasesAdapter
from .usno_seasons import SeasonsAdapter

ASTRONOMY_ADAPTERS: dict[str, SourceAdapter] = {
    "moon-phases": MoonPhasesAdapter(),
    "seasons": SeasonsAdapter(),
}

__all__ = ["ASTRONOMY_ADAPTERS", "MoonPhasesAdapter", "SeasonsAdapter", "SourceAdapter"]
