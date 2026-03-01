---
name: source-planetary-events
description: Fetch and normalize major Jupiter, Saturn, Mars, Venus, and Mercury events into timed occurrence records for iCalendar generation. Use when Codex needs planetary event data with exact timestamps, per-event detail URLs, source provenance, or normalized outputs that can feed separate planet calendars or combined astronomy calendars.
---

# Source Planetary Events

Normalize planetary event data into the same occurrence schema used by astronomy sources.
Treat `specs/` as the source of truth for source selection, validation, and schema rules.

## Workflow

1. Determine the requested year or year range.
2. Read [`specs/source-policy.md`](../../specs/source-policy.md).
3. Read [`specs/normalized-event-schema.md`](../../specs/normalized-event-schema.md).
4. Validate each required source before using it.
5. Stop immediately and notify the user if any required validation fails.
6. Fetch raw data and save it under `data/raw/planetary/...`.
7. Normalize the raw data into candidate occurrence records defined in
   [`specs/normalized-event-schema.md`](../../specs/normalized-event-schema.md).
8. Write normalized output under `data/normalized/planetary/...`.

## Output Expectations

Expected outputs:

- raw payload files under `data/raw/planetary/...`
- normalized occurrence files under `data/normalized/planetary/...`

The reconciliation skill decides whether these candidates become accepted records.
