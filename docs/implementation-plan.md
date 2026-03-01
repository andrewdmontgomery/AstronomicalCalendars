# Validated Phase 1 Plan for AstronomicalCalendars Python Runtime

## Summary

This plan is validated against the repository's current contracts and the loaded skills:

- `python-design-patterns`: keep the implementation explicit, layered, and small; avoid registries, plugin systems, and inheritance-heavy abstractions.
- `python-testing-patterns`: make the pipeline fixture-driven, isolate adapters from services, and test orchestration and reconciliation behavior explicitly.
- `git-storytelling-commit-strategy`: implement in small, narrative commits that preserve the development story and keep each checkpoint stable.

The main correction required to make the plan decision-complete is:

- Phase 1 must treat `astronomy-all` as an astronomy-only combined manifest.
- Planetary support remains Phase 2.
- The current mixed-scope manifest and any related docs/spec text must be updated during implementation so phase-1 acceptance criteria, manifests, and runtime behavior are consistent.

This plan keeps the existing schema-driven architecture in `specs/architecture.md` and turns it into an executable Python package for manual astronomy runs.

## Validated Decisions

### Scope

Phase 1 includes only:

- moon phases
- seasons
- eclipses
- combined astronomy calendar

Phase 2 includes:

- planetary adapters
- planetary manifests
- combined planetary output

### Manifest Decision

For Phase 1:

- `config/calendars/astronomy-all.toml` must be updated to `source_types = ["astronomy"]`.
- Create or promote these manifests as executable phase-1 targets:
  - `astronomy-moon-phases`
  - `astronomy-seasons`
  - `astronomy-eclipses`
  - `astronomy-all`
- Planetary manifests may remain in the repo, but they are explicitly non-executable for phase 1 unless marked as phase-2-only in docs/spec text.

### Runtime Entry Point

Canonical interface:

```bash
python -m astronomical_calendars validate astronomy --year 2026
python -m astronomical_calendars fetch astronomy --year 2026
python -m astronomical_calendars normalize astronomy --year 2026
python -m astronomical_calendars reconcile --calendar astronomy-all --year 2026
python -m astronomical_calendars build --calendar astronomy-all
python -m astronomical_calendars run --calendar astronomy-all --year 2026
```

`Makefile` remains a thin wrapper only.

## Public APIs, Interfaces, and Types

### Python Package Layout

Implement under:

```text
src/astronomical_calendars/
  __init__.py
  __main__.py
  cli.py
  paths.py
  hashing.py
  jsonio.py
  manifests.py
  models/
    __init__.py
    candidate.py
    catalog.py
    reports.py
    manifest.py
  adapters/
    __init__.py
    astronomy/
      __init__.py
      usno_moon_phases.py
      usno_seasons.py
      timeanddate_eclipses.py
  services/
    __init__.py
    validation_service.py
    fetch_service.py
    normalize_service.py
    reconcile_service.py
    build_ics_service.py
    run_service.py
  repositories/
    __init__.py
    raw_store.py
    candidate_store.py
    catalog_store.py
    report_store.py
    sequence_store.py
  git/
    __init__.py
    staging.py
  renderers/
    __init__.py
    markdown_report.py
```

Decision:
- add `__main__.py` so `python -m astronomical_calendars` works cleanly.

### Layer Responsibilities

- CLI layer: parse arguments, map to service calls, set exit codes.
- Adapter layer: source-specific validation, fetch, parse, normalize.
- Service layer: orchestration and business rules only.
- Repository layer: filesystem persistence only.
- Git helper: staging only, no commit logic.
- Renderer layer: Markdown report formatting only.

No adapter inheritance tree. No plugin registry. Use explicit adapter maps.

### Adapter Interface

Use a simple protocol:

```python
class SourceAdapter(Protocol):
    source_name: str
    source_type: str

    def validate(self, year: int) -> ValidationReport: ...
    def fetch(self, year: int) -> RawFetchResult: ...
    def normalize(
        self,
        year: int,
        raw_result: RawFetchResult,
    ) -> list[CandidateRecord]: ...
```

Adapter registration is explicit:

```python
ASTRONOMY_ADAPTERS = {
    "moon-phases": MoonPhasesAdapter(...),
    "seasons": SeasonsAdapter(...),
    "eclipses": EclipsesAdapter(...),
}
```

### Typed Models

Implement typed Python representations for:

- `CandidateRecord`
- `AcceptedRecord`
- `CalendarManifest`
- `ValidationReport`
- `RawFetchResult`
- `ReconciliationReport`
- `BuildReport`

Decision:
- use `dataclass` models plus explicit serializer/deserializer helpers.
- do not add `pydantic` in phase 1.

### CLI Contract

Subcommands:

- `validate`
- `fetch`
- `normalize`
- `reconcile`
- `build`
- `run`

Supported flags in phase 1:

- `--year`
- `--calendar`
- `--variant-policy`
- `--report-dir`
- `--no-stage`

Exit codes:

- `0` success
- non-zero for validation failure, normalization failure, reconciliation stop, build failure, or invalid CLI usage

Decision:
- `--source-family` is not needed as a general flag because `validate/fetch/normalize` already take the family positionally.

## Data Flow and Storage

### Storage Layout

Tracked outputs:

- `data/catalog/accepted/<source-type>/<year>/<source-name>.json`
- `data/catalog/reports/<run-timestamp>/...`
- `calendars/*.ics`
- `data/state/sequences/*.json` if sequence persistence is required for deterministic subscription semantics

Untracked outputs:

- `data/raw/...`
- `data/normalized/...`

### Reconciliation Rules

Implement exactly:

- match on `occurrence_id`
- new candidate: create revision 1 active record
- unchanged hash: keep active, report unchanged
- changed hash: create new revision, supersede prior revision, generate deterministic change summary
- missing candidate: mark active record as `suspected-removed`
- validation failure: stop before catalog modification and before build

Decision:
- manual mode writes changed catalog files, report files, and built `.ics` files to the working tree
- commits remain an explicit user action

### ICS Rules

Build from accepted active records only.

Rules:

- stable UID from `occurrence_id`
- persistent `SEQUENCE`
- include `detail_url`
- moon phases and seasons are instant timed events with no `DTEND`
- eclipses include `DTEND` when duration exists
- default eclipse variant handling follows manifest `variant_policy = "default"`

Decision:
- in phase 1, `default` means "records with `is_default = true`"; no extra `full-duration` special case should be hardcoded outside that policy.

## Testing Plan

### Test Layout

```text
tests/
  adapters/
    test_usno_moon_phases.py
    test_usno_seasons.py
    test_timeanddate_eclipses.py
  services/
    test_validation_service.py
    test_fetch_service.py
    test_normalize_service.py
    test_reconcile_service.py
    test_build_ics_service.py
    test_run_service.py
  cli/
    test_cli_validate.py
    test_cli_build.py
    test_cli_run.py
  repositories/
    test_catalog_store.py
    test_sequence_store.py
  fixtures/
    usno/
    timeanddate/
    in_the_sky/
```

Decision:
- add repository tests because this plan relies on JSON persistence and sequence-state semantics; those are stable-core behavior and should not be left untested.

### Required Scenarios

Adapter validation:

- valid USNO moon phase fixture passes
- valid USNO seasons fixture passes
- valid timeanddate eclipse fixture passes
- missing required source fields fail with explicit reason
- unresolved detail URL derivation fails validation

Normalization:

- moon phases normalize to instant timed events
- seasons normalize to instant timed events
- eclipses normalize to `full-duration` and `totality` where applicable
- `occurrence_id` is stable
- `content_hash` is deterministic

Reconciliation:

- new record creates revision 1
- unchanged record remains active
- changed record creates superseding revision
- missing current candidate becomes `suspected-removed`
- failed validation blocks writes
- manual staging includes expected files
- `--no-stage` skips staging

ICS build:

- instant events omit `DTEND`
- duration events include `DTEND`
- UID stability across rebuilds
- `SEQUENCE` increments only on content changes
- manifest filtering excludes unrelated events
- default eclipse policy includes only `is_default = true`

CLI:

- `validate` returns non-zero on failed validation
- `build` reads accepted records only
- `run` orchestrates validate -> fetch -> normalize -> reconcile -> build
- phase-1 `astronomy-all` succeeds without planetary adapters

## Dependencies

Keep and extend `requirements-dev.txt` with:

- `PyYAML`
- `requests`
- `icalendar`
- `python-dateutil`
- `pytest`
- `pytest-mock`
- `beautifulsoup4`
- `lxml`

Decision:
- phase 1 does not add `Typer`, `Click`, or `pydantic`.

## Implementation Sequence

### Code Delivery Order

1. Create package skeleton with `__main__.py`, `cli.py`, and shared path/json/hash helpers.
2. Add dataclass models and serializers for manifest, candidate, catalog, and reports.
3. Implement manifest loading against `specs/calendar-manifest-schema.md`.
4. Implement repository stores for raw, normalized, catalog, reports, and sequence state.
5. Implement validation/fetch/normalize services with explicit astronomy adapter wiring.
6. Implement USNO moon phases adapter.
7. Implement USNO seasons adapter.
8. Implement timeanddate eclipses adapter.
9. Implement reconciliation service and git staging helper.
10. Implement ICS build service.
11. Implement run orchestration service.
12. Add or update astronomy manifests for phase-1 scope, including making `astronomy-all` astronomy-only.
13. Add fixture-driven pytest coverage.
14. Extend `Makefile` with thin wrappers for `install`, `test`, `validate-skills`, and `run`.
15. Update docs/spec text only where needed to reflect the finalized phase-1 scope and executable contract.

## Commit Strategy

Use small, stable commits that tell the implementation story:

1. `feat: scaffold astronomical_calendars package and CLI entrypoint`
2. `feat: add typed models and filesystem stores for pipeline artifacts`
3. `feat: load calendar manifests from config`
4. `feat: implement moon phase adapter and normalization`
5. `feat: implement seasons adapter and normalization`
6. `feat: implement eclipse adapter and normalization`
7. `feat: add reconciliation service and git staging helper`
8. `feat: build ICS output from accepted catalog records`
9. `test: add fixture-driven adapter and service coverage`
10. `docs: align manifests and phase-1 scope with astronomy-only combined calendar`

Rule:
- each commit must leave tests for touched behavior passing
- no WIP commits
- no mixed refactor/feature/test/doc dumps

## Assumptions and Defaults

- Phase 1 is manual-run only.
- `astronomy-all` is astronomy-only for phase 1.
- Planetary manifests are phase-2 work, even if some config files remain present.
- Raw and normalized artifacts are not committed by default.
- Reports, accepted catalog files, and `.ics` outputs are committed/staged in manual runs.
- `argparse` is the CLI framework.
- `dataclass` models are sufficient for phase 1.
- Live source checks are runtime validation commands, not normal automated tests.
- The implementation must preserve enough diagnostics for future debug-skill work:
  - validation report
  - raw snapshot
  - parse summary
  - normalized candidate output
  - reconciliation report
  - failure reason

## Acceptance Criteria

Phase 1 is complete when:

- `python -m astronomical_calendars run --calendar astronomy-all --year 2026` completes successfully for astronomy sources only
- validation failures stop the run before reconciliation and build
- moon phases, seasons, and eclipses write candidate JSON
- accepted catalog files update by source and year
- reconciliation stages tracked changes in manual mode
- `.ics` outputs are generated for all phase-1 astronomy manifests
- fixture-driven pytest coverage exists for adapters, services, repositories, and CLI orchestration
- generated artifacts and reports are sufficient for later debugging-skill automation
