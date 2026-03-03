"""Pipeline report models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ValidationReport:
    source_name: str
    year: int
    status: str
    validated_at: str
    checks: list[str] = field(default_factory=list)
    reason: str | None = None
    canary_ok: bool = True
    detail_url_ok: bool = True
    source_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RawFetchResult:
    source_name: str
    year: int
    fetched_at: str
    raw_ref: str
    source_url: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReconciliationReport:
    calendar_name: str
    year: int
    generated_at: str
    review_report_path: str | None = None
    new_occurrences: list[str] = field(default_factory=list)
    unchanged_occurrences: list[str] = field(default_factory=list)
    changed_occurrences: list[str] = field(default_factory=list)
    suspected_removals: list[str] = field(default_factory=list)
    validation_failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BuildReport:
    calendar_name: str
    generated_at: str
    output_path: str
    event_count: int
    sequence_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
