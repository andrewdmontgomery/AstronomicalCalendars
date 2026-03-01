# Calendar Manifest Schema

A calendar manifest defines how the ICS builder selects accepted events and writes one
published calendar file. Separate and combined calendars are both represented by manifests.

## Required Fields

```toml
name = "astronomy-all"
output = "calendars/astronomical-events.ics"
calendar_name = "Astronomical Events"
calendar_description = "Moon phases, equinoxes and solstices, and eclipses"
variant_policy = "default"
```

## Optional Filters

```toml
source_types = ["astronomy", "planetary"]
bodies = ["moon", "sun", "jupiter", "saturn", "mars", "venus", "mercury"]
event_types = ["moon-phase", "season-marker", "eclipse", "opposition"]
tags = ["eclipse"]
```

## Field Meanings

- `name`
  - Stable manifest identifier used by the CLI and report filenames.

- `output`
  - Repo-relative path for the published `.ics` file.
  - Relative outputs are resolved against the repository root.

- `calendar_name`
  - Subscriber-facing calendar display name written into the ICS metadata.

- `calendar_description`
  - Subscriber-facing calendar description written into the ICS metadata.

- `variant_policy`
  - Controls which eclipse variants are included.
  - Supported values:
    - `default`
    - `totality-only`
    - `both`

- `source_types`
  - Optional filter limiting the manifest to one or more source families.

- `bodies`
  - Optional filter for astronomical bodies such as `moon` or `jupiter`.

- `event_types`
  - Optional filter for normalized event types such as `moon-phase`, `season-marker`, or
    `eclipse`.

- `tags`
  - Optional filter for normalized record tags.

## Variant Policy

- `default`
  - Include only occurrences where `is_default = true`.

- `totality-only`
  - Include only `variant = totality` occurrences for events that have variants.

- `both`
  - Include all matching variants.

## Builder Rules

- Generate stable `UID`s from `occurrence_id`.
- Keep sidecar sequence state so `SEQUENCE` increments only when normalized event content
  changes.
- Treat the manifest as declarative configuration.
- Build from the accepted catalog, not directly from fresh candidates.

## Example Manifests

### Astronomy moon phases

```toml
name = "astronomy-moon-phases"
output = "calendars/moon-phases.ics"
calendar_name = "Moon Phases"
calendar_description = "Exact astronomical timings for the major moon phases"
source_types = ["astronomy"]
event_types = ["moon-phase"]
variant_policy = "default"
```

### Astronomy eclipses

```toml
name = "astronomy-eclipses"
output = "calendars/eclipses.ics"
calendar_name = "Eclipses"
calendar_description = "Solar and lunar eclipses with exact astronomical timing"
source_types = ["astronomy"]
event_types = ["eclipse"]
variant_policy = "default"
```

### Jupiter major events

```toml
name = "jupiter-major-events"
output = "calendars/jupiter-major-events.ics"
calendar_name = "Jupiter Major Events"
calendar_description = "Major Jupiter observing events"
source_types = ["planetary"]
bodies = ["jupiter"]
variant_policy = "default"
```

### Combined astronomy calendar

```toml
name = "astronomy-all"
output = "calendars/astronomical-events.ics"
calendar_name = "Astronomical Events"
calendar_description = "Moon phases, equinoxes and solstices, and eclipses"
source_types = ["astronomy"]
variant_policy = "default"
```
