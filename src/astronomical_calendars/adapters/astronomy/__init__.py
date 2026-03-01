"""Astronomy source adapter registrations."""

from __future__ import annotations

from .protocol import SourceAdapter

ASTRONOMY_ADAPTERS: dict[str, SourceAdapter] = {}

__all__ = ["ASTRONOMY_ADAPTERS", "SourceAdapter"]
