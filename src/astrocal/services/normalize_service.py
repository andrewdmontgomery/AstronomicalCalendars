"""Normalization orchestration for source families."""

from __future__ import annotations

from collections.abc import Mapping

from ..models import CandidateRecord, RawFetchResult
from ..repositories import CandidateStore, DiagnosticStore


def normalize_source_family(
    source_family: str,
    year: int,
    adapters: Mapping[str, object],
    raw_results: list[RawFetchResult],
    candidate_store: CandidateStore | None = None,
    diagnostic_store: DiagnosticStore | None = None,
) -> list[tuple[str, list[CandidateRecord]]]:
    if source_family != "astronomy":
        raise ValueError(f"Unsupported source family: {source_family}")

    candidate_store = candidate_store or CandidateStore()
    diagnostic_store = diagnostic_store or DiagnosticStore()
    raw_results_by_name = {result.source_name: result for result in raw_results}

    normalized_results: list[tuple[str, list[CandidateRecord]]] = []
    for name, adapter in adapters.items():
        raw_result = raw_results_by_name[name]
        try:
            candidates = adapter.normalize(year, raw_result)
        except Exception as exc:
            diagnostic_store.write_json(
                source_family,
                year,
                name,
                "normalize-failure.json",
                {
                    "source_name": name,
                    "source_type": source_family,
                    "year": year,
                    "source_adapter": getattr(adapter, "source_adapter", ""),
                    "source_url": getattr(adapter, "source_url", ""),
                    "raw_ref": raw_result.raw_ref,
                    "failure_stage": "normalize",
                    "reason": str(exc),
                },
            )
            raise
        candidate_store.save(source_family, year, name, candidates)
        diagnostic_store.write_json(
            source_family,
            year,
            name,
            "normalize-summary.json",
            _normalize_summary(
                source_type=source_family,
                year=year,
                source_name=name,
                source_adapter=getattr(adapter, "source_adapter", ""),
                source_url=getattr(adapter, "source_url", ""),
                raw_ref=raw_result.raw_ref,
                candidates=candidates,
            ),
        )
        normalized_results.append((name, candidates))
    return normalized_results


def _normalize_summary(
    *,
    source_type: str,
    year: int,
    source_name: str,
    source_adapter: str,
    source_url: str,
    raw_ref: str,
    candidates: list[CandidateRecord],
) -> dict[str, object]:
    event_types = sorted({candidate.event_type for candidate in candidates})
    variants = sorted({candidate.variant for candidate in candidates})
    titles_sample = [candidate.title for candidate in candidates[:5]]
    metadata_keys = sorted({key for candidate in candidates for key in candidate.metadata})
    canary_ok = all(
        candidate.source_validation is None or candidate.source_validation.status == "passed"
        for candidate in candidates
    )
    return {
        "source_name": source_name,
        "source_type": source_type,
        "year": year,
        "source_adapter": source_adapter,
        "source_url": source_url,
        "raw_ref": raw_ref,
        "candidate_count": len(candidates),
        "event_types": event_types,
        "variants": variants,
        "titles_sample": titles_sample,
        "occurrence_ids_sample": [candidate.occurrence_id for candidate in candidates[:5]],
        "detail_url_count": sum(1 for candidate in candidates if candidate.detail_url),
        "metadata_keys": metadata_keys,
        "canary_ok": canary_ok,
    }
