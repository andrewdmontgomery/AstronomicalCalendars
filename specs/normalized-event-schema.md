# Normalized Event Schema

All source skills emit timed occurrence records. The ICS builder reads only this schema and
does not depend on source-specific payload structure.

## Required Fields

```json
{
  "group_id": "astronomy/eclipse/2026-08-12/total-solar",
  "occurrence_id": "astronomy/eclipse/2026-08-12/total-solar/full-duration",
  "source_type": "astronomy",
  "body": "sun",
  "event_type": "eclipse",
  "variant": "full-duration",
  "is_default": true,
  "title": "Total Solar Eclipse",
  "summary": "Total Solar Eclipse",
  "description": "Visible astronomical event with exact timing and a detail link.",
  "start": "2026-08-12T15:42:00Z",
  "end": "2026-08-12T18:11:00Z",
  "all_day": false,
  "timezone": "UTC",
  "categories": ["Astronomy", "Eclipse"],
  "tags": ["eclipse", "solar", "total"],
  "detail_url": "https://example.com/event",
  "timing_source": {
    "name": "timeanddate",
    "url": "https://example.com/event"
  },
  "validation_sources": [],
  "metadata": {},
  "raw_ref": "data/raw/astronomy/2026/eclipse.json"
}
```

## Field Rules

- `group_id`
  - Stable identifier for related occurrences that describe the same event.
  - Example: an eclipse group that contains both `full-duration` and `totality`.

- `occurrence_id`
  - Stable identifier for one publishable occurrence.
  - This is the source material for deterministic calendar `UID`s.

- `source_type`
  - One of `astronomy` or `planetary`.

- `body`
  - Primary celestial body associated with the event.
  - Examples: `moon`, `sun`, `jupiter`, `saturn`, `mars`, `venus`, `mercury`.

- `event_type`
  - Examples: `moon-phase`, `season-marker`, `eclipse`, `opposition`, `conjunction`,
    `greatest-elongation`, `station`.

- `variant`
  - Defaults to `default` for ordinary timed events.
  - Use `full-duration` and `totality` for eclipses.

- `is_default`
  - The builder uses this when manifest policy is `default`.
  - For eclipses, set `full-duration` to `true` and `totality` to `false`.

- `start`, `end`
  - Use exact timestamps with offset.
  - `end` may be `null` for instant events such as moon phases or equinox timestamps.

- `all_day`
  - Always `false` for the astronomy and planetary event families covered here.

- `detail_url`
  - Required. Link to a user-facing page for that exact occurrence.

- `timing_source`
  - Required. Describe the upstream source used for event timing.

- `validation_sources`
  - Optional secondary sources used to confirm correctness.

- `raw_ref`
  - Required path to stored raw payload or source snapshot used to derive the record.

## Event-Specific Rules

### Moon phases

- Emit one timed occurrence per major phase.
- Use `event_type = moon-phase`.
- Use `variant = default`.
- Omit `end`.

### Equinoxes and solstices

- Emit one timed occurrence per seasonal marker.
- Use `event_type = season-marker`.
- Omit `end`.

### Eclipses

- Emit one `full-duration` occurrence when start and end are available.
- Emit one `totality` occurrence when a totality window exists.
- Both records share the same `group_id`.
- Mark `full-duration` as `is_default = true`.

### Planetary events

- Emit timed occurrences for whichever planetary event types are supported by the source.
- Always set `body`.
- Omit `end` for instant events unless the source defines a meaningful duration.

## Invariants

- `occurrence_id` must remain stable across rebuilds for the same logical occurrence.
- Every publishable occurrence must have a `detail_url`.
- Every occurrence must be traceable to a raw payload.
- The builder should be able to create separate or combined calendars using only the
  normalized records plus a manifest.
