"""Structured review bundle models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ReviewBundleEntry:
    occurrence_id: str
    group_id: str
    status: str
    source_name: str
    candidate_content_hash: str | None
    generated_content_hash: str | None
    allowed_actions: list[str] = field(default_factory=list)
    candidate: dict[str, Any] | None = None
    accepted: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ReviewBundleEntry":
        return cls(
            occurrence_id=payload["occurrence_id"],
            group_id=payload["group_id"],
            status=payload["status"],
            source_name=payload["source_name"],
            candidate_content_hash=payload.get("candidate_content_hash"),
            generated_content_hash=payload.get("generated_content_hash"),
            allowed_actions=list(payload.get("allowed_actions", [])),
            candidate=dict(payload["candidate"]) if isinstance(payload.get("candidate"), dict) else None,
            accepted=dict(payload["accepted"]) if isinstance(payload.get("accepted"), dict) else None,
        )


@dataclass(slots=True)
class ReviewBundle:
    calendar_name: str
    year: int
    generated_at: str
    entries: list[ReviewBundleEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "calendar_name": self.calendar_name,
            "year": self.year,
            "generated_at": self.generated_at,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ReviewBundle":
        return cls(
            calendar_name=payload["calendar_name"],
            year=int(payload["year"]),
            generated_at=payload["generated_at"],
            entries=[
                ReviewBundleEntry.from_dict(item)
                for item in payload.get("entries", [])
                if isinstance(item, dict)
            ],
        )
