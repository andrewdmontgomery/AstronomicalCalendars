"""Accepted catalog record models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

DESCRIPTION_PROVENANCE_KEY = "description_provenance"
DESCRIPTION_REVIEW_KEY = "description_review"
GENERATED_CONTENT_HASH_KEY = "generated_content_hash"


@dataclass(slots=True)
class AcceptedRecord:
    occurrence_id: str
    revision: int
    status: str
    accepted_at: str
    superseded_at: str | None
    change_reason: str
    content_hash: str
    source_adapter: str
    detail_url: str
    record: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AcceptedRecord":
        return cls(
            occurrence_id=payload["occurrence_id"],
            revision=payload["revision"],
            status=payload["status"],
            accepted_at=payload["accepted_at"],
            superseded_at=payload.get("superseded_at"),
            change_reason=payload["change_reason"],
            content_hash=payload["content_hash"],
            source_adapter=payload["source_adapter"],
            detail_url=payload["detail_url"],
            record=dict(payload["record"]),
        )
