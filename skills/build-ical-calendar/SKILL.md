---
name: build-ical-calendar
description: Build or update iCalendar files from normalized timed occurrence records and declarative calendar manifests. Use when Codex needs to generate separate or combined `.ics` calendars, apply eclipse variant rules, preserve stable event identity, or rebuild calendar artifacts from normalized event data.
---

# Build iCal Calendar

Generate `.ics` files only from accepted catalog records and manifests. Do not parse raw
upstream source pages here.

## Workflow

1. Read accepted catalog data derived from
   [`specs/normalized-event-schema.md`](../../specs/normalized-event-schema.md) and
   [`specs/event-catalog-schema.md`](../../specs/event-catalog-schema.md).
2. Read one or more manifests that conform to
   [`specs/calendar-manifest-schema.md`](../../specs/calendar-manifest-schema.md).
3. Filter occurrences by `source_type`, `body`, `event_type`, `tags`, and `variant_policy`.
4. Write `.ics` output files and update sequence state.

## Manifest Rules

- Treat the manifest as declarative configuration.
- Allow separate calendars and combined calendars to be built from the same event pool.
- Do not hard-code astronomy-specific calendar definitions into builder logic.
- Respect reconciliation and source-failure stop conditions before building.

## Eclipse Variant Rules

- Default to `variant_policy = default`.
- For eclipses, `default` means publish the `full-duration` occurrence.
- If interaction is possible and the request is ambiguous, prompt once:
  - `full-duration` as the recommended default
  - `totality-only`
  - `both`
- If interaction is not possible, keep the default policy.

## ICS Rules

- Derive `UID` from the stable `occurrence_id`.
- Preserve stable `UID`s across rebuilds.
- Increment `SEQUENCE` only when the normalized event content changes.
- Use timed events for all astronomy and planetary records covered by this repository.
- Include the normalized `detail_url` in the event.
- Stop when source validation failed or reconciliation left unresolved conflicts.

## Output Expectations

Suggested outputs:

- `.ics` files under `output/calendars/...`
- sequence state under `data/state/sequences/...`

## Example Manifest Families

- `astronomy-moon-phases`
- `astronomy-seasons`
- `astronomy-eclipses`
- `astronomy-all`
- `jupiter-major-events`
- `saturn-major-events`
- `mars-major-events`
- `venus-major-events`
- `mercury-major-events`
- `all-planetary-events`
