---
name: build-ical-calendar
description: Build or update iCalendar files from normalized timed occurrence records and declarative calendar manifests. Use when Codex needs to generate separate or combined `.ics` calendars, apply eclipse variant rules, preserve stable event identity, or rebuild calendar artifacts from normalized event data.
---

# Build iCal Calendar

Generate `.ics` files only from accepted catalog records and manifests. Do not parse raw
upstream source pages here. Treat `specs/` and manifests as the source of truth for build
rules.

## Workflow

1. Read accepted catalog data derived from
   [`specs/normalized-event-schema.md`](../../specs/normalized-event-schema.md) and
   [`specs/event-catalog-schema.md`](../../specs/event-catalog-schema.md).
2. Read one or more manifests that conform to
   [`specs/calendar-manifest-schema.md`](../../specs/calendar-manifest-schema.md).
3. Stop when source validation failed or reconciliation left unresolved conflicts.
4. Filter occurrences according to the manifest.
5. Write `.ics` output files and update sequence state.

## Output Expectations

Suggested outputs:

- `.ics` files under `output/calendars/...`
- sequence state under `data/state/sequences/...`
