from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from astrocal.models import ReviewBundle, ReviewBundleEntry
from astrocal.paths import PROJECT_ROOT
from astrocal.repositories import CandidateStore, CatalogStore
from tests.test_cli import sample_review_bundle
from tests.test_reconcile_service import _accepted_from_candidate
from tests.test_review_report_service import build_eclipse_candidate


def _write_message(handle, payload: dict[str, object]) -> None:
    handle.write((json.dumps(payload) + "\n").encode("utf-8"))
    handle.flush()


def _read_message(handle) -> dict[str, object]:
    line = handle.readline()
    if not line:
        raise EOFError("MCP server closed stdout")
    return json.loads(line.decode("utf-8"))


@contextmanager
def mcp_server(project_root: Path | None = None, adapters_factory: str | None = None):
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["PYTHONUNBUFFERED"] = "1"
    if project_root is not None:
        env["ASTROCAL_PROJECT_ROOT"] = str(project_root)
    if adapters_factory is not None:
        env["ASTROCAL_ADAPTERS_FACTORY"] = adapters_factory
    process = subprocess.Popen(
        [sys.executable, "-m", "astrocal.mcp"],
        cwd=PROJECT_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    try:
        _write_message(
            process.stdin,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "1.0"},
                },
            },
        )
        response = _read_message(process.stdout)
        assert response["id"] == 1
        _write_message(
            process.stdin,
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        )
        yield process
    finally:
        process.terminate()
        process.wait(timeout=5)


def _request(process: subprocess.Popen[bytes], request_id: int, method: str, params: dict) -> dict:
    assert process.stdin is not None
    assert process.stdout is not None
    _write_message(
        process.stdin,
        {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
    )
    response = _read_message(process.stdout)
    assert response["id"] == request_id
    return response


def _list_tools(process: subprocess.Popen[bytes]) -> list[dict[str, object]]:
    response = _request(process, 2, "tools/list", {})
    return response["result"]["tools"]


def _list_resources(process: subprocess.Popen[bytes]) -> list[dict[str, object]]:
    response = _request(process, 3, "resources/list", {})
    return response["result"]["resources"]


def _call_tool(process: subprocess.Popen[bytes], request_id: int, name: str, arguments: dict) -> dict:
    response = _request(
        process,
        request_id,
        "tools/call",
        {"name": name, "arguments": arguments},
    )
    return response["result"]["structuredContent"]


def _write_review_bundle(root: Path) -> Path:
    bundle = sample_review_bundle()
    return _write_bundle(root, bundle)


def _write_bundle(root: Path, bundle: ReviewBundle) -> Path:
    report_path = root / "2026-03-03T00-00-00Z" / "review.astronomy-eclipses.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(bundle.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report_path


@contextmanager
def fixture_project_root():
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        shutil.copytree(PROJECT_ROOT / "config", root / "config")
        yield root


def test_mcp_server_lists_expected_tools() -> None:
    with mcp_server() as process:
        tool_names = [tool["name"] for tool in _list_tools(process)]
        assert tool_names == [
            "astrocal_list_pending_reviews",
            "astrocal_get_review_bundle",
            "astrocal_get_review_markdown",
            "astrocal_reconcile_calendar",
            "astrocal_build_calendar",
            "astrocal_run_calendar_pipeline",
            "astrocal_approve_review",
        ]


def test_mcp_server_registers_no_resources() -> None:
    with mcp_server() as process:
        assert _list_resources(process) == []


def test_list_pending_reviews_returns_paginated_review_summaries() -> None:
    with TemporaryDirectory() as temp_dir:
        report_dir = Path(temp_dir)
        _write_review_bundle(report_dir)
        with mcp_server() as process:
            result = _call_tool(
                process,
                4,
                "astrocal_list_pending_reviews",
                {"report_dir": str(report_dir), "limit": 10, "offset": 0},
            )

    assert result["ok"] is True
    assert result["total"] == 1
    assert result["count"] == 1
    assert result["items"][0]["calendar_name"] == "astronomy-eclipses"
    assert result["items"][0]["entry_count"] == 1
    assert result["items"][0]["report_path"].endswith("review.astronomy-eclipses.json")


def test_get_review_bundle_returns_structured_bundle() -> None:
    with TemporaryDirectory() as temp_dir:
        report_path = _write_review_bundle(Path(temp_dir))
        with mcp_server() as process:
            result = _call_tool(
                process,
                5,
                "astrocal_get_review_bundle",
                {"report_path": str(report_path)},
            )

    assert result["ok"] is True
    assert result["bundle"]["calendar_name"] == "astronomy-eclipses"
    assert len(result["bundle"]["entries"]) == 1


def test_get_review_markdown_returns_rendered_text() -> None:
    with TemporaryDirectory() as temp_dir:
        report_path = _write_review_bundle(Path(temp_dir))
        with mcp_server() as process:
            result = _call_tool(
                process,
                6,
                "astrocal_get_review_markdown",
                {"report_path": str(report_path)},
            )

    assert result["ok"] is True
    assert "Review bundle: astronomy-eclipses" in result["markdown"]
    assert result["report_path"] == str(report_path)


def test_missing_review_bundle_maps_to_not_found_error() -> None:
    with mcp_server() as process:
        result = _call_tool(
            process,
            7,
            "astrocal_get_review_bundle",
            {"report_path": "missing-review.json"},
        )

    assert result["ok"] is False
    assert result["error"]["code"] == "not_found"


def test_relative_report_dir_is_resolved_against_project_root() -> None:
    with TemporaryDirectory(dir=PROJECT_ROOT) as temp_dir:
        report_dir = Path(temp_dir)
        report_path = _write_review_bundle(report_dir)
        with mcp_server() as process:
            result = _call_tool(
                process,
                8,
                "astrocal_get_review_bundle",
                {"report_path": str(report_path.relative_to(PROJECT_ROOT))},
            )

    assert result["ok"] is True
    assert result["bundle"]["calendar_name"] == "astronomy-eclipses"


def test_reconcile_calendar_returns_review_artifact_paths() -> None:
    with fixture_project_root() as root:
        candidate_store = CandidateStore(base_dir=root / "data" / "normalized")
        candidate_store.save("astronomy", 2026, "eclipses", [build_eclipse_candidate()])

        with mcp_server(project_root=root) as process:
            result = _call_tool(
                process,
                9,
                "astrocal_reconcile_calendar",
                {"calendar": "astronomy-eclipses", "year": 2026},
            )

    assert result["ok"] is True
    assert result["calendar_name"] == "astronomy-eclipses"
    assert result["review_report_path"].endswith("review.astronomy-eclipses.md")
    assert result["review_bundle_path"].endswith("review.astronomy-eclipses.json")
    assert any(path.endswith("reconcile.astronomy-eclipses.json") for path in result["written_paths"])


def test_reconcile_calendar_reports_unknown_manifest_as_not_found() -> None:
    with fixture_project_root() as root:
        with mcp_server(project_root=root) as process:
            result = _call_tool(
                process,
                10,
                "astrocal_reconcile_calendar",
                {"calendar": "astronomy-does-not-exist", "year": 2026},
            )

    assert result["ok"] is False
    assert result["error"]["code"] == "not_found"


def test_build_calendar_returns_absolute_output_and_report_paths() -> None:
    with fixture_project_root() as root:
        candidate = build_eclipse_candidate()
        accepted = _accepted_from_candidate(
            candidate,
            revision=1,
            status="active",
            accepted_at="2026-03-01T00:00:00Z",
            change_reason="Initial acceptance",
        )
        catalog_store = CatalogStore(base_dir=root / "data" / "catalog" / "accepted")
        catalog_store.save("astronomy", 2026, "eclipses", [accepted])

        with mcp_server(project_root=root) as process:
            result = _call_tool(
                process,
                11,
                "astrocal_build_calendar",
                {"calendar": "astronomy-eclipses"},
            )

    assert result["ok"] is True
    assert result["output_path"].endswith("calendars/eclipses.ics")
    assert result["build_report_path"].endswith("build.astronomy-eclipses.json")
    assert all(Path(path).is_absolute() for path in result["written_paths"])


def test_build_calendar_resolves_relative_report_dir_against_project_root() -> None:
    with fixture_project_root() as root:
        candidate = build_eclipse_candidate()
        accepted = _accepted_from_candidate(
            candidate,
            revision=1,
            status="active",
            accepted_at="2026-03-01T00:00:00Z",
            change_reason="Initial acceptance",
        )
        CatalogStore(base_dir=root / "data" / "catalog" / "accepted").save(
            "astronomy",
            2026,
            "eclipses",
            [accepted],
        )

        with mcp_server(project_root=root) as process:
            result = _call_tool(
                process,
                12,
                "astrocal_build_calendar",
                {"calendar": "astronomy-eclipses", "report_dir": "tmp-reports"},
            )

    assert result["ok"] is True
    assert Path(result["build_report_path"]).is_relative_to((root / "tmp-reports").resolve())


def test_run_calendar_pipeline_returns_full_result_without_review_stop() -> None:
    with fixture_project_root() as root:
        with mcp_server(
            project_root=root,
            adapters_factory="tests.test_run_pipeline_service:mcp_test_adapters",
        ) as process:
            result = _call_tool(
                process,
                13,
                "astrocal_run_calendar_pipeline",
                {"calendar": "astronomy-moon-phases", "year": 2026},
            )

    assert result["ok"] is True
    pipeline_result = result["result"]
    assert pipeline_result["calendar_name"] == "astronomy-moon-phases"
    assert pipeline_result["stopped_for_review"] is False
    assert pipeline_result["build_report"] is not None
    assert len(pipeline_result["validation_reports"]) == 1
    assert len(pipeline_result["raw_results"]) == 1
    assert len(pipeline_result["normalized_results"]) == 1


def test_run_calendar_pipeline_stops_before_build_when_review_is_pending() -> None:
    with fixture_project_root() as root:
        with mcp_server(
            project_root=root,
            adapters_factory="tests.test_run_pipeline_service:mcp_test_adapters",
        ) as process:
            result = _call_tool(
                process,
                14,
                "astrocal_run_calendar_pipeline",
                {"calendar": "astronomy-eclipses", "year": 2026, "report_dir": "tmp-reports"},
            )

    assert result["ok"] is True
    pipeline_result = result["result"]
    assert pipeline_result["stopped_for_review"] is True
    assert pipeline_result["build_report"] is None
    assert pipeline_result["reconciliation_report"]["review_bundle_path"] is not None
    assert all(Path(path).is_absolute() for path in pipeline_result["written_paths"])


def test_approve_review_writes_new_catalog_revision() -> None:
    with fixture_project_root() as root:
        report_path = _write_review_bundle(root / "data" / "catalog" / "reports")
        with mcp_server(project_root=root) as process:
            result = _call_tool(
                process,
                15,
                "astrocal_approve_review",
                {
                    "report_path": str(report_path),
                    "reviewer": "tester",
                    "occurrence_ids": [
                        "astronomy/eclipse/2026-08-12/total-sun/full-duration"
                    ],
                },
            )

        saved = CatalogStore(base_dir=root / "data" / "catalog" / "accepted").load(
            "astronomy",
            2026,
            "eclipses",
        )

    assert result["ok"] is True
    assert result["approved_count"] == 1
    assert result["catalog_path"].endswith("data/catalog/accepted/astronomy/2026/eclipses.json")
    assert saved[0].record["metadata"]["description_review"]["status"] == "accepted"


def test_approve_review_maps_stale_entry_to_conflict() -> None:
    with fixture_project_root() as root:
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
        CatalogStore(base_dir=root / "data" / "catalog" / "accepted").save(
            "astronomy",
            2026,
            "eclipses",
            [existing],
        )
        report_path = _write_bundle(root / "data" / "catalog" / "reports", bundle)

        with mcp_server(project_root=root) as process:
            result = _call_tool(
                process,
                16,
                "astrocal_approve_review",
                {
                    "report_path": str(report_path),
                    "reviewer": "tester",
                    "occurrence_ids": [candidate.occurrence_id],
                },
            )

    assert result["ok"] is False
    assert result["error"]["code"] == "conflict"


def test_approve_review_maps_invalid_request_combinations() -> None:
    with fixture_project_root() as root:
        report_path = _write_review_bundle(root / "data" / "catalog" / "reports")
        with mcp_server(project_root=root) as process:
            no_selector = _call_tool(
                process,
                17,
                "astrocal_approve_review",
                {"report_path": str(report_path), "reviewer": "tester"},
            )
            invalid_override = _call_tool(
                process,
                18,
                "astrocal_approve_review",
                {
                    "report_path": str(report_path),
                    "reviewer": "tester",
                    "group_ids": ["astronomy/eclipse/2026-08-12/total-sun"],
                    "title": "Edited",
                },
            )

    assert no_selector["ok"] is False
    assert no_selector["error"]["code"] == "invalid_request"
    assert invalid_override["ok"] is False
    assert invalid_override["error"]["code"] == "invalid_request"


def test_approve_review_maps_missing_bundle_to_not_found() -> None:
    with fixture_project_root() as root:
        with mcp_server(project_root=root) as process:
            result = _call_tool(
                process,
                19,
                "astrocal_approve_review",
                {
                    "report_path": "missing-review.json",
                    "reviewer": "tester",
                    "occurrence_ids": ["astronomy/eclipse/2026-08-12/total-sun/full-duration"],
                },
            )

    assert result["ok"] is False
    assert result["error"]["code"] == "not_found"


def test_reconcile_inspect_approve_build_workflow_succeeds_over_mcp() -> None:
    with fixture_project_root() as root:
        CandidateStore(base_dir=root / "data" / "normalized").save(
            "astronomy",
            2026,
            "eclipses",
            [build_eclipse_candidate()],
        )

        with mcp_server(project_root=root) as process:
            reconcile_result = _call_tool(
                process,
                20,
                "astrocal_reconcile_calendar",
                {"calendar": "astronomy-eclipses", "year": 2026},
            )
            bundle_result = _call_tool(
                process,
                21,
                "astrocal_get_review_bundle",
                {"report_path": reconcile_result["review_bundle_path"]},
            )
            approve_result = _call_tool(
                process,
                22,
                "astrocal_approve_review",
                {
                    "report_path": reconcile_result["review_bundle_path"],
                    "reviewer": "tester",
                    "occurrence_ids": [
                        bundle_result["bundle"]["entries"][0]["occurrence_id"]
                    ],
                },
            )
            build_result = _call_tool(
                process,
                23,
                "astrocal_build_calendar",
                {"calendar": "astronomy-eclipses"},
            )

            assert reconcile_result["ok"] is True
            assert bundle_result["ok"] is True
            assert approve_result["ok"] is True
            assert build_result["ok"] is True
            assert Path(build_result["output_path"]).exists()


def test_run_inspect_approve_build_workflow_succeeds_over_mcp() -> None:
    with fixture_project_root() as root:
        with mcp_server(
            project_root=root,
            adapters_factory="tests.test_run_pipeline_service:mcp_test_adapters",
        ) as process:
            run_result = _call_tool(
                process,
                24,
                "astrocal_run_calendar_pipeline",
                {"calendar": "astronomy-eclipses", "year": 2026},
            )
            bundle_path = run_result["result"]["reconciliation_report"]["review_bundle_path"]
            markdown_result = _call_tool(
                process,
                25,
                "astrocal_get_review_markdown",
                {"report_path": bundle_path},
            )
            approve_result = _call_tool(
                process,
                26,
                "astrocal_approve_review",
                {
                    "report_path": bundle_path,
                    "reviewer": "tester",
                    "occurrence_ids": [
                        "astronomy/eclipse/2026-08-12/total-sun/full-duration"
                    ],
                },
            )
            build_result = _call_tool(
                process,
                27,
                "astrocal_build_calendar",
                {"calendar": "astronomy-eclipses"},
            )

            assert run_result["ok"] is True
            assert run_result["result"]["stopped_for_review"] is True
            assert markdown_result["ok"] is True
            assert "Review bundle: astronomy-eclipses" in markdown_result["markdown"]
            assert approve_result["ok"] is True
            assert build_result["ok"] is True
            assert Path(build_result["output_path"]).exists()
