"""Protocols for astronomy adapters."""

from __future__ import annotations

from typing import Protocol

from ...models import CandidateRecord, RawFetchResult, ValidationReport


class SourceAdapter(Protocol):
    source_name: str
    source_type: str

    def validate(self, year: int) -> ValidationReport: ...

    def fetch(self, year: int) -> RawFetchResult: ...

    def normalize(
        self,
        year: int,
        raw_result: RawFetchResult,
    ) -> list[CandidateRecord]: ...
