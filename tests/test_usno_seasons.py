from __future__ import annotations

import json
from pathlib import Path

from astrocal.adapters.astronomy.usno_seasons import SeasonsAdapter
from astrocal.repositories import CandidateStore, DiagnosticStore, RawStore
from astrocal.services.normalize_service import normalize_source_family


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "usno" / "seasons_2026.json"


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


def build_adapter(tmp_path: Path) -> SeasonsAdapter:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return SeasonsAdapter(
        http_client=FixtureHttpClient(payload),
        raw_store=RawStore(base_dir=tmp_path / "raw"),
        now_provider=lambda: "2026-03-01T12:00:00Z",
    )


def test_validate_usno_seasons_fixture_passes(tmp_path: Path) -> None:
    adapter = build_adapter(tmp_path)

    report = adapter.validate(2026)

    assert report.status == "passed"
    assert report.canary_ok is True
    assert report.detail_url_ok is True
    assert "required timing fields present" in report.checks


def test_fetch_and_normalize_usno_seasons_fixture(tmp_path: Path) -> None:
    adapter = build_adapter(tmp_path)

    raw_result = adapter.fetch(2026)
    normalized = normalize_source_family(
        "astronomy",
        2026,
        adapters={"seasons": adapter},
        raw_results=[raw_result],
        candidate_store=CandidateStore(base_dir=tmp_path / "normalized"),
    )

    assert raw_result.raw_ref.endswith("response.json")
    assert len(normalized) == 1
    source_name, candidates = normalized[0]
    assert source_name == "seasons"
    assert len(candidates) == 2
    assert candidates[0].event_type == "season-marker"
    assert candidates[0].end is None
    assert candidates[0].detail_url.startswith("https://in-the-sky.org/")
    assert candidates[0].occurrence_id.endswith("/default")
    assert all(candidate.metadata["phenom"] in {"Equinox", "Solstice"} for candidate in candidates)


def test_season_content_hash_is_deterministic_for_same_fixture(tmp_path: Path) -> None:
    adapter = build_adapter(tmp_path)

    first = adapter.normalize(2026, adapter.fetch(2026))
    second = adapter.normalize(2026, adapter.fetch(2026))

    assert [candidate.content_hash for candidate in first] == [
        candidate.content_hash for candidate in second
    ]


def test_validate_usno_seasons_accepts_generic_usno_labels(tmp_path: Path) -> None:
    payload = {
        "year": 2026,
        "data": [
            {
                "year": 2026,
                "month": 3,
                "day": 20,
                "time": "09:46",
                "phenom": "Equinox",
            }
        ],
    }
    adapter = SeasonsAdapter(
        http_client=FixtureHttpClient(payload),
        raw_store=RawStore(base_dir=tmp_path / "raw"),
        now_provider=lambda: "2026-03-01T12:00:00Z",
    )

    report = adapter.validate(2026)

    assert report.status == "passed"
    assert report.canary_ok is True


def test_normalize_usno_seasons_ignores_non_season_rows(tmp_path: Path) -> None:
    adapter = build_adapter(tmp_path)

    candidates = adapter.normalize(2026, adapter.fetch(2026))

    assert len(candidates) == 2
    assert {candidate.title for candidate in candidates} == {
        "March Equinox",
        "June Solstice",
    }


def test_normalize_diagnostics_include_season_extraction_summary(tmp_path: Path) -> None:
    adapter = build_adapter(tmp_path)

    raw_result = adapter.fetch(2026)
    normalize_source_family(
        "astronomy",
        2026,
        adapters={"seasons": adapter},
        raw_results=[raw_result],
        candidate_store=CandidateStore(base_dir=tmp_path / "normalized"),
        diagnostic_store=DiagnosticStore(base_dir=tmp_path / "diagnostics"),
    )

    summary_path = (
        tmp_path / "diagnostics" / "astronomy" / "2026" / "seasons" / "normalize-summary.json"
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["extraction_summary"] == {
        "titles_seen": ["June Solstice", "March Equinox"],
        "ignored_non_season_row_count": 2,
    }


def test_validate_usno_seasons_fails_canary_when_no_season_rows_exist(tmp_path: Path) -> None:
    payload = {
        "year": 2026,
        "data": [
            {
                "year": 2026,
                "month": 1,
                "day": 3,
                "time": "17:15",
                "phenom": "Perihelion",
            }
        ],
    }
    adapter = SeasonsAdapter(
        http_client=FixtureHttpClient(payload),
        raw_store=RawStore(base_dir=tmp_path / "raw"),
        now_provider=lambda: "2026-03-01T12:00:00Z",
    )

    report = adapter.validate(2026)

    assert report.status == "failed"
    assert report.canary_ok is False
    assert report.reason == "season-marker data missing"
