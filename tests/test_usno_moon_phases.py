from __future__ import annotations

import json
from pathlib import Path

from astrocal.adapters.astronomy.usno_moon_phases import MoonPhasesAdapter
from astrocal.repositories import CandidateStore, RawStore
from astrocal.services.normalize_service import normalize_source_family


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "usno" / "moon_phases_2026.json"


class FixtureResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class FixtureHttpClient:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def get(self, url: str, params: dict | None = None, timeout: int = 30) -> FixtureResponse:
        return FixtureResponse(self._payload)


def build_adapter(tmp_path: Path) -> MoonPhasesAdapter:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return MoonPhasesAdapter(
        http_client=FixtureHttpClient(payload),
        raw_store=RawStore(base_dir=tmp_path / "raw"),
        now_provider=lambda: "2026-03-01T12:00:00Z",
    )


def test_validate_usno_moon_phases_fixture_passes(tmp_path: Path) -> None:
    adapter = build_adapter(tmp_path)

    report = adapter.validate(2026)

    assert report.status == "passed"
    assert report.detail_url_ok is True
    assert "required timing fields present" in report.checks


def test_fetch_and_normalize_usno_moon_phases_fixture(tmp_path: Path) -> None:
    adapter = build_adapter(tmp_path)

    raw_result = adapter.fetch(2026)
    normalized = normalize_source_family(
        "astronomy",
        2026,
        adapters={"moon-phases": adapter},
        raw_results=[raw_result],
        candidate_store=CandidateStore(base_dir=tmp_path / "normalized"),
    )

    assert raw_result.raw_ref.endswith("response.json")
    assert len(normalized) == 1
    source_name, candidates = normalized[0]
    assert source_name == "moon-phases"
    assert len(candidates) == 2
    assert candidates[0].event_type == "moon-phase"
    assert candidates[0].end is None
    assert candidates[0].detail_url.startswith("https://in-the-sky.org/")
    assert candidates[0].occurrence_id.endswith("/default")


def test_content_hash_is_deterministic_for_same_fixture(tmp_path: Path) -> None:
    adapter = build_adapter(tmp_path)

    first = adapter.normalize(2026, adapter.fetch(2026))
    second = adapter.normalize(2026, adapter.fetch(2026))

    assert [candidate.content_hash for candidate in first] == [
        candidate.content_hash for candidate in second
    ]


def test_validate_usno_moon_phases_fails_canary_when_required_field_is_missing(tmp_path: Path) -> None:
    payload = {
        "phasedata": [
            {
                "phase": "New Moon",
                "year": 2026,
                "month": 1,
                "day": 1,
            }
        ]
    }
    adapter = MoonPhasesAdapter(
        http_client=FixtureHttpClient(payload),
        raw_store=RawStore(base_dir=tmp_path / "raw"),
        now_provider=lambda: "2026-03-01T12:00:00Z",
    )

    report = adapter.validate(2026)

    assert report.status == "failed"
    assert report.reason == "missing required fields: time"
