"""Calendar manifest model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CalendarManifest:
    name: str
    output: str
    calendar_name: str
    calendar_description: str
    variant_policy: str
    source_types: list[str] = field(default_factory=list)
    source_names: list[str] = field(default_factory=list)
    event_types: list[str] = field(default_factory=list)
    bodies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
