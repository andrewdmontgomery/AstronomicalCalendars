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
    source_validation_policy: str
    reconciliation_mode: str
    correction_mode: str
    stop_on_source_failure: bool
    stop_on_conflict: bool
    source_types: list[str] = field(default_factory=list)
    event_types: list[str] = field(default_factory=list)
    bodies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
