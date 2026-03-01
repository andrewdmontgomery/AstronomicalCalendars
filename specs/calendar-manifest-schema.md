# Calendar Manifest Schema

A calendar manifest defines how the ICS builder selects normalized events and writes one
calendar file. Separate and combined calendars are both represented by manifests.

## Required Fields

```toml
name = "astronomy-all"
output = "output/calendars/astronomy-all.ics"
calendar_name = "Astronomical Events"
calendar_description = "Moon phases, seasons, eclipses, and planetary events"
variant_policy = "default"
```

## Optional Filters

```toml
source_types = ["astronomy", "planetary"]
bodies = ["moon", "sun", "jupiter", "saturn", "mars", "venus", "mercury"]
event_types = ["moon-phase", "season-marker", "eclipse", "opposition"]
tags = ["eclipse"]
```

## Variant Policy

- `default`
  - Include only occurrences where `is_default = true`.
  - This is the default behavior and should be assumed when the user does not specify an
    eclipse preference.

- `totality-only`
  - Include only `variant = totality` occurrences for events that have variants.

- `both`
  - Include all matching variants.

## Interactive Rule

If a requested manifest includes eclipses and the user did not specify a variant policy:

- Prompt once when interaction is possible.
- Offer:
  - `full-duration` as the recommended default
  - `totality-only`
  - `both`
- If no prompt is possible, resolve to `default`.

## Builder Rules

- Generate stable `UID`s from `occurrence_id`.
- Keep sidecar sequence state so `SEQUENCE` increments only when normalized event content
  changes.
- Treat the manifest as declarative configuration. The builder should not contain
  astronomy-specific filtering logic beyond applying the manifest and variant policy.

## Example Manifests

### Astronomy moon phases

```toml
name = "astronomy-moon-phases"
output = "output/calendars/astronomy-moon-phases.ics"
calendar_name = "Moon Phases"
calendar_description = "Major moon phase events"
source_types = ["astronomy"]
event_types = ["moon-phase"]
variant_policy = "default"
```

### Astronomy eclipses

```toml
name = "astronomy-eclipses"
output = "output/calendars/astronomy-eclipses.ics"
calendar_name = "Eclipses"
calendar_description = "Solar and lunar eclipses"
source_types = ["astronomy"]
event_types = ["eclipse"]
variant_policy = "default"
```

### Jupiter major events

```toml
name = "jupiter-major-events"
output = "output/calendars/jupiter-major-events.ics"
calendar_name = "Jupiter Major Events"
calendar_description = "Major Jupiter observing events"
source_types = ["planetary"]
bodies = ["jupiter"]
variant_policy = "default"
```

### Combined astronomy calendar

```toml
name = "astronomy-all"
output = "output/calendars/astronomy-all.ics"
calendar_name = "Astronomical Events"
calendar_description = "Moon phases, seasons, eclipses, and planetary events"
source_types = ["astronomy", "planetary"]
variant_policy = "default"
```
