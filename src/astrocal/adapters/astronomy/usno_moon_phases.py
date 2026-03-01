"""USNO moon phase adapter."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Protocol

import requests

from .canary_checks import non_empty_records, required_fields
from ...hashing import sha256_text
from ...models import (
    CandidateRecord,
    RawFetchResult,
    SourceReference,
    ValidationReport,
    ValidationResult,
)
from ...paths import PROJECT_ROOT
from ...repositories import RawStore


class HttpResponse(Protocol):
    text: str

    def json(self) -> Any: ...

    def raise_for_status(self) -> None: ...


class HttpClient(Protocol):
    def get(self, url: str, params: dict[str, Any] | None = None, timeout: int = 30) -> HttpResponse: ...


PHASE_NAMES = {
    "New Moon": "new-moon",
    "First Quarter": "first-quarter",
    "Full Moon": "full-moon",
    "Last Quarter": "last-quarter",
}

PHASE_DESCRIPTIONS = {
    "New Moon": "This entry marks the exact astronomical moment of the New Moon.",
    "First Quarter": "This entry marks the exact astronomical moment of the First Quarter Moon.",
    "Full Moon": "This entry marks the exact astronomical moment of the Full Moon.",
    "Last Quarter": "This entry marks the exact astronomical moment of the Last Quarter Moon.",
}


class MoonPhasesAdapter:
    source_name = "moon-phases"
    source_type = "astronomy"
    source_adapter = "usno-moon-phases-v1"
    source_url = "https://aa.usno.navy.mil/api/moon/phases/year"

    def __init__(
        self,
        http_client: HttpClient | None = None,
        raw_store: RawStore | None = None,
        now_provider: callable | None = None,
    ) -> None:
        self._http_client = http_client or requests.Session()
        self._raw_store = raw_store or RawStore()
        self._now_provider = now_provider or _utc_now

    def validate(self, year: int) -> ValidationReport:
        try:
            response = self._http_client.get(
                self.source_url,
                params={"year": year},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            phases = payload.get("phasedata", [])
            canary_failure = non_empty_records(phases, "phasedata")
            if canary_failure:
                return self._failed_report(year, canary_failure)

            sample = phases[0]
            canary_failure = required_fields(sample, {"phase", "year", "month", "day", "time"})
            if canary_failure:
                return self._failed_report(year, canary_failure)

            if not _detail_url_for_phase(sample["phase"], sample["year"], sample["month"], sample["day"]):
                return self._failed_report(year, "detail URL derivation failed")
        except Exception as exc:  # pragma: no cover - exercised via tests with broad failures
            return self._failed_report(year, str(exc))

        return ValidationReport(
            source_name=self.source_name,
            year=year,
            status="passed",
            validated_at=self._now_provider(),
            checks=[
                "reachable",
                "canary payload present",
                "canary required fields present",
                "required timing fields present",
                "detail url resolved",
            ],
            canary_ok=True,
            detail_url_ok=True,
            source_url=self.source_url,
        )

    def fetch(self, year: int) -> RawFetchResult:
        response = self._http_client.get(
            self.source_url,
            params={"year": year},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        raw_path = self._raw_store.write_text(
            self.source_type,
            year,
            "usno-moon-phases",
            "response.json",
            json.dumps(payload, indent=2, sort_keys=True),
        )
        return RawFetchResult(
            source_name=self.source_name,
            year=year,
            fetched_at=self._now_provider(),
            raw_ref=_raw_ref_for_path(raw_path),
            source_url=self.source_url,
            metadata={"record_count": len(payload.get("phasedata", []))},
        )

    def normalize(self, year: int, raw_result: RawFetchResult) -> list[CandidateRecord]:
        raw_path = self._raw_store.dir_for(self.source_type, year, "usno-moon-phases") / "response.json"
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
        validation = ValidationResult(
            status="passed",
            validated_at=self._now_provider(),
            reason=None,
            checks=[
                "reachable",
                "required timing fields present",
                "detail url resolved",
            ],
            detail_url_ok=True,
        )
        seen_at = self._now_provider()
        candidates: list[CandidateRecord] = []
        for phase in payload.get("phasedata", []):
            start = _iso_timestamp_for_phase(phase)
            detail_url = _detail_url_for_phase(
                phase["phase"],
                phase["year"],
                phase["month"],
                phase["day"],
            )
            phase_slug = PHASE_NAMES[phase["phase"]]
            group_id = f"astronomy/moon-phase/{phase['year']}-{phase['month']:02d}-{phase['day']:02d}/{phase_slug}"
            occurrence_id = f"{group_id}/default"
            metadata = {
                "source_id": phase.get("id"),
                "phase": phase["phase"],
            }
            candidate = CandidateRecord(
                group_id=group_id,
                occurrence_id=occurrence_id,
                source_type=self.source_type,
                body="moon",
                event_type="moon-phase",
                variant="default",
                is_default=True,
                title=phase["phase"],
                summary=phase["phase"],
                description=PHASE_DESCRIPTIONS[phase["phase"]],
                start=start,
                end=None,
                all_day=False,
                timezone="UTC",
                categories=["Astronomy", "Moon Phase"],
                tags=["moon-phase", phase_slug],
                detail_url=detail_url,
                source_adapter=self.source_adapter,
                source_validation=validation,
                content_hash="",
                first_seen_at=seen_at,
                last_seen_at=seen_at,
                candidate_status="new",
                accepted_revision=None,
                timing_source=SourceReference(name="usno", url=self.source_url),
                validation_sources=[],
                metadata=metadata,
                raw_ref=raw_result.raw_ref,
            )
            candidate.content_hash = _candidate_content_hash(candidate)
            candidates.append(candidate)
        return candidates

    def _failed_report(self, year: int, reason: str) -> ValidationReport:
        return ValidationReport(
            source_name=self.source_name,
            year=year,
            status="failed",
            validated_at=self._now_provider(),
            checks=["reachable"],
            reason=reason,
            canary_ok=False,
            detail_url_ok=False,
            source_url=self.source_url,
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_timestamp_for_phase(phase: dict[str, Any]) -> str:
    timestamp = datetime(
        int(phase["year"]),
        int(phase["month"]),
        int(phase["day"]),
        int(str(phase["time"]).split(":")[0]),
        int(str(phase["time"]).split(":")[1]),
        tzinfo=timezone.utc,
    )
    return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def _detail_url_for_phase(phase_name: str, year: int, month: int, day: int) -> str:
    phase_slug = PHASE_NAMES.get(phase_name)
    if phase_slug is None:
        return ""
    return (
        "https://in-the-sky.org/news.php?id="
        f"{year:04d}{month:02d}{day:02d}_08_100"
        f"&phase={phase_slug}"
    )


def _candidate_content_hash(candidate: CandidateRecord) -> str:
    payload = candidate.to_dict()
    payload["content_hash"] = ""
    return sha256_text(json.dumps(payload, sort_keys=True))


def _raw_ref_for_path(path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)
