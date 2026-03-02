from __future__ import annotations

from astrocal.models import CandidateRecord, SourceReference, ValidationResult
from astrocal.services.description_generation_service import (
    GeneratedDescription,
    apply_generated_descriptions,
)


class FakeGenerator:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate(self, *, facts: dict[str, object], variant: str, occurrence_id: str) -> GeneratedDescription:
        self.calls.append(
            {
                "facts": facts,
                "variant": variant,
                "occurrence_id": occurrence_id,
            }
        )
        return GeneratedDescription(
            title="Generated Eclipse Title",
            summary="Generated Eclipse Summary",
            description="Generated eclipse description from structured facts.",
            generator_id="fake-generator",
            prompt_version="test-prompt-v1",
        )


def build_eclipse_candidate() -> CandidateRecord:
    candidate = build_candidate()
    candidate.group_id = "astronomy/eclipse/2026-08-12/total-sun"
    candidate.occurrence_id = "astronomy/eclipse/2026-08-12/total-sun/full-duration"
    candidate.body = "sun"
    candidate.event_type = "eclipse"
    candidate.variant = "full-duration"
    candidate.title = "Total Solar Eclipse"
    candidate.summary = "Total Solar Eclipse"
    candidate.description = "Placeholder eclipse description."
    candidate.metadata = {
        "description_generation": {
            "facts": {
                "schema_version": "eclipse-facts-v1",
                "group_id": candidate.group_id,
                "identity": {
                    "body": "sun",
                    "degree": "total",
                    "canonical_title": "Total Solar Eclipse",
                },
                "timing": {
                    "full_duration": {
                        "start": "2026-08-12T15:34:15Z",
                        "end": "2026-08-12T19:57:57Z",
                    },
                    "special_phase": {
                        "kind": "totality",
                        "start": "2026-08-12T16:58:09Z",
                        "end": "2026-08-12T18:34:07Z",
                    },
                },
                "visibility": {
                    "partial_regions": ["Europe", "North America"],
                    "path_countries": ["Greenland", "Iceland", "Spain"],
                    "visibility_note": "Local visibility varies by location.",
                },
                "generation_inputs": {
                    "facts_hash": "sha256:facts",
                    "prompt_version": "eclipse-description-v1",
                },
            }
        }
    }
    return candidate


def test_apply_generated_descriptions_uses_structured_facts_and_sets_provenance() -> None:
    generator = FakeGenerator()
    eclipse = build_eclipse_candidate()

    updated = apply_generated_descriptions(
        [eclipse],
        generator=generator,
        generated_at="2026-03-01T12:00:00Z",
    )

    assert len(generator.calls) == 1
    assert generator.calls[0]["facts"] == eclipse.metadata["description_generation"]["facts"]
    assert generator.calls[0]["variant"] == "full-duration"
    assert generator.calls[0]["occurrence_id"] == eclipse.occurrence_id

    updated_candidate = updated[0]
    assert updated_candidate.title == "Generated Eclipse Title"
    assert updated_candidate.summary == "Generated Eclipse Summary"
    assert updated_candidate.description == "Generated eclipse description from structured facts."
    assert updated_candidate.metadata["description_provenance"] == {
        "facts_hash": "sha256:facts",
        "facts_schema_version": "eclipse-facts-v1",
        "generator": "fake-generator",
        "generated_at": "2026-03-01T12:00:00Z",
        "prompt_version": "test-prompt-v1",
    }


def test_apply_generated_descriptions_leaves_non_eclipse_candidates_unchanged() -> None:
    moon_phase = build_candidate()

    updated = apply_generated_descriptions(
        [moon_phase],
        generator=FakeGenerator(),
        generated_at="2026-03-01T12:00:00Z",
    )

    assert updated[0].title == "New Moon"
    assert updated[0].description == "A new moon occurs."
    assert "description_provenance" not in updated[0].metadata


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
