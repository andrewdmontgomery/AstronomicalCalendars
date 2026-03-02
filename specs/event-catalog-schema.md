# Event Catalog Schema

The accepted catalog is the source of truth for published calendar content. Source modules
emit candidates. Reconciliation decides whether those candidates become accepted active
records.

For eclipse descriptions, agent-generated candidate prose is review-stage material only.
Published `.ics` output must continue to come from accepted catalog records after human
review.

## Accepted Record

```json
{
  "occurrence_id": "astronomy/eclipse/2026-08-12/total-solar/full-duration",
  "revision": 2,
  "status": "active",
  "accepted_at": "2026-03-01T12:10:00Z",
  "superseded_at": null,
  "change_reason": "Corrected eclipse end time from updated source data",
  "content_hash": "sha256:...",
  "source_adapter": "timeanddate-eclipse-v1",
  "detail_url": "https://example.com/event",
  "record": {}
}
```

## Required Fields

- `occurrence_id`
  - Stable identifier matching the candidate occurrence.

- `revision`
  - Monotonic integer that increments each time the accepted content changes.

- `status`
  - One of `active`, `superseded`, `suspected-removed`.

- `accepted_at`
  - Timestamp when this revision became accepted.

- `superseded_at`
  - Timestamp when this revision stopped being active, or `null`.

- `change_reason`
  - Human-readable explanation for the revision or status change.

- `content_hash`
  - Hash of the accepted record content, used during reconciliation.

- `source_adapter`
  - Adapter identifier that produced the candidate which became accepted.

- `detail_url`
  - Detail page used by the accepted record.

- `record`
  - The accepted normalized event record.
  - For reviewed eclipse records, store description generation provenance and review state
    under `record.metadata`.

## Eclipse Description Metadata

Reviewed eclipse records may include:

- `record.metadata.description_provenance`
  - `facts_hash`
  - `facts_schema_version`
  - `generator`
  - `generated_at`
  - `prompt_version`
- `record.metadata.description_review`
  - `status`
  - `reviewed_at`
  - `reviewer`
  - `edited`
  - `resolution`
  - `note`

If accepted eclipse copy changes after review, write a new accepted revision rather than
editing the active revision in place.

## Reconciliation Report

Each reconciliation run should emit a report describing:

- source validation failures
- new occurrences added
- unchanged occurrences verified
- changed occurrences staged for review
- changed occurrences auto-applied
- suspected removals
- unresolved conflicts

Eclipse reconciliation should also emit a human-readable Markdown review report at
`data/catalog/reports/<run_timestamp>/review.<manifest>.md` showing the generated
description, key facts, source URL, raw snapshot reference, and accepted-vs-candidate
comparison for changed events.

## Default Policy

- Add new occurrences automatically.
- Do not silently modify accepted existing occurrences.
- For eclipse changes, generate review artifacts first and require an explicit accepted
  catalog update before publishing.
- For manual runs in a git repository, stage approved corrections in the working tree.
- For automation runs, open a pull request when corrections are detected.
- For source validation failures in automation runs, open an issue and stop.
- Never auto-delete a missing event by default. Mark it as `suspected-removed` until it is
  reviewed.
