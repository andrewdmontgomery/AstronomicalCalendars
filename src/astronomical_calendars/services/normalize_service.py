"""Normalization orchestration for source families."""

from __future__ import annotations

from collections.abc import Mapping

from ..models import CandidateRecord, RawFetchResult
from ..repositories import CandidateStore


def normalize_source_family(
    source_family: str,
    year: int,
    adapters: Mapping[str, object],
    raw_results: list[RawFetchResult],
    candidate_store: CandidateStore | None = None,
) -> list[tuple[str, list[CandidateRecord]]]:
    if source_family != "astronomy":
        raise ValueError(f"Unsupported source family: {source_family}")

    candidate_store = candidate_store or CandidateStore()
    raw_results_by_name = {result.source_name: result for result in raw_results}

    normalized_results: list[tuple[str, list[CandidateRecord]]] = []
    for name, adapter in adapters.items():
        raw_result = raw_results_by_name[name]
        candidates = adapter.normalize(year, raw_result)
        candidate_store.save(source_family, year, name, candidates)
        normalized_results.append((name, candidates))
    return normalized_results
