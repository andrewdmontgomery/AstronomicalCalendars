"""timeanddate eclipse adapter."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import requests
from bs4 import BeautifulSoup

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

    def raise_for_status(self) -> None: ...


class HttpClient(Protocol):
    def get(self, url: str, timeout: int = 30) -> HttpResponse: ...


ECLIPSE_DETAIL_URLS = {
    2026: [
        "https://www.timeanddate.com/eclipse/lunar/2026-march-3",
        "https://www.timeanddate.com/eclipse/solar/2026-august-12",
        "https://www.timeanddate.com/eclipse/lunar/2026-august-28",
    ]
}


class EclipsesAdapter:
    source_name = "eclipses"
    source_type = "astronomy"
    source_adapter = "timeanddate-eclipse-v1"
    source_url = "https://www.timeanddate.com/eclipse/"

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
            urls = self._urls_for_year(year)
            if not urls:
                return self._failed_report(year, "no configured eclipse detail URLs")

            html = self._http_client.get(urls[0], timeout=30).text
            parsed = _parse_eclipse_html(html, urls[0])
            if not parsed["group_id"]:
                return self._failed_report(year, "unable to derive eclipse identity")
            if not parsed["full_duration"]:
                return self._failed_report(year, "required timing fields missing")
        except Exception as exc:  # pragma: no cover
            return self._failed_report(year, str(exc))

        return ValidationReport(
            source_name=self.source_name,
            year=year,
            status="passed",
            validated_at=self._now_provider(),
            checks=[
                "reachable",
                "canary detail page reachable",
                "canary timeline present",
                "required timing fields present",
                "detail url resolved",
            ],
            detail_url_ok=True,
            source_url=self.source_url,
        )

    def fetch(self, year: int) -> RawFetchResult:
        urls = self._urls_for_year(year)
        if not urls:
            raise ValueError(f"No configured eclipse detail URLs for {year}")

        saved_files: list[str] = []
        for index, url in enumerate(urls, start=1):
            response = self._http_client.get(url, timeout=30)
            response.raise_for_status()
            raw_path = self._raw_store.write_text(
                self.source_type,
                year,
                "timeanddate-eclipses",
                f"eclipse-{index}.html",
                response.text,
            )
            saved_files.append(_raw_ref_for_path(raw_path))

        manifest_path = self._raw_store.write_text(
            self.source_type,
            year,
            "timeanddate-eclipses",
            "manifest.json",
            json.dumps({"urls": urls, "files": saved_files}, indent=2, sort_keys=True),
        )
        return RawFetchResult(
            source_name=self.source_name,
            year=year,
            fetched_at=self._now_provider(),
            raw_ref=_raw_ref_for_path(manifest_path),
            source_url=self.source_url,
            metadata={"record_count": len(saved_files), "detail_urls": urls},
        )

    def normalize(self, year: int, raw_result: RawFetchResult) -> list[CandidateRecord]:
        manifest_path = Path(raw_result.raw_ref)
        if not manifest_path.is_absolute():
            manifest_path = PROJECT_ROOT / raw_result.raw_ref
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
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

        for file_ref, url in zip(manifest["files"], manifest["urls"], strict=True):
            html_path = Path(file_ref)
            if not html_path.is_absolute():
                html_path = PROJECT_ROOT / file_ref
            html = html_path.read_text(encoding="utf-8")
            parsed = _parse_eclipse_html(html, url)
            if parsed["full_duration"] is None:
                raise ValueError(f"Missing full-duration timing for {url}")
            candidates.append(
                _candidate_from_parsed(
                    parsed=parsed,
                    variant="full-duration",
                    start=parsed["full_duration"]["start"],
                    end=parsed["full_duration"]["end"],
                    is_default=True,
                    validation=validation,
                    seen_at=seen_at,
                    raw_ref=file_ref,
                    source_adapter=self.source_adapter,
                )
            )
            if parsed["totality"] is not None:
                candidates.append(
                    _candidate_from_parsed(
                        parsed=parsed,
                        variant="totality",
                        start=parsed["totality"]["start"],
                        end=parsed["totality"]["end"],
                        is_default=False,
                        validation=validation,
                        seen_at=seen_at,
                        raw_ref=file_ref,
                        source_adapter=self.source_adapter,
                    )
                )

        return candidates

    def _urls_for_year(self, year: int) -> list[str]:
        return list(ECLIPSE_DETAIL_URLS.get(year, []))

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


def _parse_eclipse_html(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    title_text = soup.title.get_text(" ", strip=True) if soup.title else ""
    event_title = title_text.split(" – ")[0]
    event_title = event_title.split(" on ")[0]

    h1 = soup.find("h1")
    heading = h1.get_text(" ", strip=True) if h1 else event_title

    body = "moon" if "lunar eclipse" in heading.lower() else "sun"
    degree = "total" if "total" in heading.lower() else "partial"
    if "annular" in heading.lower():
        degree = "annular"
    if "penumbral" in heading.lower():
        degree = "penumbral"
    if "hybrid" in heading.lower():
        degree = "hybrid"

    date_slug = _date_slug_from_url(url)
    group_id = f"astronomy/eclipse/{date_slug}/{degree}-{body}"

    timeline_table = soup.find("table", id="eclipse-table")
    if timeline_table is None:
        return {
            "title": heading,
            "group_id": "",
            "body": body,
            "tags": [],
            "detail_url": url,
            "full_duration": None,
            "totality": None,
        }

    stages: dict[str, str] = {}
    for row in timeline_table.select("tbody tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        stage = cells[0].get_text(" ", strip=True)
        utc_text = cells[1].get_text(" ", strip=True)
        stages[stage] = _parse_utc_stage_time(utc_text)

    full_duration = _full_duration_for_heading(heading, stages)
    totality = _totality_for_heading(heading, stages)
    tags = ["eclipse", body, degree]
    return {
        "title": _base_title(degree, body),
        "group_id": group_id,
        "body": body,
        "degree": degree,
        "tags": tags,
        "detail_url": url,
        "full_duration": full_duration,
        "totality": totality,
    }


def _date_slug_from_url(url: str) -> str:
    match = re.search(r"/eclipse/(?:solar|lunar)/(\d{4})-([a-z]+)-(\d{1,2})", url)
    if not match:
        return "unknown-date"
    year, month_name, day = match.groups()
    month = _month_number(month_name)
    return f"{year}-{month:02d}-{int(day):02d}"


def _parse_utc_stage_time(text: str) -> str:
    match = re.match(
        r"([A-Z][a-z]{2}) (\d{1,2}) at (\d{2}):(\d{2})(?::(\d{2}))?",
        text,
    )
    if not match:
        raise ValueError(f"Unexpected UTC stage time format: {text}")
    month_name, day, hour, minute, second = match.groups()
    month = _month_number(month_name)
    year = 2026
    timestamp = datetime(
        year,
        month,
        int(day),
        int(hour),
        int(minute),
        int(second or 0),
        tzinfo=timezone.utc,
    )
    return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def _full_duration_for_heading(heading: str, stages: dict[str, str]) -> dict | None:
    lower = heading.lower()
    if "lunar eclipse" in lower:
        start = stages.get("Penumbral Eclipse begins")
        end = stages.get("Penumbral Eclipse ends")
    else:
        start = stages.get("First location to see the partial eclipse begin")
        end = stages.get("Last location to see the partial eclipse end")
    if not start or not end:
        return None
    return {"start": start, "end": end}


def _totality_for_heading(heading: str, stages: dict[str, str]) -> dict | None:
    lower = heading.lower()
    if "total" not in lower:
        return None
    if "lunar eclipse" in lower:
        start = stages.get("Full Eclipse begins")
        end = stages.get("Full Eclipse ends")
    else:
        start = stages.get("First location to see the full eclipse begin")
        end = stages.get("Last location to see the full eclipse end")
    if not start or not end:
        return None
    return {"start": start, "end": end}


def _candidate_from_parsed(
    *,
    parsed: dict,
    variant: str,
    start: str,
    end: str,
    is_default: bool,
    validation: ValidationResult,
    seen_at: str,
    raw_ref: str,
    source_adapter: str,
) -> CandidateRecord:
    occurrence_id = f"{parsed['group_id']}/{variant}"
    title = _variant_title(parsed["title"], parsed["degree"], variant)
    candidate = CandidateRecord(
        group_id=parsed["group_id"],
        occurrence_id=occurrence_id,
        source_type="astronomy",
        body=parsed["body"],
        event_type="eclipse",
        variant=variant,
        is_default=is_default,
        title=title,
        summary=title,
        description=_variant_description(parsed["title"], parsed["degree"], variant),
        start=start,
        end=end,
        all_day=False,
        timezone="UTC",
        categories=["Astronomy", "Eclipse"],
        tags=parsed["tags"],
        detail_url=parsed["detail_url"],
        source_adapter=source_adapter,
        source_validation=validation,
        content_hash="",
        first_seen_at=seen_at,
        last_seen_at=seen_at,
        candidate_status="new",
        accepted_revision=None,
        timing_source=SourceReference(name="timeanddate", url=parsed["detail_url"]),
        validation_sources=[],
        metadata={},
        raw_ref=raw_ref,
    )
    candidate.content_hash = _candidate_content_hash(candidate)
    return candidate


def _candidate_content_hash(candidate: CandidateRecord) -> str:
    payload = candidate.to_dict()
    payload["content_hash"] = ""
    return sha256_text(json.dumps(payload, sort_keys=True))


def _base_title(degree: str, body: str) -> str:
    degree_title = {
        "total": "Total",
        "partial": "Partial",
        "annular": "Annular",
        "penumbral": "Penumbral",
        "hybrid": "Hybrid",
    }.get(degree, degree.title())
    body_title = "Lunar" if body == "moon" else "Solar"
    return f"{degree_title} {body_title} Eclipse"


def _variant_title(base_title: str, degree: str, variant: str) -> str:
    if variant != "totality":
        return base_title
    if degree == "annular":
        return f"{base_title}: Annularity"
    return f"{base_title}: Totality"


def _variant_description(base_title: str, degree: str, variant: str) -> str:
    if variant == "full-duration":
        return (
            f"This entry covers the full duration of the {base_title.lower()} worldwide. "
            "See the source page for local visibility and circumstances."
        )
    if degree == "annular":
        return "This entry marks the period of annularity during the eclipse."
    return "This entry marks the period of totality during the eclipse."


def _month_number(value: str) -> int:
    months = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    normalized = value.strip().lower()
    month = months.get(normalized)
    if month is None:
        raise ValueError(f"Unknown month name: {value}")
    return month


def _raw_ref_for_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path.resolve())
