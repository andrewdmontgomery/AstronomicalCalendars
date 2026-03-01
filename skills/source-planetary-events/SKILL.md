---
name: source-planetary-events
description: Fetch and normalize major Jupiter, Saturn, Mars, Venus, and Mercury events into timed occurrence records for iCalendar generation. Use when Codex needs planetary event data with exact timestamps, per-event detail URLs, source provenance, or normalized outputs that can feed separate planet calendars or combined astronomy calendars.
---

# Source Planetary Events

Normalize planetary event data into the same occurrence schema used by astronomy sources.
Keep planetary sourcing independent from ICS generation so new planets or event classes do
not require builder changes.

## Workflow

1. Determine the requested year or year range.
2. Read [`specs/source-policy.md`](../../specs/source-policy.md) for source selection.
3. Validate each required source before using it.
4. Stop immediately and notify the user if any required validation fails.
5. Fetch raw data and save it under `data/raw/planetary/...`.
6. Normalize the raw data into candidate occurrence records defined in
   [`specs/normalized-event-schema.md`](../../specs/normalized-event-schema.md).
7. Write normalized output under `data/normalized/planetary/...`.

## Source Rules

- Use In-The-Sky event pages as the primary timing source and `detail_url` source for
  planetary events unless a more authoritative per-event source is added to the source
  policy.
- Prefer pages for exact occurrences over generic planet overview pages.
- Fail clearly when exact timing is available but no stable per-event detail page can be
  attached.

## Validation Rules

- Validate source reachability before fetching.
- Validate that required response fields or page markers still exist.
- Validate that a stable `detail_url` can still be derived.
- Validate that the current adapter can parse the source shape.
- Record validation outcomes in each candidate's `source_validation` field.
- If validation fails, mark the source as unusable for the run and stop.

## Event Rules

- Always set `source_type = planetary`.
- Always set `body` to one of `jupiter`, `saturn`, `mars`, `venus`, or `mercury`.
- Use `variant = default` unless a future planetary event family requires sub-occurrences.
- Omit `end` for instant events unless the source defines a meaningful duration window.

## Supported Event Families

Normalize any supported planetary event into the shared schema. Expected early event types
include:

- `opposition`
- `conjunction`
- `greatest-elongation`
- `station`

Add new event types by extending the source parser and preserving the same schema contract.

## Normalization Rules

- Keep `occurrence_id` stable across rebuilds.
- Preserve source-specific identifiers in `metadata` when available.
- Carry the upstream detail page in `detail_url`.
- Include the raw payload path in `raw_ref`.

## Output Expectations

Expected outputs:

- raw payload files under `data/raw/planetary/...`
- normalized occurrence files under `data/normalized/planetary/...`

The reconciliation skill should decide whether these candidates become accepted records.
