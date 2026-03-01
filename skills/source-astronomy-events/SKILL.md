---
name: source-astronomy-events
description: Fetch and normalize moon phases, equinoxes, solstices, and eclipses into timed occurrence records for iCalendar generation. Use when Codex needs to gather raw astronomical event data, preserve source provenance, attach per-event detail URLs, or prepare normalized astronomy events for separate or combined calendars.
---

# Source Astronomy Events

Normalize astronomy data into the shared occurrence schema before any calendar generation.
Treat raw source payloads as inputs and normalized occurrence records as the publishable
intermediate format.

## Workflow

1. Determine the requested year or year range.
2. Read [`specs/source-policy.md`](../../specs/source-policy.md) for the approved source mix.
3. Fetch raw data and save it under `data/raw/astronomy/...`.
4. Normalize the raw data into occurrence records defined in
   [`specs/normalized-event-schema.md`](../../specs/normalized-event-schema.md).
5. Write normalized output under `data/normalized/astronomy/...`.

## Source Rules

- Use USNO as the primary timing source for moon phases and seasonal markers.
- Use In-The-Sky event pages as the required `detail_url` source for moon phases and
  seasonal markers.
- Use timeanddate eclipse pages for both eclipse timing and eclipse `detail_url`.
- Record timing provenance in `timing_source` and any cross-check pages in
  `validation_sources`.
- Do not publish an occurrence unless it has a stable `detail_url`.

## Event Rules

### Moon phases

- Emit one timed occurrence for each major phase.
- Set `event_type = moon-phase`.
- Use `variant = default`.
- Leave `end = null`.

### Equinoxes and solstices

- Emit one timed occurrence for each seasonal marker.
- Set `event_type = season-marker`.
- Leave `end = null`.

### Eclipses

- Emit a `full-duration` occurrence when contact times permit a start and end window.
- Emit a `totality` occurrence when the source provides a totality window.
- Share `group_id` across related eclipse occurrences.
- Set `is_default = true` on `full-duration`.
- Set `is_default = false` on `totality`.

## Normalization Rules

- Preserve source-specific identifiers in `metadata` when available.
- Convert all timestamps to ISO 8601 with offset.
- Use UTC unless the upstream source clearly requires another timezone.
- Keep `occurrence_id` stable across rebuilds.
- Include the raw payload path in `raw_ref`.

## Output Expectations

Expected outputs:

- raw payload files under `data/raw/astronomy/...`
- normalized occurrence files under `data/normalized/astronomy/...`

The builder skill should be able to create astronomy-only or combined calendars without
re-reading raw source pages.
