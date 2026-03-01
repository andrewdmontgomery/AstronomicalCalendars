"""Astronomy source adapter registrations."""

from __future__ import annotations

from .protocol import SourceAdapter
from .usno_moon_phases import MoonPhasesAdapter
from .usno_seasons import SeasonsAdapter
from .timeanddate_eclipses import EclipsesAdapter

ASTRONOMY_ADAPTERS: dict[str, SourceAdapter] = {
    "moon-phases": MoonPhasesAdapter(),
    "seasons": SeasonsAdapter(),
    "eclipses": EclipsesAdapter(),
}

__all__ = [
    "ASTRONOMY_ADAPTERS",
    "EclipsesAdapter",
    "MoonPhasesAdapter",
    "SeasonsAdapter",
    "SourceAdapter",
]
