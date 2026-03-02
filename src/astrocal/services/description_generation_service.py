"""Generate review-stage descriptions from structured eclipse facts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from ..hashing import sha256_text
from ..models import (
    DESCRIPTION_GENERATION_KEY,
    DESCRIPTION_PROVENANCE_KEY,
    CandidateRecord,
)


@dataclass(slots=True)
class GeneratedDescription:
    title: str
    summary: str
    description: str
    generator_id: str
    prompt_version: str


class DescriptionGenerator(Protocol):
    def generate(
        self,
        *,
        facts: dict[str, object],
        variant: str,
        occurrence_id: str,
    ) -> GeneratedDescription: ...


class StructuredFactsDescriptionGenerator:
    generator_id = "structured-facts-generator-v1"
    prompt_version = "eclipse-description-v1"

    def generate(
        self,
        *,
        facts: dict[str, object],
        variant: str,
        occurrence_id: str,
    ) -> GeneratedDescription:
        identity = _as_dict(facts.get("identity"))
        timing = _as_dict(facts.get("timing"))
        visibility = _as_dict(facts.get("visibility"))

        body = str(identity.get("body", ""))
        degree = str(identity.get("degree", ""))
        base_title = str(identity.get("canonical_title", occurrence_id))
        event_label = f"{degree} {'solar' if body == 'sun' else 'lunar'} eclipse".strip()
        full_duration = _as_dict(timing.get("full_duration"))
        special_phase = _as_dict(timing.get("special_phase"))
        partial_regions = _string_list(visibility.get("partial_regions"))
        path_countries = _string_list(visibility.get("path_countries"))

        if variant == "totality":
            phase_kind = str(special_phase.get("kind", "totality"))
            phase_title = "Annularity" if phase_kind == "annularity" else "Totality"
            description = (
                f"This {phase_kind} phase of the {event_label} runs from "
                f"{special_phase.get('start')} to {special_phase.get('end')} UTC."
            )
            if path_countries:
                description += (
                    f" Countries on the path of {phase_kind} include "
                    f"{_format_list(path_countries)}."
                )
            if partial_regions:
                description += f" Partial visibility extends across {_format_list(partial_regions)}."
            return GeneratedDescription(
                title=f"{base_title}: {phase_title}",
                summary=f"{base_title}: {phase_title}",
                description=description,
                generator_id=self.generator_id,
                prompt_version=self.prompt_version,
            )

        description = (
            f"This {event_label} runs from {full_duration.get('start')} to "
            f"{full_duration.get('end')} UTC."
        )
        if special_phase:
            phase_kind = str(special_phase.get("kind", "totality"))
            description += (
                f" {phase_kind.capitalize()} lasts from {special_phase.get('start')} to "
                f"{special_phase.get('end')} UTC."
            )
        if partial_regions:
            description += f" At least part of the eclipse is visible across {_format_list(partial_regions)}."
        if path_countries:
            description += (
                f" The path of {'annularity' if degree == 'annular' else 'totality'} crosses "
                f"{_format_list(path_countries)}."
            )

        return GeneratedDescription(
            title=base_title,
            summary=base_title,
            description=description,
            generator_id=self.generator_id,
            prompt_version=self.prompt_version,
        )


def apply_generated_descriptions(
    candidates: list[CandidateRecord],
    *,
    generator: DescriptionGenerator | None = None,
    generated_at: str,
) -> list[CandidateRecord]:
    generator = generator or StructuredFactsDescriptionGenerator()

    for candidate in candidates:
        facts = candidate.metadata.get(DESCRIPTION_GENERATION_KEY, {}).get("facts")
        if candidate.event_type != "eclipse" or not isinstance(facts, dict):
            continue

        generated = generator.generate(
            facts=facts,
            variant=candidate.variant,
            occurrence_id=candidate.occurrence_id,
        )
        candidate.title = generated.title
        candidate.summary = generated.summary
        candidate.description = generated.description
        candidate.metadata[DESCRIPTION_PROVENANCE_KEY] = {
            "facts_hash": _facts_hash(facts),
            "facts_schema_version": facts.get("schema_version"),
            "generator": generated.generator_id,
            "generated_at": generated_at,
            "prompt_version": generated.prompt_version,
        }
        candidate.content_hash = _candidate_content_hash(candidate)

    return candidates


def _candidate_content_hash(candidate: CandidateRecord) -> str:
    payload = candidate.to_dict()
    payload["content_hash"] = ""
    metadata = payload.get("metadata", {})
    if isinstance(metadata, dict):
        provenance = metadata.get(DESCRIPTION_PROVENANCE_KEY)
        if isinstance(provenance, dict):
            provenance["generated_at"] = ""
    return sha256_text(json.dumps(payload, sort_keys=True))


def _facts_hash(facts: dict[str, object]) -> str:
    generation_inputs = _as_dict(facts.get("generation_inputs"))
    existing = generation_inputs.get("facts_hash")
    if isinstance(existing, str) and existing:
        return existing
    return sha256_text(json.dumps(facts, sort_keys=True))


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _format_list(values: list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"
