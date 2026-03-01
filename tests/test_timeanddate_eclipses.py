from __future__ import annotations

from pathlib import Path

from astronomical_calendars.adapters.astronomy.timeanddate_eclipses import EclipsesAdapter
from astronomical_calendars.repositories import CandidateStore, RawStore
from astronomical_calendars.services.normalize_service import normalize_source_family


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "timeanddate"


class FixtureResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class FixtureHttpClient:
    def __init__(self, pages: dict[str, str]) -> None:
        self._pages = pages

    def get(self, url: str, timeout: int = 30) -> FixtureResponse:
        return FixtureResponse(self._pages[url])


def build_adapter(tmp_path: Path) -> EclipsesAdapter:
    pages = {
        "https://www.timeanddate.com/eclipse/lunar/2026-march-3": (
            FIXTURE_DIR / "eclipse-detail-lunar-2026-03-03.html"
        ).read_text(encoding="utf-8"),
        "https://www.timeanddate.com/eclipse/solar/2026-august-12": (
            FIXTURE_DIR / "eclipse-detail-solar-2026-08-12.html"
        ).read_text(encoding="utf-8"),
        "https://www.timeanddate.com/eclipse/lunar/2026-august-28": (
            FIXTURE_DIR / "eclipse-detail-lunar-2026-08-28.html"
        ).read_text(encoding="utf-8"),
    }
    return EclipsesAdapter(
        http_client=FixtureHttpClient(pages),
        raw_store=RawStore(base_dir=tmp_path / "raw"),
        now_provider=lambda: "2026-03-01T12:00:00Z",
    )


def test_validate_timeanddate_eclipses_fixture_passes(tmp_path: Path) -> None:
    adapter = build_adapter(tmp_path)

    report = adapter.validate(2026)

    assert report.status == "passed"
    assert report.detail_url_ok is True


def test_fetch_and_normalize_timeanddate_eclipses_fixture(tmp_path: Path) -> None:
    adapter = build_adapter(tmp_path)

    raw_result = adapter.fetch(2026)
    normalized = normalize_source_family(
        "astronomy",
        2026,
        adapters={"eclipses": adapter},
        raw_results=[raw_result],
        candidate_store=CandidateStore(base_dir=tmp_path / "normalized"),
    )

    assert raw_result.raw_ref.endswith("manifest.json")
    assert len(normalized) == 1
    source_name, candidates = normalized[0]
    assert source_name == "eclipses"
    assert len(candidates) == 5
    assert {candidate.variant for candidate in candidates} == {"full-duration", "totality"}
    assert all(candidate.event_type == "eclipse" for candidate in candidates)


def test_partial_eclipse_omits_totality_variant(tmp_path: Path) -> None:
    adapter = build_adapter(tmp_path)

    candidates = adapter.normalize(2026, adapter.fetch(2026))

    partial_group_candidates = [
        candidate
        for candidate in candidates
        if "2026-08-28" in candidate.group_id
    ]

    assert len(partial_group_candidates) == 1
    assert partial_group_candidates[0].variant == "full-duration"
