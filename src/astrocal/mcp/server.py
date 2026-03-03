"""FastMCP server exposing the astrocal review workflow."""

from __future__ import annotations

import traceback
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..errors import CliUserError
from ..manifests import load_manifest
from ..paths import PROJECT_ROOT
from ..repositories import CatalogStore, ReportStore
from ..services.build_ics_service import build_calendar
from ..services.reconcile_service import reconcile_calendar
from ..services.review_approval_service import approve_review
from ..services.review_query_service import list_pending_reviews, load_review_bundle, render_review_bundle
from ..services.run_pipeline_service import run_calendar_pipeline
from .schemas import (
    ApproveReviewResult,
    BuildCalendarResult,
    GetReviewBundleResult,
    GetReviewMarkdownResult,
    ListPendingReviewsResult,
    PendingReviewItem,
    ReconcileCalendarResult,
    RunCalendarPipelineResult,
    ToolError,
)

mcp = FastMCP("astrocal_mcp", json_response=True)


@mcp.tool(
    name="astrocal_list_pending_reviews",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    structured_output=True,
)
def astrocal_list_pending_reviews(
    report_dir: str | None = None,
    calendar_name: str | None = None,
    year: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> ListPendingReviewsResult:
    """List persisted review bundles that still need action."""
    try:
        pending = list_pending_reviews(_resolve_optional_path(report_dir))
        if calendar_name is not None:
            pending = [review for review in pending if review.bundle.calendar_name == calendar_name]
        if year is not None:
            pending = [review for review in pending if review.bundle.year == year]

        total = len(pending)
        page = pending[offset : offset + limit]
        return ListPendingReviewsResult(
            ok=True,
            total=total,
            count=len(page),
            offset=offset,
            has_more=offset + len(page) < total,
            next_offset=offset + len(page) if offset + len(page) < total else None,
            items=[
                PendingReviewItem(
                    report_path=str(review.report_path.resolve()),
                    calendar_name=review.bundle.calendar_name,
                    year=review.bundle.year,
                    generated_at=review.bundle.generated_at,
                    entry_count=len(review.bundle.entries),
                )
                for review in page
            ],
        )
    except Exception as exc:
        return _error_result(ListPendingReviewsResult, exc)


@mcp.tool(
    name="astrocal_get_review_bundle",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    structured_output=True,
)
def astrocal_get_review_bundle(report_path: str) -> GetReviewBundleResult:
    """Load a persisted review bundle as structured JSON."""
    try:
        bundle = load_review_bundle(_resolve_path(report_path))
        return GetReviewBundleResult(ok=True, bundle=bundle.to_dict())
    except Exception as exc:
        return _error_result(GetReviewBundleResult, exc)


@mcp.tool(
    name="astrocal_get_review_markdown",
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    structured_output=True,
)
def astrocal_get_review_markdown(report_path: str) -> GetReviewMarkdownResult:
    """Render a persisted review bundle as markdown text."""
    try:
        resolved = _resolve_path(report_path)
        bundle = load_review_bundle(resolved)
        return GetReviewMarkdownResult(
            ok=True,
            report_path=str(resolved),
            markdown=render_review_bundle(bundle, output_format="markdown"),
        )
    except Exception as exc:
        return _error_result(GetReviewMarkdownResult, exc)


@mcp.tool(
    name="astrocal_reconcile_calendar",
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
    structured_output=True,
)
def astrocal_reconcile_calendar(
    calendar: str,
    year: int,
    report_dir: str | None = None,
) -> ReconcileCalendarResult:
    """Run reconciliation for a calendar and return any review artifacts."""
    try:
        manifest = load_manifest(calendar)
        resolved_report_dir = _resolve_optional_path(report_dir)
        report_store = ReportStore(base_dir=resolved_report_dir) if resolved_report_dir else None
        report, written_paths = reconcile_calendar(
            manifest=manifest,
            year=year,
            report_store=report_store,
        )
        return ReconcileCalendarResult(
            ok=True,
            calendar_name=report.calendar_name,
            year=report.year,
            generated_at=report.generated_at,
            report_dir=str(resolved_report_dir or (PROJECT_ROOT / "data" / "catalog" / "reports")),
            validation_failures=report.validation_failures,
            new_occurrence_ids=report.new_occurrences,
            changed_occurrence_ids=report.changed_occurrences,
            suspected_removal_ids=report.suspected_removals,
            review_report_path=report.review_report_path,
            review_bundle_path=report.review_bundle_path,
            written_paths=[str(Path(path).resolve()) for path in written_paths],
        )
    except Exception as exc:
        return _error_result(ReconcileCalendarResult, exc)


@mcp.tool(
    name="astrocal_build_calendar",
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
    structured_output=True,
)
def astrocal_build_calendar(
    calendar: str,
    variant_policy: str | None = None,
    report_dir: str | None = None,
) -> BuildCalendarResult:
    """Build a published ICS calendar from accepted records."""
    try:
        manifest = load_manifest(calendar)
        resolved_report_dir = _resolve_optional_path(report_dir)
        report_store = ReportStore(base_dir=resolved_report_dir) if resolved_report_dir else None
        effective_variant_policy = variant_policy or manifest.variant_policy
        report, written_paths = build_calendar(
            manifest=manifest,
            report_store=report_store,
            variant_policy=effective_variant_policy,
        )
        build_report_path = next(
            (
                str(Path(path).resolve())
                for path in written_paths
                if Path(path).name == f"build.{manifest.name}.json"
            ),
            None,
        )
        return BuildCalendarResult(
            ok=True,
            calendar_name=report.calendar_name,
            generated_at=report.generated_at,
            variant_policy=effective_variant_policy,
            output_path=_resolve_output_path(report.output_path),
            event_count=report.event_count,
            sequence_path=_resolve_output_path(report.sequence_path),
            build_report_path=build_report_path,
            written_paths=[str(Path(path).resolve()) for path in written_paths],
        )
    except Exception as exc:
        return _error_result(BuildCalendarResult, exc)


@mcp.tool(
    name="astrocal_run_calendar_pipeline",
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
    structured_output=True,
)
def astrocal_run_calendar_pipeline(
    calendar: str,
    year: int,
    variant_policy: str | None = None,
    report_dir: str | None = None,
) -> RunCalendarPipelineResult:
    """Run validate, fetch, normalize, reconcile, and build for a calendar."""
    try:
        manifest = load_manifest(calendar)
        resolved_report_dir = _resolve_optional_path(report_dir)
        report_store = ReportStore(base_dir=resolved_report_dir) if resolved_report_dir else None
        result = run_calendar_pipeline(
            manifest=manifest,
            year=year,
            report_store=report_store,
            variant_policy=variant_policy or manifest.variant_policy,
        )
        return RunCalendarPipelineResult(ok=True, result=result.to_dict())
    except Exception as exc:
        return _error_result(RunCalendarPipelineResult, exc)


@mcp.tool(
    name="astrocal_approve_review",
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    ),
    structured_output=True,
)
def astrocal_approve_review(
    report_path: str,
    reviewer: str,
    occurrence_ids: list[str] | None = None,
    group_ids: list[str] | None = None,
    resolution: str = "accepted",
    note: str | None = None,
    title: str | None = None,
    summary: str | None = None,
    description: str | None = None,
    catalog_dir: str | None = None,
) -> ApproveReviewResult:
    """Approve a persisted review bundle entry into the accepted catalog."""
    try:
        resolved_catalog_dir = _resolve_optional_path(catalog_dir)
        result = approve_review(
            report_path=_resolve_path(report_path),
            reviewer=reviewer,
            occurrence_ids=occurrence_ids or [],
            group_ids=group_ids or [],
            resolution=resolution,
            note=note,
            title=title,
            summary=summary,
            description=description,
            catalog_store=CatalogStore(base_dir=resolved_catalog_dir) if resolved_catalog_dir else None,
        )
        return ApproveReviewResult(
            ok=True,
            catalog_path=str(result.catalog_path.resolve()),
            approved_count=len(result.approved_records),
            approved_occurrence_ids=[record.occurrence_id for record in result.approved_records],
        )
    except Exception as exc:
        return _error_result(ApproveReviewResult, exc)


def _resolve_optional_path(value: str | None) -> Path | None:
    if value is None:
        return None
    return _resolve_path(value)


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _resolve_output_path(value: str | None) -> str | None:
    if value is None:
        return None
    return str(_resolve_path(value).resolve())


def _error_result(model_cls: type[Any], exc: Exception) -> Any:
    if isinstance(exc, CliUserError):
        return model_cls(ok=False, error=_tool_error(exc))

    traceback.print_exc()
    return model_cls(
        ok=False,
        error=ToolError(code="internal_error", message=f"Internal error: {type(exc).__name__}"),
    )


def _tool_error(exc: CliUserError) -> ToolError:
    message = str(exc)
    lowered = message.lower()
    if "not found" in lowered or "unknown calendar manifest" in lowered:
        code = "not_found"
    elif "not valid json" in lowered or "malformed" in lowered or "not readable" in lowered:
        code = "invalid_data"
    elif "stale" in lowered:
        code = "conflict"
    else:
        code = "invalid_request"
    return ToolError(code=code, message=message)
