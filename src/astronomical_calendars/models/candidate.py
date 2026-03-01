"""Normalized candidate event models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ValidationResult:
    status: str
    validated_at: str
    reason: str | None
    checks: list[str] = field(default_factory=list)
    detail_url_ok: bool = True


@dataclass(slots=True)
class SourceReference:
    name: str
    url: str


@dataclass(slots=True)
class CandidateRecord:
    group_id: str
    occurrence_id: str
    source_type: str
    body: str
    event_type: str
    variant: str
    is_default: bool
    title: str
    summary: str
    description: str
    start: str
    end: str | None
    all_day: bool
    timezone: str
    categories: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    detail_url: str = ""
    source_adapter: str = ""
    source_validation: ValidationResult | None = None
    content_hash: str = ""
    first_seen_at: str = ""
    last_seen_at: str = ""
    candidate_status: str = "new"
    accepted_revision: int | None = None
    timing_source: SourceReference | None = None
    validation_sources: list[SourceReference] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CandidateRecord":
        return cls(
            group_id=payload["group_id"],
            occurrence_id=payload["occurrence_id"],
            source_type=payload["source_type"],
            body=payload["body"],
            event_type=payload["event_type"],
            variant=payload["variant"],
            is_default=payload["is_default"],
            title=payload["title"],
            summary=payload["summary"],
            description=payload["description"],
            start=payload["start"],
            end=payload.get("end"),
            all_day=payload["all_day"],
            timezone=payload["timezone"],
            categories=list(payload.get("categories", [])),
            tags=list(payload.get("tags", [])),
            detail_url=payload["detail_url"],
            source_adapter=payload["source_adapter"],
            source_validation=ValidationResult(**payload["source_validation"]),
            content_hash=payload["content_hash"],
            first_seen_at=payload["first_seen_at"],
            last_seen_at=payload["last_seen_at"],
            candidate_status=payload["candidate_status"],
            accepted_revision=payload.get("accepted_revision"),
            timing_source=SourceReference(**payload["timing_source"]),
            validation_sources=[
                SourceReference(**source) for source in payload.get("validation_sources", [])
            ],
            metadata=dict(payload.get("metadata", {})),
            raw_ref=payload["raw_ref"],
        )
