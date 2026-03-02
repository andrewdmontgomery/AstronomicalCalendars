"""Typed models for the astronomical calendars pipeline."""

from .candidate import (
    DESCRIPTION_GENERATION_KEY,
    ECLIPSE_FACTS_SCHEMA_VERSION,
    CandidateRecord,
    SourceReference,
    ValidationResult,
)
from .catalog import AcceptedRecord, DESCRIPTION_PROVENANCE_KEY, DESCRIPTION_REVIEW_KEY
from .manifest import CalendarManifest
from .reports import BuildReport, RawFetchResult, ReconciliationReport, ValidationReport

__all__ = [
    "AcceptedRecord",
    "BuildReport",
    "CalendarManifest",
    "CandidateRecord",
    "DESCRIPTION_GENERATION_KEY",
    "DESCRIPTION_PROVENANCE_KEY",
    "DESCRIPTION_REVIEW_KEY",
    "ECLIPSE_FACTS_SCHEMA_VERSION",
    "RawFetchResult",
    "ReconciliationReport",
    "SourceReference",
    "ValidationReport",
    "ValidationResult",
]
