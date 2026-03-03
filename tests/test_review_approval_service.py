from __future__ import annotations

import json

import pytest

from astrocal.models import GENERATED_CONTENT_HASH_KEY, ReviewBundle, ReviewBundleEntry
from astrocal.repositories import CatalogStore
from astrocal.services.review_approval_service import approve_review
from tests.test_reconcile_service import _accepted_from_candidate
from tests.test_review_report_service import build_eclipse_candidate


def test_approve_review_creates_initial_accepted_revision(tmp_path) -> None:
    candidate = build_eclipse_candidate()
    bundle = ReviewBundle(
        calendar_name="astronomy-eclipses",
        year=2026,
        generated_at="2026-03-03T00-00-00Z",
        entries=[
            ReviewBundleEntry(
                occurrence_id=candidate.occurrence_id,
                group_id=candidate.group_id,
                status="new",
                source_name="eclipses",
                candidate_content_hash=candidate.content_hash,
                generated_content_hash=candidate.content_hash,
                allowed_actions=["approve-as-is"],
                candidate=candidate.to_dict(),
                accepted=None,
            )
        ],
    )
    report_path = tmp_path / "review.astronomy-eclipses.json"
    report_path.write_text(json.dumps(bundle.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    result = approve_review(
        report_path=report_path,
        reviewer="tester",
        occurrence_ids=[candidate.occurrence_id],
        catalog_store=CatalogStore(base_dir=tmp_path / "accepted"),
        reviewed_at="2026-03-03T01:00:00Z",
    )

    saved = CatalogStore(base_dir=tmp_path / "accepted").load("astronomy", 2026, "eclipses")
    assert result.catalog_path.exists()
    assert len(saved) == 1
    assert saved[0].revision == 1
    assert saved[0].record["metadata"]["description_review"]["status"] == "accepted"
    assert (
        saved[0].record["metadata"]["description_provenance"][GENERATED_CONTENT_HASH_KEY]
        == candidate.content_hash
    )


def test_approve_review_supersedes_current_revision_when_editing_prose(tmp_path) -> None:
    candidate = build_eclipse_candidate()
    existing = _accepted_from_candidate(
        candidate,
        revision=1,
        status="active",
        accepted_at="2026-03-01T00:00:00Z",
        change_reason="Initial acceptance",
    )
    bundle = ReviewBundle(
        calendar_name="astronomy-eclipses",
        year=2026,
        generated_at="2026-03-03T00-00-00Z",
        entries=[
            ReviewBundleEntry(
                occurrence_id=candidate.occurrence_id,
                group_id=candidate.group_id,
                status="changed",
                source_name="eclipses",
                candidate_content_hash=candidate.content_hash,
                generated_content_hash=candidate.content_hash,
                allowed_actions=["approve-as-is", "approve-with-prose-edits"],
                candidate=candidate.to_dict(),
                accepted=existing.to_dict(),
            )
        ],
    )
    report_path = tmp_path / "review.astronomy-eclipses.json"
    report_path.write_text(json.dumps(bundle.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    store = CatalogStore(base_dir=tmp_path / "accepted")
    store.save("astronomy", 2026, "eclipses", [existing])

    approve_review(
        report_path=report_path,
        reviewer="tester",
        occurrence_ids=[candidate.occurrence_id],
        resolution="prose-edited",
        title="Edited Eclipse Title",
        summary="Edited Eclipse Summary",
        description="Edited eclipse description.",
        note="Tightened the prose.",
        catalog_store=store,
        reviewed_at="2026-03-03T01:00:00Z",
    )

    saved = store.load("astronomy", 2026, "eclipses")
    assert len(saved) == 2
    assert saved[0].status == "superseded"
    assert saved[1].revision == 2
    assert saved[1].record["title"] == "Edited Eclipse Title"
    assert saved[1].record["summary"] == "Edited Eclipse Summary"
    assert saved[1].record["description"] == "Edited eclipse description."
    assert saved[1].record["metadata"]["description_review"]["edited"] is True
    assert saved[1].record["metadata"]["description_review"]["resolution"] == "prose-edited"
    assert saved[1].record["content_hash"] == saved[1].content_hash
    assert saved[1].content_hash != candidate.content_hash


def test_approve_review_rejects_stale_review_entry(tmp_path) -> None:
    candidate = build_eclipse_candidate()
    existing = _accepted_from_candidate(
        candidate,
        revision=1,
        status="active",
        accepted_at="2026-03-01T00:00:00Z",
        change_reason="Initial acceptance",
    )
    stale = _accepted_from_candidate(
        candidate,
        revision=1,
        status="active",
        accepted_at="2026-03-01T00:00:00Z",
        change_reason="Initial acceptance",
    )
    stale.content_hash = "sha256:stale"
    bundle = ReviewBundle(
        calendar_name="astronomy-eclipses",
        year=2026,
        generated_at="2026-03-03T00-00-00Z",
        entries=[
            ReviewBundleEntry(
                occurrence_id=candidate.occurrence_id,
                group_id=candidate.group_id,
                status="changed",
                source_name="eclipses",
                candidate_content_hash=candidate.content_hash,
                generated_content_hash=candidate.content_hash,
                allowed_actions=["approve-as-is"],
                candidate=candidate.to_dict(),
                accepted=stale.to_dict(),
            )
        ],
    )
    report_path = tmp_path / "review.astronomy-eclipses.json"
    report_path.write_text(json.dumps(bundle.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    store = CatalogStore(base_dir=tmp_path / "accepted")
    store.save("astronomy", 2026, "eclipses", [existing])

    with pytest.raises(ValueError, match="stale"):
        approve_review(
            report_path=report_path,
            reviewer="tester",
            occurrence_ids=[candidate.occurrence_id],
            catalog_store=store,
            reviewed_at="2026-03-03T01:00:00Z",
        )


def test_approve_review_rejects_suspected_removal_entries(tmp_path) -> None:
    candidate = build_eclipse_candidate()
    accepted = _accepted_from_candidate(
        candidate,
        revision=1,
        status="suspected-removed",
        accepted_at="2026-03-01T00:00:00Z",
        change_reason="Missing from current candidate set",
    )
    bundle = ReviewBundle(
        calendar_name="astronomy-eclipses",
        year=2026,
        generated_at="2026-03-03T00-00-00Z",
        entries=[
            ReviewBundleEntry(
                occurrence_id=candidate.occurrence_id,
                group_id=candidate.group_id,
                status="suspected-removed",
                source_name="eclipses",
                candidate_content_hash=None,
                generated_content_hash=candidate.content_hash,
                allowed_actions=["review-removal"],
                candidate=None,
                accepted=accepted.to_dict(),
            )
        ],
    )
    report_path = tmp_path / "review.astronomy-eclipses.json"
    report_path.write_text(json.dumps(bundle.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="suspected removal"):
        approve_review(
            report_path=report_path,
            reviewer="tester",
            occurrence_ids=[candidate.occurrence_id],
            catalog_store=CatalogStore(base_dir=tmp_path / "accepted"),
            reviewed_at="2026-03-03T01:00:00Z",
        )
