from __future__ import annotations

from astrocal.models import (
    AcceptedRecord,
    CandidateRecord,
    ReconciliationReport,
    SourceReference,
    ValidationResult,
)
from astrocal.repositories import CandidateStore, CatalogStore, DiagnosticStore, SequenceStore


def build_candidate() -> CandidateRecord:
    return CandidateRecord(
        group_id="astronomy/moon-phase/2026-01-01/new-moon",
        occurrence_id="astronomy/moon-phase/2026-01-01/new-moon/default",
        source_type="astronomy",
        body="moon",
        event_type="moon-phase",
        variant="default",
        is_default=True,
        title="New Moon",
        summary="New Moon",
        description="A new moon occurs.",
        start="2026-01-01T00:00:00Z",
        end=None,
        all_day=False,
        timezone="UTC",
        categories=["Astronomy"],
        tags=["moon-phase"],
        detail_url="https://example.com/new-moon",
        source_adapter="usno-moon-phases-v1",
        source_validation=ValidationResult(
            status="passed",
            validated_at="2026-03-01T00:00:00Z",
            reason=None,
            checks=["reachable"],
            canary_ok=True,
            detail_url_ok=True,
        ),
        content_hash="sha256:abc123",
        first_seen_at="2026-03-01T00:00:00Z",
        last_seen_at="2026-03-01T00:00:00Z",
        candidate_status="new",
        accepted_revision=None,
        timing_source=SourceReference(
            name="usno",
            url="https://example.com/usno/new-moon",
        ),
        validation_sources=[],
        metadata={},
        raw_ref="data/raw/astronomy/2026/usno-moon-phases/response.json",
    )


def test_candidate_store_round_trip(tmp_path) -> None:
    store = CandidateStore(base_dir=tmp_path)
    candidate = build_candidate()
    candidate.metadata = {
        "description_generation": {
            "facts": {
                "schema_version": "eclipse-facts-v1",
                "group_id": candidate.group_id,
            },
            "facts_hash": "sha256:facts",
        }
    }

    saved_path = store.save("astronomy", 2026, "moon-phases", [candidate])
    loaded = store.load("astronomy", 2026, "moon-phases")

    assert saved_path.exists()
    assert len(loaded) == 1
    assert loaded[0].occurrence_id == candidate.occurrence_id
    assert loaded[0].source_validation is not None
    assert loaded[0].source_validation.status == "passed"
    assert loaded[0].source_validation.canary_ok is True
    assert loaded[0].metadata["description_generation"]["facts"]["schema_version"] == (
        "eclipse-facts-v1"
    )


def test_catalog_store_round_trip(tmp_path) -> None:
    store = CatalogStore(base_dir=tmp_path)
    candidate = build_candidate()
    candidate.metadata = {
        "description_provenance": {
            "facts_hash": "sha256:facts",
            "facts_schema_version": "eclipse-facts-v1",
            "generator": "test-generator",
            "generated_at": "2026-03-01T00:00:00Z",
            "prompt_version": "eclipse-description-v1",
        },
        "description_review": {
            "status": "accepted",
            "reviewed_at": "2026-03-01T01:00:00Z",
            "reviewer": "tester",
            "edited": True,
            "resolution": "prose-edited",
            "note": "Tightened wording.",
        },
    }
    record = AcceptedRecord(
        occurrence_id="astronomy/moon-phase/2026-01-01/new-moon/default",
        revision=1,
        status="active",
        accepted_at="2026-03-01T00:10:00Z",
        superseded_at=None,
        change_reason="Initial acceptance",
        content_hash="sha256:abc123",
        source_adapter="usno-moon-phases-v1",
        detail_url="https://example.com/new-moon",
        record=candidate.to_dict(),
    )

    saved_path = store.save("astronomy", 2026, "moon-phases", [record])
    loaded = store.load("astronomy", 2026, "moon-phases")

    assert saved_path.exists()
    assert len(loaded) == 1
    assert loaded[0].revision == 1
    assert loaded[0].record["title"] == "New Moon"
    assert loaded[0].record["metadata"]["description_provenance"]["prompt_version"] == (
        "eclipse-description-v1"
    )
    assert loaded[0].record["metadata"]["description_review"]["resolution"] == "prose-edited"


def test_reconciliation_report_supports_review_artifacts() -> None:
    report = ReconciliationReport(
        calendar_name="astronomy-eclipses",
        year=2026,
        generated_at="2026-03-01T00-00-00Z",
        review_report_path="data/catalog/reports/2026-03-01T00-00-00Z/review.astronomy-eclipses.md",
    )

    payload = report.to_dict()

    assert payload["review_report_path"].endswith("review.astronomy-eclipses.md")


def test_sequence_store_round_trip(tmp_path) -> None:
    store = SequenceStore(base_dir=tmp_path)

    saved_path = store.save("astronomy-all", {"event-1": 2, "event-2": 1})
    loaded = store.load("astronomy-all")

    assert saved_path.exists()
    assert loaded == {"event-1": 2, "event-2": 1}


def test_diagnostic_store_round_trip(tmp_path) -> None:
    store = DiagnosticStore(base_dir=tmp_path)

    saved_path = store.write_json(
        "astronomy",
        2026,
        "moon-phases",
        "normalize-summary.json",
        {"candidate_count": 2, "source_name": "moon-phases"},
    )

    assert saved_path.exists()
    assert saved_path.read_text(encoding="utf-8").startswith("{")
