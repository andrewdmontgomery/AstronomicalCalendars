# Normalized Event Schema

All source skills emit timed candidate occurrence records. Reconciliation compares those
candidates with the accepted catalog. The ICS builder reads accepted records derived from
this schema and does not depend on source-specific payload structure.

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
  "source_adapter": "timeanddate-eclipse-v1",
  "source_validation": {
    "status": "passed",
    "validated_at": "2026-03-01T12:00:00Z",
    "reason": null,
    "checks": [
      "reachable",
      "canary payload present",
      "canary required fields present",
      "required timing fields present",
      "detail url resolved"
    ],
    "canary_ok": true,
    "detail_url_ok": true
  },
  "content_hash": "sha256:...",
  "first_seen_at": "2026-03-01T12:01:00Z",
  "last_seen_at": "2026-03-01T12:01:00Z",
  "candidate_status": "new",
  "accepted_revision": null,
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

- `source_adapter`
  - Required. Identifier for the parser or adapter used to produce the candidate.

- `source_validation`
  - Required. Result of preflight validation for the source used in this run.
  - `canary_ok` records whether the source-specific structure check passed before fetch or
    normalization proceeded.

- `content_hash`
  - Required. Hash of the normalized candidate content used for change detection.

- `first_seen_at`, `last_seen_at`
  - Required timestamps tracking when the candidate was first and last observed.

- `candidate_status`
  - Required. One of `new`, `unchanged`, `changed`, `conflict`, `unusable`.

- `accepted_revision`
  - Revision of the currently accepted record matched during reconciliation, or `null`.

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
- Every candidate must carry source validation results.
- The builder should be able to create separate or combined calendars using only the
  accepted records plus a manifest.
