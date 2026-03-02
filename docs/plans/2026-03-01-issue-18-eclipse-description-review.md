# Issue 18 Eclipse Description Review Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add review-gated, agent-generated eclipse descriptions derived from structured facts, while keeping the accepted catalog as the only source for published `.ics` output.

**Architecture:** Extend eclipse normalization so each candidate carries a structured fact bundle, then run description generation on those normalized facts instead of raw HTML. Reuse reconciliation-style comparison to write JSON and Markdown review artifacts for eclipses, but do not publish new eclipse descriptions until a human has updated the accepted catalog and rerun the build.

**Tech Stack:** Python 3, dataclasses, BeautifulSoup, pytest, Markdown report generation, existing `astrocal` repositories/services.

---

## Implementation Decisions

- Generate descriptions **after** normalization into occurrence variants. This keeps full-duration and totality prose variant-specific and testable.
- Store the eclipse fact bundle in `CandidateRecord.metadata`, and preserve that metadata in accepted records by copying it into `AcceptedRecord.record.metadata` when a reviewer accepts a change.
- Use `data/catalog/reports/<run_timestamp>/review.<manifest>.md` for the human-readable review report so it sits beside `reconcile.<manifest>.json` and `build.<manifest>.json`.
- Distinguish `facts wrong` from `prose wrong` in review metadata:
  - `description_review.resolution = "facts-corrected"` when the reviewer changes structured facts or timing-derived content.
  - `description_review.resolution = "prose-edited"` when the reviewer keeps the facts but edits title/summary/description.
- Manual accepted-description changes should create a **new accepted revision**, not edit an active revision in place. That keeps review history auditable and fits the existing `revision` model.
- Reconciliation for eclipses should become **review-gated**:
  - moon phases and seasons can keep current auto-accept behavior.
  - eclipse new/changed/suspected-removed records should produce review artifacts and leave the accepted catalog unchanged until a human updates it.

## Recommended Commit Story

1. `docs: define eclipse description review workflow`
2. `feat: capture eclipse fact bundles during normalization`
3. `feat: add review-gated eclipse description generation`
4. `feat: write markdown eclipse review reports`
5. `refactor: split reconciliation diffing from catalog writes`
6. `test: cover manual eclipse acceptance workflow`

### Task 1: Codify The Contracts

**Files:**
- Create: `specs/eclipse-description-fact-bundle.md`
- Modify: `specs/architecture.md`
- Modify: `specs/event-catalog-schema.md`
- Modify: `README.md`

**Step 1: Write the contract updates**

- Define the first-pass eclipse fact bundle shape:
  - identity: `body`, `degree`, `canonical_title`
  - timing: `full_duration`, `special_phase`
  - visibility: `partial_regions`, `path_countries`, `visibility_note`
  - provenance: `detail_url`, `raw_ref`, `facts_schema_version`
- Document that eclipse description generation happens after normalization and before human acceptance.
- Document that accepted eclipse records are updated only after review.

**Step 2: Review the storage and workflow wording**

Check that the docs consistently point to:
- `data/normalized/astronomy/<year>/eclipses.json`
- `data/catalog/reports/<run_timestamp>/review.<manifest>.md`
- `data/catalog/accepted/astronomy/<year>/eclipses.json`

**Step 3: Commit**

```bash
git add specs/eclipse-description-fact-bundle.md specs/architecture.md specs/event-catalog-schema.md README.md
git commit -m "docs: define eclipse description review workflow"
```

### Task 2: Add Fact Bundle And Review Metadata Types

**Files:**
- Modify: `src/astrocal/models/candidate.py`
- Modify: `src/astrocal/models/catalog.py`
- Modify: `src/astrocal/models/reports.py`
- Modify: `src/astrocal/models/__init__.py`
- Test: `tests/test_repositories.py`

**Step 1: Write the failing tests**

Add serialization tests for:
- candidate metadata carrying `description_generation.facts`
- accepted record metadata carrying `description_provenance` and `description_review`
- report model carrying a Markdown review path/reference

**Step 2: Run the focused tests**

Run: `pytest tests/test_repositories.py -v`
Expected: FAIL because the new metadata/report fields are not yet modeled.

**Step 3: Write the minimal implementation**

- Keep the current top-level dataclasses.
- Add helper constants or thin typed helpers for:
  - `facts_schema_version`
  - `description_provenance`
  - `description_review`
- Extend report models only enough to support the new review artifact references.

**Step 4: Run the focused tests again**

Run: `pytest tests/test_repositories.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/astrocal/models/candidate.py src/astrocal/models/catalog.py src/astrocal/models/reports.py src/astrocal/models/__init__.py tests/test_repositories.py
git commit -m "feat: add eclipse description metadata models"
```

### Task 3: Extract Structured Eclipse Facts During Normalization

**Files:**
- Modify: `src/astrocal/adapters/astronomy/timeanddate_eclipses.py`
- Modify: `tests/test_timeanddate_eclipses.py`
- Test fixtures: `tests/fixtures/timeanddate/eclipse-detail-lunar-2026-03-03.html`
- Test fixtures: `tests/fixtures/timeanddate/eclipse-detail-solar-2026-08-12.html`
- Test fixtures: `tests/fixtures/timeanddate/eclipse-detail-lunar-2026-08-28.html`

**Step 1: Write the failing tests**

Add coverage that normalized eclipse candidates include:
- `metadata["description_generation"]["facts"]`
- full-duration timing for every eclipse
- special-phase timing only when totality or annularity exists
- visibility regions and path-country extraction where present
- stable `facts_hash` or equivalent provenance input

**Step 2: Run the focused tests**

Run: `pytest tests/test_timeanddate_eclipses.py -v`
Expected: FAIL because the adapter only emits generic description text today.

**Step 3: Write the minimal implementation**

- Keep HTML parsing in the adapter.
- Extract structured facts into a single bundle builder near `_parse_eclipse_html`.
- Attach the fact bundle to candidate metadata for both `full-duration` and `totality` variants.
- Keep the current fallback fields explicit when source pages omit optional visibility details.

**Step 4: Run the focused tests again**

Run: `pytest tests/test_timeanddate_eclipses.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/astrocal/adapters/astronomy/timeanddate_eclipses.py tests/test_timeanddate_eclipses.py tests/fixtures/timeanddate/eclipse-detail-lunar-2026-03-03.html tests/fixtures/timeanddate/eclipse-detail-solar-2026-08-12.html tests/fixtures/timeanddate/eclipse-detail-lunar-2026-08-28.html
git commit -m "feat: capture eclipse fact bundles during normalization"
```

### Task 4: Add Description Generation As A Separate Service

**Files:**
- Create: `src/astrocal/services/description_generation_service.py`
- Modify: `src/astrocal/services/normalize_service.py`
- Modify: `src/astrocal/services/__init__.py`
- Create: `tests/test_description_generation_service.py`
- Modify: `tests/test_timeanddate_eclipses.py`

**Step 1: Write the failing tests**

Add tests that:
- pass normalized eclipse candidates with fact bundles into a generator service
- verify the generator is called with structured facts, not raw HTML
- verify `title`, `summary`, `description`, and provenance fields are updated on returned candidates
- keep moon phases and seasons unchanged

**Step 2: Run the focused tests**

Run: `pytest tests/test_description_generation_service.py tests/test_timeanddate_eclipses.py -v`
Expected: FAIL because no generation boundary exists yet.

**Step 3: Write the minimal implementation**

- Introduce a small protocol for the generator client so tests can use a fake implementation.
- Make the service operate on normalized candidates after adapter parsing completes.
- Write generated prose back onto candidate records and store:
  - `description_provenance.generator`
  - `description_provenance.generated_at`
  - `description_provenance.prompt_version`
  - `description_provenance.facts_hash`

**Step 4: Run the focused tests again**

Run: `pytest tests/test_description_generation_service.py tests/test_timeanddate_eclipses.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/astrocal/services/description_generation_service.py src/astrocal/services/normalize_service.py src/astrocal/services/__init__.py tests/test_description_generation_service.py tests/test_timeanddate_eclipses.py
git commit -m "feat: add review-gated eclipse description generation"
```

### Task 5: Split Diffing From Reconciliation And Write Review Reports

**Files:**
- Create: `src/astrocal/services/review_report_service.py`
- Modify: `src/astrocal/services/reconcile_service.py`
- Modify: `src/astrocal/repositories/report_store.py`
- Modify: `src/astrocal/models/reports.py`
- Modify: `tests/test_reconcile_service.py`
- Create: `tests/test_review_report_service.py`

**Step 1: Write the failing tests**

Add coverage that:
- new/changed/suspected-removed eclipse candidates produce JSON diff data plus `review.<manifest>.md`
- eclipse reconciliation does not overwrite `data/catalog/accepted/.../eclipses.json` while review is pending
- moon phase reconciliation still writes accepted catalog changes as it does now
- changed-event review sections include accepted-vs-generated description comparisons

**Step 2: Run the focused tests**

Run: `pytest tests/test_reconcile_service.py tests/test_review_report_service.py -v`
Expected: FAIL because reconciliation currently auto-writes all source updates and report storage is JSON-only.

**Step 3: Write the minimal implementation**

- Extract a pure comparison helper from `reconcile_service.py`.
- Use that helper in:
  - normal auto-reconcile writes for non-eclipse sources
  - review-report generation for eclipse sources
- Add `ReportStore.write_text_report(...)`.
- Emit Markdown sections for:
  - new events
  - changed events with compact before/after comparison
  - suspected removals
  - fact bundle summary
  - generated description
  - source detail URL and raw snapshot reference

**Step 4: Run the focused tests again**

Run: `pytest tests/test_reconcile_service.py tests/test_review_report_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/astrocal/services/review_report_service.py src/astrocal/services/reconcile_service.py src/astrocal/repositories/report_store.py src/astrocal/models/reports.py tests/test_reconcile_service.py tests/test_review_report_service.py
git commit -m "feat: write markdown eclipse review reports"
```

### Task 6: Wire The CLI And Manual Acceptance Workflow

**Files:**
- Modify: `src/astrocal/cli.py`
- Modify: `src/astrocal/services/stub_service.py`
- Modify: `src/astrocal/services/run_service.py`
- Modify: `src/astrocal/services/build_ics_service.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_build_ics_service.py`

**Step 1: Write the failing tests**

Add coverage that:
- `astrocal reconcile --calendar astronomy-eclipses --year 2026` prints the Markdown review path
- `astrocal run --calendar astronomy-eclipses --year 2026` stops after writing review artifacts when eclipse changes need approval
- `astrocal build --calendar astronomy-eclipses` still publishes from accepted records only
- accepted manual edits that change title/summary/description are treated as a new revision with `description_review.resolution`

**Step 2: Run the focused tests**

Run: `pytest tests/test_cli.py tests/test_build_ics_service.py -v`
Expected: FAIL because the CLI has no review-gated eclipse workflow today.

**Step 3: Write the minimal implementation**

- Print the Markdown review report path from reconcile/run flows.
- In `run_service.py`, stop before build when eclipse review work is pending.
- Keep `build_ics_service.py` simple: it should continue to read only active accepted records.
- Update accepted revision handling so post-review manual description edits create a superseding accepted revision instead of mutating the active one in place.

**Step 4: Run the focused tests again**

Run: `pytest tests/test_cli.py tests/test_build_ics_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/astrocal/cli.py src/astrocal/services/stub_service.py src/astrocal/services/run_service.py src/astrocal/services/build_ics_service.py tests/test_cli.py tests/test_build_ics_service.py
git commit -m "refactor: gate run flow on pending eclipse review"
```

### Task 7: Verify The End-To-End Review Loop

**Files:**
- Modify: `tests/test_services.py`
- Modify: `tests/test_repositories.py`
- Modify: `README.md`

**Step 1: Write the failing end-to-end test**

Cover this sequence:
- normalize eclipse candidates with fact bundles
- generate descriptions
- write review report
- confirm accepted catalog is unchanged before review
- simulate manual acceptance by writing a new accepted revision with review metadata
- build `.ics` from the accepted catalog

**Step 2: Run the focused tests**

Run: `pytest tests/test_services.py tests/test_repositories.py -v`
Expected: FAIL until the full loop is wired together.

**Step 3: Write the minimal implementation/doc updates**

- Fill any small orchestration gaps revealed by the end-to-end test.
- Document the manual reviewer steps in `README.md`:
  - inspect `review.<manifest>.md`
  - update `data/catalog/accepted/astronomy/<year>/eclipses.json`
  - rerun `astrocal build --calendar astronomy-eclipses`

**Step 4: Run the targeted suite and then the full suite**

Run: `pytest tests/test_services.py tests/test_repositories.py -v`
Expected: PASS

Run: `pytest -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_services.py tests/test_repositories.py README.md
git commit -m "test: cover manual eclipse acceptance workflow"
```

## Notes For The Implementer

- Keep the first iteration eclipse-only. Do not generalize to moon phases or seasons until the review loop proves itself.
- Do not introduce a separate override table or a generic plugin framework in this pass.
- Prefer explicit metadata keys over nested abstractions. The event volume is small and clarity matters more than reuse here.
- Keep generated `.ics` files as build artifacts only. The review/edit surface is the accepted catalog plus the Markdown review artifact.
