# Eclipse Description Fact Bundle

Eclipse descriptions are generated from a structured fact bundle derived from normalized
source data. The generator must not read raw HTML directly. Raw snapshots remain part of
the provenance trail, but the generation boundary is the fact bundle attached to each
normalized eclipse candidate.

## Scope

This first iteration applies only to eclipse candidates produced by
`src/astrocal/adapters/astronomy/timeanddate_eclipses.py`.

Moon phases and seasons keep their current deterministic text until the eclipse workflow is
proven.

## Bundle Shape

Store the fact bundle under `CandidateRecord.metadata["description_generation"]["facts"]`.

```json
{
  "schema_version": "eclipse-facts-v1",
  "source_type": "astronomy",
  "event_type": "eclipse",
  "occurrence_scope": "group",
  "group_id": "astronomy/eclipse/2026-08-12/total-sun",
  "detail_url": "https://www.timeanddate.com/eclipse/solar/2026-august-12",
  "raw_ref": "data/raw/astronomy/2026/timeanddate-eclipses/eclipse-2.html",
  "identity": {
    "body": "sun",
    "degree": "total",
    "canonical_title": "Total Solar Eclipse"
  },
  "timing": {
    "full_duration": {
      "start": "2026-08-12T15:34:15Z",
      "end": "2026-08-12T19:57:57Z"
    },
    "special_phase": {
      "kind": "totality",
      "start": "2026-08-12T16:58:09Z",
      "end": "2026-08-12T18:34:07Z"
    }
  },
  "visibility": {
    "partial_regions": [
      "Europe",
      "North in Asia",
      "North/West Africa",
      "Much of North America",
      "Pacific",
      "Atlantic",
      "Arctic"
    ],
    "path_countries": [
      "Greenland",
      "Iceland",
      "Spain"
    ],
    "visibility_note": "Local visibility varies by location."
  },
  "generation_inputs": {
    "facts_hash": "sha256:...",
    "prompt_version": "eclipse-description-v1"
  }
}
```

## Required Fields

- `schema_version`
  - Starts at `eclipse-facts-v1`.
- `source_type`
  - `astronomy` for the current workflow.
- `event_type`
  - `eclipse`.
- `occurrence_scope`
  - Use `group` in the first iteration so one fact bundle can support multiple variants.
- `group_id`
  - Stable group identity for the eclipse.
- `detail_url`
  - Canonical human-facing source page.
- `raw_ref`
  - Path to the persisted raw snapshot used for extraction.
- `identity.body`
  - `sun` or `moon`.
- `identity.degree`
  - `partial`, `total`, `annular`, `penumbral`, or `hybrid`.
- `identity.canonical_title`
  - Human-readable eclipse title derived from structured facts.
- `timing.full_duration`
  - Required for every eclipse.
- `generation_inputs.facts_hash`
  - Stable hash used to track whether generated prose still matches the facts.

## Optional Fields

- `timing.special_phase`
  - Present only for totality or annularity windows.
- `visibility.partial_regions`
  - Regions with some visibility.
- `visibility.path_countries`
  - Countries on the path of totality or annularity when the source provides them.
- `visibility.visibility_note`
  - Short extracted note when present in the source.

## Review And Acceptance

- Description generation happens after normalization into occurrence variants.
- Generated title, summary, and description remain candidate-stage content until human
  review updates the accepted catalog.
- Accepted records store generation provenance and review state under
  `record.metadata.description_provenance` and `record.metadata.description_review`.
- If a reviewer edits accepted eclipse copy after generation, create a new accepted
  revision instead of mutating the active revision in place.
