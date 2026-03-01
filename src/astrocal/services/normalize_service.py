"""Normalization orchestration for source families."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from ..models import CandidateRecord, RawFetchResult
from ..paths import PROJECT_ROOT
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
        "extraction_summary": _extraction_summary(
            source_name=source_name,
            raw_ref=raw_ref,
            candidates=candidates,
        ),
    }


def _extraction_summary(
    *,
    source_name: str,
    raw_ref: str,
    candidates: list[CandidateRecord],
) -> dict[str, object]:
    if source_name == "moon-phases":
        return {
            "phase_names": sorted({candidate.metadata.get("phase", "") for candidate in candidates if candidate.metadata.get("phase")}),
            "first_start": min((candidate.start for candidate in candidates), default=""),
            "last_start": max((candidate.start for candidate in candidates), default=""),
        }
    if source_name == "seasons":
        return {
            "titles_seen": sorted({candidate.title for candidate in candidates}),
            "ignored_non_season_row_count": _ignored_non_season_row_count(raw_ref),
        }
    if source_name == "eclipses":
        variant_counts: dict[str, int] = {}
        detail_urls_sample: list[str] = []
        for candidate in candidates:
            variant_counts[candidate.variant] = variant_counts.get(candidate.variant, 0) + 1
            if candidate.detail_url and candidate.detail_url not in detail_urls_sample:
                detail_urls_sample.append(candidate.detail_url)
        return {
            "titles_seen": sorted({candidate.title for candidate in candidates}),
            "variant_counts": variant_counts,
            "detail_urls_sample": detail_urls_sample[:3],
        }
    return {}


def _ignored_non_season_row_count(raw_ref: str) -> int:
    if not raw_ref:
        return 0
    raw_path = Path(raw_ref)
    if not raw_path.is_absolute():
        raw_path = PROJECT_ROOT / raw_ref
    if not raw_path.exists():
        return 0
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    rows = payload.get("data", [])
    season_rows = [
        row
        for row in rows
        if str(row.get("phenom", "")).strip().lower() in {"equinox", "solstice"}
    ]
    return max(len(rows) - len(season_rows), 0)
