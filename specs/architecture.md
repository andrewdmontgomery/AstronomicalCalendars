# iCalendar Skill Architecture

This repository is organized around a normalized event pipeline. Source skills gather and
normalize raw astronomical data. A separate builder skill reads normalized events plus one
or more calendar manifests and produces `.ics` files.

## Modules

### `source-astronomy-events`

Use for moon phases, equinoxes, solstices, and eclipses.

Responsibilities:

- Fetch raw source data for a requested year or year range.
- Persist raw responses for traceability.
- Normalize raw data into timed occurrence records defined in
  [`specs/normalized-event-schema.md`](../specs/normalized-event-schema.md).
- Include a `detail_url` for every normalized occurrence.
- Emit both eclipse `full-duration` and `totality` occurrences when totality exists.
- Mark the default publishable eclipse occurrence as `full-duration`.

### `source-planetary-events`

Use for major events involving Jupiter, Saturn, Mars, Venus, and Mercury.

Responsibilities:

- Fetch raw event data for a requested year or year range.
- Normalize planetary events into the same timed occurrence schema used by astronomy data.
- Tag each occurrence with a `body` such as `jupiter` or `venus`.
- Include a `detail_url` for every normalized occurrence.

### `build-ical-calendar`

Use for generating one or more `.ics` files from normalized occurrences.

Responsibilities:

- Read normalized occurrence data from one or more source modules.
- Read calendar manifest files defined in
  [`specs/calendar-manifest-schema.md`](../specs/calendar-manifest-schema.md).
- Generate separate calendars and combined calendars from the same event pool.
- Default eclipse publishing to `full-duration` unless the user explicitly requests
  `totality` or `both`.
- Prompt once for eclipse variant policy when interactive and the request is ambiguous.
- Generate stable `UID`s from normalized identifiers and increment `SEQUENCE` only when an
  event changes.

## Data Flow

1. A source skill fetches upstream data and stores raw payloads.
2. The source skill normalizes the raw payloads into occurrence records.
3. The builder skill filters those normalized records using a manifest.
4. The builder skill writes one or more `.ics` files.

## Shared Contracts

- Normalized event schema:
  [`specs/normalized-event-schema.md`](../specs/normalized-event-schema.md)
- Calendar manifest schema:
  [`specs/calendar-manifest-schema.md`](../specs/calendar-manifest-schema.md)
- Upstream source policy:
  [`specs/source-policy.md`](../specs/source-policy.md)

## Default Calendar Set

Recommended first-pass manifests:

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

## Storage Layout

Suggested repository layout for generated artifacts:

```text
data/
  raw/
    astronomy/
    planetary/
  normalized/
    astronomy/
    planetary/
  state/
    sequences/
output/
  calendars/
config/
  calendars/
```
