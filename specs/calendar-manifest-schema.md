# Calendar Manifest Schema

A calendar manifest defines how the ICS builder selects normalized events and writes one
calendar file. Separate and combined calendars are both represented by manifests.

## Required Fields

```toml
name = "astronomy-all"
output = "calendars/astronomical-events.ics"
calendar_name = "Astronomical Events"
calendar_description = "Moon phases, equinoxes and solstices, and eclipses"
variant_policy = "default"
source_validation_policy = "strict"
reconciliation_mode = "verify"
correction_mode = "apply-working-tree"
stop_on_source_failure = true
stop_on_conflict = true
```

## Optional Filters

```toml
source_types = ["astronomy", "planetary"]
bodies = ["moon", "sun", "jupiter", "saturn", "mars", "venus", "mercury"]
event_types = ["moon-phase", "season-marker", "eclipse", "opposition"]
tags = ["eclipse"]
```

## Operational Policies

- `source_validation_policy`
  - Use `strict` by default.
  - Stop the action if a required source fails validation.

- `reconciliation_mode`
  - `append-only`: add new dates only
  - `verify`: compare existing accepted dates and report corrections
  - `verify-and-apply`: compare existing accepted dates and apply corrections according to
    `correction_mode`

- `correction_mode`
  - `apply-working-tree`: for manual runs, apply corrections to the working tree
  - `report-only`: emit a reconciliation report but do not change accepted records
  - `automation-pr`: when corrections are detected in automation, prepare repo changes and
    open a pull request

- `stop_on_source_failure`
  - When `true`, stop before reconciliation or ICS generation if validation fails.

- `stop_on_conflict`
  - When `true`, stop before ICS generation if reconciliation leaves unresolved conflicts.

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

## Manual and Automation Defaults

- Manual runs should default to `correction_mode = apply-working-tree`.
- Automation runs should default to `correction_mode = automation-pr`.
- If source validation fails in automation, open an issue and stop.
- New dates can be added automatically without changing existing accepted dates.

## Builder Rules

- Generate stable `UID`s from `occurrence_id`.
- Keep sidecar sequence state so `SEQUENCE` increments only when normalized event content
  changes.
- Treat the manifest as declarative configuration. The builder should not contain
  astronomy-specific filtering logic beyond applying the manifest and variant policy.
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
source_validation_policy = "strict"
reconciliation_mode = "verify"
correction_mode = "apply-working-tree"
stop_on_source_failure = true
stop_on_conflict = true
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
source_validation_policy = "strict"
reconciliation_mode = "verify"
correction_mode = "apply-working-tree"
stop_on_source_failure = true
stop_on_conflict = true
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
source_validation_policy = "strict"
reconciliation_mode = "verify"
correction_mode = "apply-working-tree"
stop_on_source_failure = true
stop_on_conflict = true
```

### Combined astronomy calendar

```toml
name = "astronomy-all"
output = "calendars/astronomical-events.ics"
calendar_name = "Astronomical Events"
calendar_description = "Moon phases, equinoxes and solstices, and eclipses"
source_types = ["astronomy"]
variant_policy = "default"
source_validation_policy = "strict"
reconciliation_mode = "verify"
correction_mode = "apply-working-tree"
stop_on_source_failure = true
stop_on_conflict = true
```
