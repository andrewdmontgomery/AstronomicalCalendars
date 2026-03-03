# AstronomicalCalendars

AstronomicalCalendars publishes subscribable `.ics` calendars for major astronomical events. AstronomicalCalendars currently publishes moon phases, equinoxes and solstices, and eclipses, with published calendar files committed under [`calendars/`](calendars/).

## Subscribe

The subscriber-facing calendar index, including copyable subscription URLs, lives at [`calendars/README.md`](calendars/README.md).

Available calendars:

| Calendar | Includes |
| --- | --- |
| Astronomical Events | Combined feed for moon phases, equinoxes and solstices, and eclipses |
| Moon Phases | New Moon, First Quarter, Full Moon, and Last Quarter |
| Equinoxes and Solstices | March Equinox, June Solstice, September Equinox, and December Solstice |
| Eclipses | Solar and lunar eclipses with exact astronomical timing |

## Current Source Coverage

AstronomicalCalendars currently publishes calendars backed by:

- USNO moon phases
- USNO seasons
- timeanddate eclipses

Planetary calendars are planned for phase 2.

## How It Works

The pipeline validates upstream sources, fetches raw source data, normalizes candidate events, reconciles accepted catalog records, and builds published `.ics` calendar files.

For eclipses, normalization will also extract a structured fact bundle that feeds
description generation. Generated eclipse copy is reviewed in Markdown before any accepted
catalog update, and the accepted catalog remains the only source for published calendar
content.

## Repository Layout

- [`calendars/`](calendars/): published subscriber-facing `.ics` files and calendar index
- [`data/catalog/accepted/`](data/catalog/accepted/): accepted catalog records that feed calendar builds
- [`data/catalog/reports/`](data/catalog/reports/): validation, reconciliation, and build reports
- [`specs/eclipse-description-fact-bundle.md`](specs/eclipse-description-fact-bundle.md): eclipse-specific fact bundle and review contract
- [`data/diagnostics/`](data/diagnostics/): source-boundary validation, fetch, and normalize diagnostics
- [`config/calendars/`](config/calendars/): calendar manifest definitions
- [`src/astrocal/`](src/astrocal/): Python runtime and adapters

## Local Usage

```bash
make install
.venv/bin/python -m astrocal validate astronomy --year 2026
.venv/bin/python -m astrocal run --calendar astronomy-all --year 2026
```

## Eclipse Review Workflow

1. Run `.venv/bin/python -m astrocal reconcile --calendar astronomy-eclipses --year 2026`
   or the equivalent `run` flow.
2. Review the generated artifacts:
   - `data/catalog/reports/<run_timestamp>/review.astronomy-eclipses.md`
   - `data/catalog/reports/<run_timestamp>/review.astronomy-eclipses.json`
   - or inspect the persisted bundle with
     `.venv/bin/python -m astrocal show-review --report data/catalog/reports/<run_timestamp>/review.astronomy-eclipses.json`
3. List pending persisted review bundles at any time with
   `.venv/bin/python -m astrocal list-pending-reviews`.
4. Approve reviewed content without editing accepted catalog JSON directly:
   - accept as-is with
     `.venv/bin/python -m astrocal approve-review --report data/catalog/reports/<run_timestamp>/review.astronomy-eclipses.json --reviewer <name> --occurrence-id <occurrence-id>`
   - or approve edited prose by also passing `--title`, `--summary`, and `--description-file`
5. Rebuild the published calendar from accepted records with
   `.venv/bin/python -m astrocal build --calendar astronomy-eclipses`.

## Maintainer Notes

Expected operator mistakes in `astrocal` should return a short `error: ...` message and
exit non-zero. Unexpected programming failures should still raise visibly, and review
bundle errors should name the artifact path that needs attention.

For source-boundary failures, use
[`skills/debug-source-adapters/SKILL.md`](skills/debug-source-adapters/SKILL.md) to inspect
reports, diagnostics, raw snapshots, normalized candidates, and reconciliation artifacts in
a fixed order.
