# iCalendar Skill Architecture

This repository is organized around a validated, normalized event pipeline. Source skills
validate their upstream sources, gather raw astronomical data, and normalize it into
candidate occurrences. A reconciliation skill compares those candidates against the accepted
catalog. A separate builder skill reads accepted events plus one or more calendar manifests
and produces `.ics` files.

## Modules

### `source-astronomy-events`

Use for moon phases, equinoxes, solstices, and eclipses.

Responsibilities:

- Validate source reachability and parseability before using the source.
- Fetch raw source data for a requested year or year range.
- Persist raw responses for traceability.
- Normalize raw data into candidate timed occurrence records defined in
  [`specs/normalized-event-schema.md`](../specs/normalized-event-schema.md).
- For eclipses, extract a structured fact bundle from normalized source data and attach it
  to candidate metadata for later description generation.
- Include a `detail_url` for every normalized occurrence.
- Emit both eclipse `full-duration` and `totality` occurrences when totality exists.
- Mark the default publishable eclipse occurrence as `full-duration`.
- Stop and notify the user when validation fails.

### `source-planetary-events`

Use for major events involving Jupiter, Saturn, Mars, Venus, and Mercury.

Responsibilities:

- Validate source reachability and parseability before using the source.
- Fetch raw event data for a requested year or year range.
- Normalize planetary events into the same candidate occurrence schema used by astronomy
  data.
- Tag each occurrence with a `body` such as `jupiter` or `venus`.
- Include a `detail_url` for every normalized occurrence.
- Stop and notify the user when validation fails.

### `reconcile-event-catalog`

Use for maintaining the accepted event catalog in a git-backed repository.

Responsibilities:

- Compare new candidate occurrences against the accepted catalog.
- Add new dates without modifying accepted existing dates.
- Verify accepted dates against fresh candidate data.
- Write accepted catalog updates directly for non-eclipse sources during manual runs.
- For eclipses, generate human-review artifacts and leave accepted catalog records unchanged
  until review is complete.
- Produce reconciliation reports for human review or automation workflows.
- Stop when source validation failed or unresolved conflicts remain.
- Open a pull request in automation contexts when corrections are detected.
- Open an issue in automation contexts when source validation fails.

### `build-ical-calendar`

Use for generating one or more `.ics` files from accepted occurrences.

Responsibilities:

- Read accepted occurrence data from the reconciliation layer.
- Read calendar manifest files defined in
  [`specs/calendar-manifest-schema.md`](../specs/calendar-manifest-schema.md).
- Generate separate calendars and combined calendars from the same event pool.
- Default eclipse publishing to `full-duration` unless the user explicitly requests
  `totality` or `both`.
- Prompt once for eclipse variant policy when interactive and the request is ambiguous.
- Generate stable `UID`s from normalized identifiers and increment `SEQUENCE` only when an
  event changes.
- Stop when reconciliation leaves unresolved conflicts or source failures.

## Data Flow

1. A source skill validates its upstream sources.
2. The source skill fetches upstream data and stores raw payloads.
3. The source skill normalizes the raw payloads into candidate occurrence records.
4. For eclipses, a description-generation step produces candidate prose from the structured
   fact bundle, then writes review-ready candidate metadata.
5. The reconciliation skill compares candidates with the accepted catalog and writes a
   report plus direct accepted-record updates for non-eclipse sources.
6. For eclipse changes, a Markdown review report is written to
   `data/catalog/reports/<run_timestamp>/review.<manifest>.md`.
7. The builder skill filters accepted records using a manifest.
8. The builder skill writes one or more `.ics` files from accepted records only.

## Shared Contracts

- Normalized event schema:
  [`specs/normalized-event-schema.md`](../specs/normalized-event-schema.md)
- Calendar manifest schema:
  [`specs/calendar-manifest-schema.md`](../specs/calendar-manifest-schema.md)
- Upstream source policy:
  [`specs/source-policy.md`](../specs/source-policy.md)
- Accepted catalog schema:
  [`specs/event-catalog-schema.md`](../specs/event-catalog-schema.md)
- Eclipse description fact bundle:
  [`specs/eclipse-description-fact-bundle.md`](../specs/eclipse-description-fact-bundle.md)

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
  catalog/
    accepted/
    reports/
  state/
    sequences/
output/
  calendars/
config/
  calendars/
```
