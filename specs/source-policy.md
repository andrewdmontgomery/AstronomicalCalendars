# Source Policy

Every normalized occurrence must include both authoritative timing provenance and a
user-facing detail URL. No event should be published without a usable `detail_url`.

Every source must be validated before it is used for a live run. If validation fails, the
action stops and the user is notified.

## Source Selection Rules

For each event type, record:

- `timing_source.name`
- `timing_source.url`
- `detail_url`
- optional `validation_sources`

If a single upstream page provides both reliable timing and a good detail page, use the
same URL for `timing_source.url` and `detail_url`.

## Validation Rules

Before any live fetch or normalization run, validate the chosen source adapter:

- the endpoint or page is reachable
- the expected response shape or page markers are present
- required timing fields for that event family are present
- the detail URL pattern still resolves
- the parser can extract a known canary event when a fixture or canary is available

If any required validation fails:

- mark the source as unusable for that run
- notify the user with a concrete failure reason
- stop the action before normalization
- in automation contexts, open an issue instead of continuing

## Preferred Sources

### Moon phases

- Timing source: USNO moon phase API
- Detail URL source: In-The-Sky moon phase event pages
- Rationale: USNO is authoritative for exact primary phase times. In-The-Sky provides
  event-specific pages suitable for calendar links.

### Equinoxes and solstices

- Timing source: USNO seasons API
- Detail URL source: In-The-Sky seasonal event pages
- Rationale: USNO is authoritative for season timestamps. In-The-Sky provides user-facing
  event pages with context.

### Eclipses

- Timing source: timeanddate eclipse event pages
- Detail URL source: same timeanddate event pages
- Validation source: In-The-Sky eclipse pages when useful
- Rationale: timeanddate pages expose staged timings and duration summaries needed for both
  `full-duration` and `totality` occurrences.

### Planetary events

- Timing source: In-The-Sky event pages
- Detail URL source: same In-The-Sky event pages
- Rationale: In-The-Sky provides broad per-event coverage for planetary conjunctions,
  oppositions, elongations, and related events with stable detail pages.

## Source Fallback Rules

- Prefer the configured primary source for a category.
- If the timing source is unavailable, fail clearly rather than silently publishing low
  confidence data.
- If exact timing is available but no stable detail URL can be found, keep the event out of
  the publishable set until a detail URL rule is added.
- Record source-specific parsing assumptions in the raw metadata for auditability.

## Normalization Rules

- Preserve the original upstream identifier when available in `metadata.source_id`.
- Save raw responses to disk before normalization.
- Carry enough provenance to reproduce the normalized record from raw data.
- Convert all timestamps to ISO 8601 with offset.
- Use UTC when the source does not provide a location-specific timezone requirement.

## Event URL Rules

- `detail_url` should point to a page a user can open for more information about that exact
  occurrence.
- Avoid generic overview pages when a per-event page exists.
- Use HTTPS URLs.
- Keep the event URL stable across rebuilds whenever the upstream source allows it.
