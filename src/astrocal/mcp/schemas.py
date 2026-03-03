"""Pydantic schemas for the local astrocal MCP server."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolError(BaseModel):
    code: Literal["not_found", "invalid_request", "invalid_data", "conflict", "internal_error"]
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    ok: bool
    error: ToolError | None = None


class PendingReviewItem(BaseModel):
    report_path: str
    calendar_name: str
    year: int
    generated_at: str
    entry_count: int


class ListPendingReviewsResult(ToolResult):
    total: int = 0
    count: int = 0
    offset: int = 0
    has_more: bool = False
    next_offset: int | None = None
    items: list[PendingReviewItem] = Field(default_factory=list)


class GetReviewBundleResult(ToolResult):
    bundle: dict[str, Any] | None = None


class GetReviewMarkdownResult(ToolResult):
    report_path: str | None = None
    markdown: str | None = None


class ReconcileCalendarResult(ToolResult):
    calendar_name: str | None = None
    year: int | None = None
    generated_at: str | None = None
    report_dir: str | None = None
    validation_failures: list[str] = Field(default_factory=list)
    new_occurrence_ids: list[str] = Field(default_factory=list)
    changed_occurrence_ids: list[str] = Field(default_factory=list)
    suspected_removal_ids: list[str] = Field(default_factory=list)
    review_report_path: str | None = None
    review_bundle_path: str | None = None
    written_paths: list[str] = Field(default_factory=list)


class BuildCalendarResult(ToolResult):
    calendar_name: str | None = None
    generated_at: str | None = None
    variant_policy: str | None = None
    output_path: str | None = None
    event_count: int = 0
    sequence_path: str | None = None
    build_report_path: str | None = None
    written_paths: list[str] = Field(default_factory=list)


class RunCalendarPipelineResult(ToolResult):
    result: dict[str, Any] | None = None


class ApproveReviewResult(ToolResult):
    catalog_path: str | None = None
    approved_count: int = 0
    approved_occurrence_ids: list[str] = Field(default_factory=list)
