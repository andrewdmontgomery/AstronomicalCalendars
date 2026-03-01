# AstronomicalCalendars

AstronomicalCalendars publishes subscribable `.ics` calendars for major astronomical events. AstronomicalCalendars currently publishes moon phases, equinoxes and solstices, and eclipses, with published calendar files committed under [`calendars/`](/Users/andrew/Documents/Git/GitHub/andrewdmontgomery/Calendars/calendars).

## Subscribe

The subscriber-facing calendar index, including copyable subscription URLs, lives at [`calendars/README.md`](/Users/andrew/Documents/Git/GitHub/andrewdmontgomery/Calendars/calendars/README.md).

Available calendars:

| Calendar | Includes |
| --- | --- |
| Astronomical Events | Combined feed for moon phases, equinoxes and solstices, and eclipses |
| Moon Phases | New Moon, First Quarter, Full Moon, and Last Quarter |
| Equinoxes and Solstices | March Equinox, June Solstice, September Equinox, and December Solstice |
| Eclipses | Solar and lunar eclipses with exact astronomical timing |

## Status

Phase 1 is live for astronomy sources:

- USNO moon phases
- USNO seasons
- timeanddate eclipses

Planetary calendars are planned for phase 2.

## How It Works

The pipeline validates upstream sources, fetches raw source data, normalizes candidate events, reconciles accepted catalog records, and builds published `.ics` calendar files.

## Repository Layout

- [`calendars/`](/Users/andrew/Documents/Git/GitHub/andrewdmontgomery/Calendars/calendars): published subscriber-facing `.ics` files and calendar index
- [`data/catalog/accepted/`](/Users/andrew/Documents/Git/GitHub/andrewdmontgomery/Calendars/data/catalog/accepted): accepted catalog records that feed calendar builds
- [`data/catalog/reports/`](/Users/andrew/Documents/Git/GitHub/andrewdmontgomery/Calendars/data/catalog/reports): validation, reconciliation, and build reports
- [`config/calendars/`](/Users/andrew/Documents/Git/GitHub/andrewdmontgomery/Calendars/config/calendars): calendar manifest definitions
- [`src/astrocal/`](/Users/andrew/Documents/Git/GitHub/andrewdmontgomery/Calendars/src/astrocal): Python runtime and adapters

## Local Usage

```bash
make install
.venv/bin/python -m astrocal validate astronomy --year 2026
.venv/bin/python -m astrocal run --calendar astronomy-all --year 2026
```
