---
name: source-astronomy-events
description: Fetch and normalize moon phases, equinoxes, solstices, and eclipses into timed occurrence records for iCalendar generation. Use when Codex needs to gather raw astronomical event data, preserve source provenance, attach per-event detail URLs, or prepare normalized astronomy events for separate or combined calendars.
---

# Source Astronomy Events

Normalize astronomy data into candidate occurrence records before any calendar generation.
Treat `specs/` as the source of truth for source selection, validation, and schema rules.

## Workflow

1. Determine the requested year or year range.
2. Read [`specs/source-policy.md`](../../specs/source-policy.md).
3. Read [`specs/normalized-event-schema.md`](../../specs/normalized-event-schema.md).
4. Validate each required source before using it.
5. Stop immediately and notify the user if any required validation fails.
6. Fetch raw data and save it under `data/raw/astronomy/...`.
7. Normalize the raw data into candidate occurrence records defined in
   [`specs/normalized-event-schema.md`](../../specs/normalized-event-schema.md).
8. Write normalized output under `data/normalized/astronomy/...`.

If validation, fetch, or normalization fails, use
[`debug-source-adapters`](../debug-source-adapters/SKILL.md) before changing parser logic.

## Output Expectations

Expected outputs:

- raw payload files under `data/raw/astronomy/...`
- normalized occurrence files under `data/normalized/astronomy/...`

The reconciliation skill decides whether these candidates become accepted records.
