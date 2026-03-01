"""USNO seasons adapter."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Protocol

import requests

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
    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> HttpResponse: ...


SEASON_NAMES = {
    "March equinox": ("march-equinox", "March Equinox"),
    "June solstice": ("june-solstice", "June Solstice"),
    "September equinox": ("september-equinox", "September Equinox"),
    "December solstice": ("december-solstice", "December Solstice"),
}


class SeasonsAdapter:
    source_name = "seasons"
    source_type = "astronomy"
    source_adapter = "usno-seasons-v1"
    source_url = "https://aa.usno.navy.mil/api/seasons"

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
            data = payload.get("data", [])
            if not data:
                return self._failed_report(year, "data missing")

            sample = data[0]
            required_fields = {"phenom", "year", "month", "day", "time"}
            missing = sorted(required_fields - set(sample))
            if missing:
                return self._failed_report(
                    year,
                    f"missing required fields: {', '.join(missing)}",
                )

            if not _detail_url_for_season(
                sample["phenom"],
                sample["year"],
                sample["month"],
                sample["day"],
            ):
                return self._failed_report(year, "detail URL derivation failed")
        except Exception as exc:  # pragma: no cover
            return self._failed_report(year, str(exc))

        return ValidationReport(
            source_name=self.source_name,
            year=year,
            status="passed",
            validated_at=self._now_provider(),
            checks=[
                "reachable",
                "required timing fields present",
                "detail url resolved",
            ],
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
            "usno-seasons",
            "response.json",
            json.dumps(payload, indent=2, sort_keys=True),
        )
        return RawFetchResult(
            source_name=self.source_name,
            year=year,
            fetched_at=self._now_provider(),
            raw_ref=_raw_ref_for_path(raw_path),
            source_url=self.source_url,
            metadata={"record_count": len(payload.get("data", []))},
        )

    def normalize(self, year: int, raw_result: RawFetchResult) -> list[CandidateRecord]:
        raw_path = self._raw_store.dir_for(self.source_type, year, "usno-seasons") / "response.json"
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
        for season in payload.get("data", []):
            start = _iso_timestamp_for_record(season)
            season_slug, title = SEASON_NAMES[season["phenom"]]
            detail_url = _detail_url_for_season(
                season["phenom"],
                season["year"],
                season["month"],
                season["day"],
            )
            group_id = (
                f"astronomy/season-marker/"
                f"{season['year']}-{season['month']:02d}-{season['day']:02d}/{season_slug}"
            )
            occurrence_id = f"{group_id}/default"
            candidate = CandidateRecord(
                group_id=group_id,
                occurrence_id=occurrence_id,
                source_type=self.source_type,
                body="sun",
                event_type="season-marker",
                variant="default",
                is_default=True,
                title=title,
                summary=title,
                description=f"{title} at exact astronomical timing.",
                start=start,
                end=None,
                all_day=False,
                timezone="UTC",
                categories=["Astronomy", "Season"],
                tags=["season-marker", season_slug],
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
                metadata={
                    "source_id": season.get("id"),
                    "phenom": season["phenom"],
                },
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
            detail_url_ok=False,
            source_url=self.source_url,
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_timestamp_for_record(record: dict[str, Any]) -> str:
    hours, minutes = str(record["time"]).split(":")
    timestamp = datetime(
        int(record["year"]),
        int(record["month"]),
        int(record["day"]),
        int(hours),
        int(minutes),
        tzinfo=timezone.utc,
    )
    return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def _detail_url_for_season(phenom: str, year: int, month: int, day: int) -> str:
    season_slug = SEASON_NAMES.get(phenom, ("", ""))[0]
    if not season_slug:
        return ""
    return (
        "https://in-the-sky.org/news.php?id="
        f"{year:04d}{month:02d}{day:02d}_07_100"
        f"&season={season_slug}"
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
