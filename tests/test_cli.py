from __future__ import annotations

import json

from astrocal.cli import main
from astrocal.models import (
    AcceptedRecord,
    BuildReport,
    RawFetchResult,
    ReconciliationReport,
    ReviewBundle,
    ReviewBundleEntry,
    ValidationReport,
)
from astrocal.repositories import CatalogStore


def build_adapter(source_name: str) -> CliAdapter:
    return type(f"{source_name.title()}CliAdapter", (CliAdapter,), {"source_name": source_name})()


class CliAdapter:
    source_name = "moon-phases"
    source_type = "astronomy"

    def validate(self, year: int) -> ValidationReport:
        return ValidationReport(
            source_name=self.source_name,
            year=year,
            status="passed",
            validated_at="2026-03-01T00:00:00Z",
            checks=["reachable"],
            canary_ok=True,
            source_url="https://example.com/moon-phases",
        )

    def fetch(self, year: int) -> RawFetchResult:
        return RawFetchResult(
            source_name=self.source_name,
            year=year,
            fetched_at="2026-03-01T00:00:00Z",
            raw_ref="data/raw/astronomy/2026/usno-moon-phases/response.json",
            source_url="https://example.com/moon-phases",
        )

    def normalize(self, year: int, raw_result: RawFetchResult) -> list[object]:
        return []


class FailingCliAdapter(CliAdapter):
    source_name = "moon-phases"

    def validate(self, year: int) -> ValidationReport:
        return ValidationReport(
            source_name=self.source_name,
            year=year,
            status="failed",
            validated_at="2026-03-01T00:00:00Z",
            checks=["reachable"],
            reason="upstream timeout",
            canary_ok=False,
            source_url="https://example.com/moon-phases",
        )


def test_run_command_executes_pipeline(capsys, mocker) -> None:
    mocker.patch(
        "astrocal.services.run_service.ASTRONOMY_ADAPTERS",
        {
            "moon-phases": build_adapter("moon-phases"),
            "seasons": build_adapter("seasons"),
            "eclipses": build_adapter("eclipses"),
        },
    )
    mocker.patch(
        "astrocal.services.run_service.reconcile_calendar",
        return_value=(
            ReconciliationReport(
                calendar_name="astronomy-all",
                year=2026,
                generated_at="2026-03-01T00:00:00Z",
            ),
            [],
        ),
    )
    mocker.patch(
        "astrocal.services.run_service.build_calendar",
        return_value=(
            BuildReport(
                calendar_name="astronomy-all",
                generated_at="2026-03-01T00:00:00Z",
                output_path="calendars/astronomical-events.ics",
                event_count=3,
                sequence_path="data/state/sequences/astronomy-all.json",
            ),
            [],
        ),
    )

    exit_code = main(["run", "--calendar", "astronomy-all", "--year", "2026"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "validate astronomy year=2026" in captured.out
    assert "validate moon-phases start year=2026" in captured.out
    assert "fetch astronomy year=2026" in captured.out
    assert "normalize astronomy year=2026" in captured.out
    assert "reconcile astronomy-all year=2026" in captured.out
    assert "build astronomy-all variant_policy=default" in captured.out
    assert "stage=" not in captured.out


def test_build_command_uses_manifest_default_variant_policy(capsys, mocker) -> None:
    build_mock = mocker.patch(
        "astrocal.services.stub_service.build_calendar",
        return_value=(
            BuildReport(
                calendar_name="astronomy-eclipses",
                generated_at="2026-03-01T00:00:00Z",
                output_path="calendars/eclipses.ics",
                event_count=2,
                sequence_path="data/state/sequences/astronomy-eclipses.json",
            ),
            [],
        ),
    )

    exit_code = main(["build", "--calendar", "astronomy-eclipses"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "build astronomy-eclipses variant_policy=default" in captured.out
    assert "stage=" not in captured.out
    assert "data/catalog/reports" in str(build_mock.call_args.kwargs["report_store"]._base_dir)


def test_validate_command_writes_reports_only_when_report_dir_is_requested(
    capsys,
    mocker,
    tmp_path,
) -> None:
    mocker.patch(
        "astrocal.services.stub_service.ASTRONOMY_ADAPTERS",
        {"moon-phases": CliAdapter()},
    )

    exit_code = main(
        [
            "validate",
            "--year",
            "2026",
            "--report-dir",
            str(tmp_path),
            "astronomy",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "validate moon-phases status=passed year=2026" in captured.out
    assert list(tmp_path.glob("*/validate.moon-phases.2026.json"))


def test_run_command_uses_repo_report_store_by_default(capsys, mocker) -> None:
    mocker.patch(
        "astrocal.services.run_service.ASTRONOMY_ADAPTERS",
        {
            "moon-phases": build_adapter("moon-phases"),
            "seasons": build_adapter("seasons"),
            "eclipses": build_adapter("eclipses"),
        },
    )
    reconcile_mock = mocker.patch(
        "astrocal.services.run_service.reconcile_calendar",
        return_value=(
            ReconciliationReport(
                calendar_name="astronomy-all",
                year=2026,
                generated_at="2026-03-01T00:00:00Z",
            ),
            [],
        ),
    )
    mocker.patch(
        "astrocal.services.run_service.build_calendar",
        return_value=(
            BuildReport(
                calendar_name="astronomy-all",
                generated_at="2026-03-01T00:00:00Z",
                output_path="calendars/astronomical-events.ics",
                event_count=3,
                sequence_path="data/state/sequences/astronomy-all.json",
            ),
            [],
        ),
    )

    exit_code = main(["run", "--calendar", "astronomy-all", "--year", "2026"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "reconcile astronomy-all year=2026" in captured.out
    assert "data/catalog/reports" in str(reconcile_mock.call_args.kwargs["report_store"]._base_dir)


def test_reconcile_command_returns_non_zero_on_validation_failure(capsys, mocker) -> None:
    mocker.patch(
        "astrocal.services.stub_service.reconcile_calendar",
        return_value=(
            ReconciliationReport(
                calendar_name="astronomy-all",
                year=2026,
                generated_at="2026-03-01T00:00:00Z",
                validation_failures=["eclipses"],
            ),
            [],
        ),
    )

    exit_code = main(["reconcile", "--calendar", "astronomy-all", "--year", "2026"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "reconcile astronomy-all year=2026" in captured.out


def test_reconcile_command_prints_review_report_path(capsys, mocker) -> None:
    mocker.patch(
        "astrocal.services.stub_service.reconcile_calendar",
        return_value=(
            ReconciliationReport(
                calendar_name="astronomy-eclipses",
                year=2026,
                generated_at="2026-03-01T00:00:00Z",
                review_report_path="data/catalog/reports/2026-03-01T00-00-00Z/review.astronomy-eclipses.md",
                review_bundle_path="data/catalog/reports/2026-03-01T00-00-00Z/review.astronomy-eclipses.json",
            ),
            [],
        ),
    )

    exit_code = main(["reconcile", "--calendar", "astronomy-eclipses", "--year", "2026"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "review_report=data/catalog/reports/2026-03-01T00-00-00Z/review.astronomy-eclipses.md" in captured.out
    assert "review_bundle=data/catalog/reports/2026-03-01T00-00-00Z/review.astronomy-eclipses.json" in captured.out


def test_run_command_stops_before_build_when_review_is_pending(capsys, mocker) -> None:
    mocker.patch(
        "astrocal.services.run_service.ASTRONOMY_ADAPTERS",
        {"eclipses": build_adapter("eclipses")},
    )
    mocker.patch(
        "astrocal.services.run_service.reconcile_calendar",
        return_value=(
            ReconciliationReport(
                calendar_name="astronomy-eclipses",
                year=2026,
                generated_at="2026-03-01T00:00:00Z",
                review_report_path="data/catalog/reports/2026-03-01T00-00-00Z/review.astronomy-eclipses.md",
                review_bundle_path="data/catalog/reports/2026-03-01T00-00-00Z/review.astronomy-eclipses.json",
            ),
            [],
        ),
    )
    build_mock = mocker.patch("astrocal.services.run_service.build_calendar")

    exit_code = main(["run", "--calendar", "astronomy-eclipses", "--year", "2026"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "reconcile astronomy-eclipses year=2026" in captured.out
    assert "review_report=data/catalog/reports/2026-03-01T00-00-00Z/review.astronomy-eclipses.md" in captured.out
    assert "review_bundle=data/catalog/reports/2026-03-01T00-00-00Z/review.astronomy-eclipses.json" in captured.out
    assert "build astronomy-eclipses" not in captured.out
    build_mock.assert_not_called()


def test_run_command_for_eclipse_manifest_ignores_unrelated_source_validation(capsys, mocker) -> None:
    mocker.patch(
        "astrocal.services.run_service.ASTRONOMY_ADAPTERS",
        {
            "moon-phases": FailingCliAdapter(),
            "eclipses": build_adapter("eclipses"),
        },
    )
    mocker.patch(
        "astrocal.services.run_service.reconcile_calendar",
        return_value=(
            ReconciliationReport(
                calendar_name="astronomy-eclipses",
                year=2026,
                generated_at="2026-03-01T00:00:00Z",
                review_report_path="data/catalog/reports/2026-03-01T00-00-00Z/review.astronomy-eclipses.md",
                review_bundle_path="data/catalog/reports/2026-03-01T00-00-00Z/review.astronomy-eclipses.json",
            ),
            [],
        ),
    )
    build_mock = mocker.patch("astrocal.services.run_service.build_calendar")

    exit_code = main(["run", "--calendar", "astronomy-eclipses", "--year", "2026"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "validate eclipses start year=2026" in captured.out
    assert "validate moon-phases start year=2026" not in captured.out
    assert "validate moon-phases status=failed" not in captured.out
    build_mock.assert_not_called()


def test_list_pending_reviews_command_prints_persisted_review_bundles(capsys, tmp_path) -> None:
    bundle = ReviewBundle(
        calendar_name="astronomy-eclipses",
        year=2026,
        generated_at="2026-03-03T00-00-00Z",
        entries=[
            ReviewBundleEntry(
                occurrence_id="astronomy/eclipse/2026-08-12/total-sun/full-duration",
                group_id="astronomy/eclipse/2026-08-12/total-sun",
                status="new",
                source_name="eclipses",
                candidate_content_hash="sha256:candidate",
                generated_content_hash="sha256:candidate",
                allowed_actions=["approve-as-is"],
                candidate={"title": "Total Solar Eclipse"},
                accepted=None,
            )
        ],
    )
    report_path = tmp_path / "2026-03-03T00-00-00Z" / "review.astronomy-eclipses.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(bundle.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    exit_code = main(["list-pending-reviews", "--report-dir", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert f"report={report_path}" in captured.out
    assert "calendar=astronomy-eclipses year=2026 entries=1" in captured.out


def test_list_pending_reviews_command_omits_already_approved_bundle(capsys, tmp_path) -> None:
    candidate = {
        "accepted_revision": None,
        "all_day": False,
        "body": "sun",
        "candidate_status": "new",
        "categories": ["Astronomy", "Eclipse"],
        "content_hash": "sha256:candidate",
        "description": "Generated eclipse description.",
        "detail_url": "https://www.timeanddate.com/eclipse/solar/2026-august-12",
        "end": "2026-08-12T19:57:57Z",
        "event_type": "eclipse",
        "first_seen_at": "2026-03-03T00:00:00Z",
        "group_id": "astronomy/eclipse/2026-08-12/total-sun",
        "is_default": True,
        "last_seen_at": "2026-03-03T00:00:00Z",
        "metadata": {
            "description_provenance": {
                "facts_hash": "sha256:facts",
                "facts_schema_version": "eclipse-facts-v1",
                "generator": "test-generator",
                "generated_at": "2026-03-03T00:00:00Z",
                "prompt_version": "eclipse-description-v1",
                "generated_content_hash": "sha256:candidate",
            },
            "description_review": {
                "status": "accepted",
                "reviewed_at": "2026-03-03T01:00:00Z",
                "reviewer": "tester",
                "edited": False,
                "resolution": "accepted",
                "note": None,
            },
        },
        "occurrence_id": "astronomy/eclipse/2026-08-12/total-sun/full-duration",
        "raw_ref": "data/raw/astronomy/2026/timeanddate-eclipses/eclipse-2.html",
        "source_adapter": "timeanddate-eclipse-v1",
        "source_type": "astronomy",
        "source_validation": {
            "checks": ["reachable"],
            "detail_url_ok": True,
            "reason": None,
            "status": "passed",
            "validated_at": "2026-03-03T00:00:00Z",
        },
        "start": "2026-08-12T15:34:15Z",
        "summary": "Total Solar Eclipse",
        "tags": ["eclipse", "sun", "total"],
        "timezone": "UTC",
        "timing_source": {
            "name": "timeanddate",
            "url": "https://www.timeanddate.com/eclipse/solar/2026-august-12",
        },
        "title": "Total Solar Eclipse",
        "validation_sources": [],
        "variant": "full-duration",
    }
    bundle = ReviewBundle(
        calendar_name="astronomy-eclipses",
        year=2026,
        generated_at="2026-03-03T00-00-00Z",
        entries=[
            ReviewBundleEntry(
                occurrence_id="astronomy/eclipse/2026-08-12/total-sun/full-duration",
                group_id="astronomy/eclipse/2026-08-12/total-sun",
                status="new",
                source_name="eclipses",
                candidate_content_hash="sha256:candidate",
                generated_content_hash="sha256:candidate",
                allowed_actions=["approve-as-is"],
                candidate=candidate,
                accepted=None,
            )
        ],
    )
    report_path = tmp_path / "2026-03-03T00-00-00Z" / "review.astronomy-eclipses.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(bundle.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    accepted_dir = tmp_path / "accepted"
    accepted_store = CatalogStore(base_dir=accepted_dir)
    accepted_store.save(
        "astronomy",
        2026,
        "eclipses",
        [
            AcceptedRecord(
                occurrence_id="astronomy/eclipse/2026-08-12/total-sun/full-duration",
                revision=1,
                status="active",
                accepted_at="2026-03-03T01:00:00Z",
                superseded_at=None,
                change_reason="Accepted after review",
                content_hash="sha256:approved",
                source_adapter="timeanddate-eclipse-v1",
                detail_url="https://www.timeanddate.com/eclipse/solar/2026-august-12",
                record=candidate | {"accepted_revision": 1, "candidate_status": "accepted", "content_hash": "sha256:approved"},
            )
        ],
    )

    exit_code = main(
        [
            "list-pending-reviews",
            "--report-dir",
            str(tmp_path),
            "--catalog-dir",
            str(accepted_dir),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ""


def test_show_review_command_supports_json_output(capsys, tmp_path) -> None:
    bundle = ReviewBundle(
        calendar_name="astronomy-eclipses",
        year=2026,
        generated_at="2026-03-03T00-00-00Z",
        entries=[
            ReviewBundleEntry(
                occurrence_id="astronomy/eclipse/2026-08-12/total-sun/full-duration",
                group_id="astronomy/eclipse/2026-08-12/total-sun",
                status="new",
                source_name="eclipses",
                candidate_content_hash="sha256:candidate",
                generated_content_hash="sha256:candidate",
                allowed_actions=["approve-as-is", "approve-with-prose-edits"],
                candidate={"title": "Total Solar Eclipse"},
                accepted=None,
            )
        ],
    )
    report_path = tmp_path / "review.astronomy-eclipses.json"
    report_path.write_text(json.dumps(bundle.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    exit_code = main(["show-review", "--report", str(report_path), "--format", "json"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"calendar_name": "astronomy-eclipses"' in captured.out
    assert '"occurrence_id": "astronomy/eclipse/2026-08-12/total-sun/full-duration"' in captured.out


def test_show_review_command_supports_markdown_output(capsys, tmp_path) -> None:
    bundle = ReviewBundle(
        calendar_name="astronomy-eclipses",
        year=2026,
        generated_at="2026-03-03T00-00-00Z",
        entries=[
            ReviewBundleEntry(
                occurrence_id="astronomy/eclipse/2026-08-12/total-sun/full-duration",
                group_id="astronomy/eclipse/2026-08-12/total-sun",
                status="changed",
                source_name="eclipses",
                candidate_content_hash="sha256:candidate",
                generated_content_hash="sha256:candidate",
                allowed_actions=["approve-as-is", "approve-with-prose-edits"],
                candidate={"title": "Total Solar Eclipse"},
                accepted={"record": {"title": "Previous Eclipse Title"}},
            )
        ],
    )
    report_path = tmp_path / "review.astronomy-eclipses.json"
    report_path.write_text(json.dumps(bundle.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    exit_code = main(["show-review", "--report", str(report_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Review bundle: astronomy-eclipses" in captured.out
    assert "status=changed" in captured.out
    assert "group_id=astronomy/eclipse/2026-08-12/total-sun" in captured.out
    assert "title=Total Solar Eclipse" in captured.out


def test_approve_review_command_writes_accepted_revision(capsys, tmp_path) -> None:
    bundle = ReviewBundle(
        calendar_name="astronomy-eclipses",
        year=2026,
        generated_at="2026-03-03T00-00-00Z",
        entries=[
            ReviewBundleEntry(
                occurrence_id="astronomy/eclipse/2026-08-12/total-sun/full-duration",
                group_id="astronomy/eclipse/2026-08-12/total-sun",
                status="new",
                source_name="eclipses",
                candidate_content_hash="sha256:candidate",
                generated_content_hash="sha256:candidate",
                allowed_actions=["approve-as-is", "approve-with-prose-edits"],
                candidate={
                    "accepted_revision": None,
                    "all_day": False,
                    "body": "sun",
                    "candidate_status": "new",
                    "categories": ["Astronomy", "Eclipse"],
                    "content_hash": "sha256:candidate",
                    "description": "Generated eclipse description.",
                    "detail_url": "https://www.timeanddate.com/eclipse/solar/2026-august-12",
                    "end": "2026-08-12T19:57:57Z",
                    "event_type": "eclipse",
                    "first_seen_at": "2026-03-03T00:00:00Z",
                    "group_id": "astronomy/eclipse/2026-08-12/total-sun",
                    "is_default": True,
                    "last_seen_at": "2026-03-03T00:00:00Z",
                    "metadata": {
                        "description_provenance": {
                            "facts_hash": "sha256:facts",
                            "facts_schema_version": "eclipse-facts-v1",
                            "generator": "test-generator",
                            "generated_at": "2026-03-03T00:00:00Z",
                            "prompt_version": "eclipse-description-v1",
                        }
                    },
                    "occurrence_id": "astronomy/eclipse/2026-08-12/total-sun/full-duration",
                    "raw_ref": "data/raw/astronomy/2026/timeanddate-eclipses/eclipse-2.html",
                    "source_adapter": "timeanddate-eclipse-v1",
                    "source_type": "astronomy",
                    "source_validation": {
                        "checks": ["reachable"],
                        "detail_url_ok": True,
                        "reason": None,
                        "status": "passed",
                        "validated_at": "2026-03-03T00:00:00Z",
                    },
                    "start": "2026-08-12T15:34:15Z",
                    "summary": "Total Solar Eclipse",
                    "tags": ["eclipse", "sun", "total"],
                    "timezone": "UTC",
                    "timing_source": {
                        "name": "timeanddate",
                        "url": "https://www.timeanddate.com/eclipse/solar/2026-august-12",
                    },
                    "title": "Total Solar Eclipse",
                    "validation_sources": [],
                    "variant": "full-duration",
                },
                accepted=None,
            )
        ],
    )
    report_path = tmp_path / "review.astronomy-eclipses.json"
    report_path.write_text(json.dumps(bundle.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    exit_code = main(
        [
            "approve-review",
            "--report",
            str(report_path),
            "--reviewer",
            "tester",
            "--occurrence-id",
            "astronomy/eclipse/2026-08-12/total-sun/full-duration",
            "--catalog-dir",
            str(tmp_path / "accepted"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "approved count=1" in captured.out
    saved_path = tmp_path / "accepted" / "astronomy" / "2026" / "eclipses.json"
    assert saved_path.exists()


def test_approve_review_command_reports_expected_errors_without_traceback(capsys, tmp_path) -> None:
    bundle = ReviewBundle(
        calendar_name="astronomy-eclipses",
        year=2026,
        generated_at="2026-03-03T00-00-00Z",
        entries=[
            ReviewBundleEntry(
                occurrence_id="astronomy/eclipse/2026-03-03/total-moon/full-duration",
                group_id="astronomy/eclipse/2026-03-03/total-moon",
                status="suspected-removed",
                source_name="eclipses",
                candidate_content_hash=None,
                generated_content_hash="sha256:accepted",
                allowed_actions=["review-removal"],
                candidate=None,
                accepted={"revision": 1, "content_hash": "sha256:accepted"},
            )
        ],
    )
    report_path = tmp_path / "review.astronomy-eclipses.json"
    report_path.write_text(json.dumps(bundle.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    exit_code = main(
        [
            "approve-review",
            "--report",
            str(report_path),
            "--reviewer",
            "tester",
            "--occurrence-id",
            "astronomy/eclipse/2026-03-03/total-moon/full-duration",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "suspected removal" in captured.err
    assert "Traceback" not in captured.err
