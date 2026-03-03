"""Typed models for the astronomical calendars pipeline."""

from .candidate import (
    DESCRIPTION_GENERATION_KEY,
    ECLIPSE_FACTS_SCHEMA_VERSION,
    CandidateRecord,
    SourceReference,
    ValidationResult,
)
from .catalog import (
    AcceptedRecord,
    DESCRIPTION_PROVENANCE_KEY,
    DESCRIPTION_REVIEW_KEY,
    GENERATED_CONTENT_HASH_KEY,
)
from .manifest import CalendarManifest
from .reports import BuildReport, RawFetchResult, ReconciliationReport, ValidationReport
from .review import ReviewBundle, ReviewBundleEntry

__all__ = [
    "AcceptedRecord",
    "BuildReport",
    "CalendarManifest",
    "CandidateRecord",
    "DESCRIPTION_GENERATION_KEY",
    "DESCRIPTION_PROVENANCE_KEY",
    "DESCRIPTION_REVIEW_KEY",
    "ECLIPSE_FACTS_SCHEMA_VERSION",
    "GENERATED_CONTENT_HASH_KEY",
    "RawFetchResult",
    "ReconciliationReport",
    "ReviewBundle",
    "ReviewBundleEntry",
    "SourceReference",
    "ValidationReport",
    "ValidationResult",
]
