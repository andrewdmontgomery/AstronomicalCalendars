from __future__ import annotations

from astrocal.models import AcceptedRecord, CalendarManifest
from astrocal.services.review_report_service import render_review_report


def build_eclipse_manifest() -> CalendarManifest:
    return CalendarManifest(
        name="astronomy-eclipses",
        output="calendars/eclipses.ics",
        calendar_name="Eclipses",
        calendar_description="Solar and lunar eclipses with exact astronomical timing",
        variant_policy="default",
        source_types=["astronomy"],
        event_types=["eclipse"],
        bodies=[],
        tags=[],
    )


def build_eclipse_candidate():
    candidate = build_candidate()
    candidate.group_id = "astronomy/eclipse/2026-08-12/total-sun"
    candidate.occurrence_id = "astronomy/eclipse/2026-08-12/total-sun/full-duration"
    candidate.body = "sun"
    candidate.event_type = "eclipse"
    candidate.variant = "full-duration"
    candidate.title = "Total Solar Eclipse"
    candidate.summary = "Total Solar Eclipse"
    candidate.description = "Generated eclipse description."
    candidate.start = "2026-08-12T15:34:15Z"
    candidate.end = "2026-08-12T19:57:57Z"
    candidate.detail_url = "https://www.timeanddate.com/eclipse/solar/2026-august-12"
    candidate.raw_ref = "data/raw/astronomy/2026/timeanddate-eclipses/eclipse-2.html"
    candidate.metadata = {
        "description_generation": {
            "facts": {
                "identity": {
                    "body": "sun",
                    "degree": "total",
                    "canonical_title": "Total Solar Eclipse",
                },
                "timing": {
                    "full_duration": {
                        "start": candidate.start,
                        "end": candidate.end,
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
            }
        }
    }
    return candidate


def test_render_review_report_includes_changed_description_comparison() -> None:
    candidate = build_eclipse_candidate()
    accepted = _accepted_from_candidate(
        candidate,
        revision=1,
        status="active",
        accepted_at="2026-03-01T12:00:00Z",
        change_reason="Initial acceptance",
    )
    accepted.record["description"] = "Previous accepted description."

    markdown = render_review_report(
        manifest=build_eclipse_manifest(),
        year=2026,
        new_candidates=[],
        changed_pairs=[(accepted, candidate)],
        suspected_removals=[],
    )

    assert "# astronomy-eclipses Eclipse Review" in markdown
    assert "Total Solar Eclipse" in markdown
    assert "Previous accepted description." in markdown
    assert "Generated eclipse description." in markdown
    assert "Greenland, Iceland, Spain" in markdown


def _accepted_from_candidate(candidate, *, revision, status, accepted_at, change_reason):
    return AcceptedRecord(
        occurrence_id=candidate.occurrence_id,
        revision=revision,
        status=status,
        accepted_at=accepted_at,
        superseded_at=None,
        change_reason=change_reason,
        content_hash=candidate.content_hash,
        source_adapter=candidate.source_adapter,
        detail_url=candidate.detail_url,
        record=candidate.to_dict(),
    )


def build_candidate():
    from astrocal.models import CandidateRecord, SourceReference, ValidationResult

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
