# Issue 20 LLM-Operable Eclipse Review Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a safe, human-controlled eclipse review workflow that is easy for either a human or an LLM to run end-to-end without hand-editing `data/catalog/accepted/.../eclipses.json`.

**Architecture:** Keep the existing Markdown review report for humans, but add a structured review bundle that captures the candidate snapshot, accepted baseline, and allowed next actions for each reviewed eclipse occurrence. Expose the workflow through explicit CLI verbs such as `list-pending-reviews`, `show-review`, and `approve-review`, backed by a dedicated promotion service that is the only path allowed to write accepted eclipse revisions. Treat the persisted review bundle as the workflow boundary so either a human or an LLM can stop after generation, inspect the state later, approve changes explicitly, and resume the publish flow safely. Do not build the MCP transport layer in this PR; that is the immediate follow-on in Issue #22.

**Tech Stack:** Python 3, argparse CLI, dataclasses, existing `astrocal` repositories/services, pytest.

---

## Implementation Decisions

- Use a new machine-readable artifact beside the Markdown review report:
  - `data/catalog/reports/<run_timestamp>/review.<manifest>.json`
  - Keep `review.<manifest>.md` as the human review surface.
- Add explicit review-management commands:
  - `astrocal list-pending-reviews`
  - `astrocal show-review --report <path> --format markdown|json`
  - `astrocal approve-review --report <path> --reviewer <name> --occurrence-id <id>`
  - Support `--group-id <id>` for accept-as-is bulk approval only.
  - Support `--resolution accepted|prose-edited|facts-corrected`, `--note`, `--title`, `--summary`, and `--description-file`.
- Keep the workflow resumable.
  - `run` may stop after generating review artifacts.
  - A later command may inspect, approve, and continue from disk state.
- Do not let the CLI mutate accepted revisions in place.
  - Every approval writes a new active `AcceptedRecord` revision and supersedes the previous active revision.
- Persist enough review provenance to avoid repeated review churn.
  - Preserve the generated-candidate provenance already stored in `description_provenance`.
  - Add `generated_content_hash` to the accepted eclipse provenance so reconciliation can tell whether the reviewed candidate snapshot has changed.
- Put enough structure in the review bundle for LLM operation.
  - Each review entry should include candidate content, accepted baseline content, fact bundle, hashes, source references, and allowed actions.
- Treat accepted human prose as stable if the reviewed candidate snapshot is unchanged.
  - If facts and generated content are unchanged since review, reconciliation should not open another review just because accepted prose differs from the generated candidate.
- Keep `.ics` generation unchanged.
  - `build` continues to publish only active accepted catalog records.
- Defer the local MCP transport layer.
  - Issue #22 should wrap the settled service/CLI surface instead of co-evolving with it in this PR.

## Recommended Commit Story

1. `docs: define llm-operable eclipse review workflow`
2. `feat: emit structured eclipse review bundles`
3. `feat: add review inspection commands`
4. `feat: add eclipse review approval service`
5. `feat: preserve approved eclipse edits across reconcile`
6. `test: cover minimal review cli workflow end to end`

### Task 1: Codify The Approval Contract

**Files:**
- Create: `specs/eclipse-review-approval-workflow.md`
- Modify: `README.md`
- Modify: `specs/event-catalog-schema.md`
- Modify: `specs/eclipse-description-fact-bundle.md`
- Modify: `specs/architecture.md`

**Step 1: Write the contract updates**

- Define the v1 workflow:
  - `reconcile` writes both `review.<manifest>.md` and `review.<manifest>.json`
  - reviewer or LLM inspects the persisted review bundle
  - reviewer or LLM runs `approve-review`
  - `build` still reads only accepted records
- Document the structured review bundle contents:
  - manifest name
  - year
  - run timestamp
  - occurrence/group ids
  - candidate snapshot
  - accepted baseline snapshot
  - candidate `content_hash`
  - candidate description provenance, including `facts_hash` and `prompt_version`
  - source references and allowed actions
- Document the inspection commands:
  - `list-pending-reviews`
  - `show-review`
- Document the approval command inputs and the meaning of:
  - `resolution=accepted`
  - `resolution=prose-edited`
  - `resolution=facts-corrected`
- Document the new provenance rule:
  - accepted eclipse records store `description_provenance.generated_content_hash`
  - accepted eclipse records never require direct JSON editing in the normal path
- Document the orchestration rule:
  - any future orchestration layer or MCP server must reuse the same persisted review bundle and approval service
- Document the follow-on boundary:
  - the local MCP server is tracked separately in #22

**Step 2: Review the wording for consistency**

Check that the docs all point to:
- `data/catalog/reports/<run_timestamp>/review.<manifest>.md`
- `data/catalog/reports/<run_timestamp>/review.<manifest>.json`
- `data/catalog/accepted/astronomy/<year>/eclipses.json`

**Step 3: Commit**

```bash
git add specs/eclipse-review-approval-workflow.md README.md specs/event-catalog-schema.md specs/eclipse-description-fact-bundle.md specs/architecture.md
git commit -m "docs: define llm-operable eclipse review workflow"
```

### Task 2: Add Typed Review Bundle And Inspection Metadata

**Files:**
- Create: `src/astrocal/models/review.py`
- Modify: `src/astrocal/models/catalog.py`
- Modify: `src/astrocal/models/reports.py`
- Modify: `src/astrocal/models/__init__.py`
- Modify: `tests/test_repositories.py`

**Step 1: Write the failing tests**

Add tests that cover:
- serializing and loading a structured review bundle entry with:
  - `occurrence_id`
  - `group_id`
  - candidate snapshot
  - accepted baseline snapshot or `null`
  - `candidate_content_hash`
  - `generated_content_hash`
  - allowed actions
- accepted eclipse metadata round-tripping with:
  - `description_provenance.generated_content_hash`
  - `description_review.edited`
  - `description_review.resolution`
- `ReconciliationReport` carrying both:
  - `review_report_path`
  - `review_bundle_path`

**Step 2: Run the focused tests**

Run: `pytest tests/test_repositories.py -v`
Expected: FAIL because the review bundle model and extra report field do not exist.

**Step 3: Write the minimal implementation**

- Add lightweight review dataclasses, for example:
  - `ReviewBundle`
  - `ReviewBundleEntry`
- Give `ReviewBundleEntry` fields that an LLM can consume directly without re-deriving state from unrelated files.
- Export the new types through `src/astrocal/models/__init__.py`.
- Extend `ReconciliationReport` with `review_bundle_path`.
- Keep catalog metadata as plain dictionaries, but define constants or thin helpers for:
  - `generated_content_hash`
  - allowed review resolutions

**Step 4: Run the focused tests again**

Run: `pytest tests/test_repositories.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/astrocal/models/review.py src/astrocal/models/catalog.py src/astrocal/models/reports.py src/astrocal/models/__init__.py tests/test_repositories.py
git commit -m "feat: add typed eclipse review bundle models"
```

### Task 3: Emit Structured Review Bundles During Reconcile

**Files:**
- Modify: `src/astrocal/services/reconcile_service.py`
- Modify: `src/astrocal/services/review_report_service.py`
- Modify: `src/astrocal/repositories/report_store.py`
- Modify: `tests/test_reconcile_service.py`
- Modify: `tests/test_review_report_service.py`

**Step 1: Write the failing tests**

Add coverage that:
- eclipse reconcile writes `review.<manifest>.json` beside `review.<manifest>.md`
- the JSON bundle contains one entry per new or changed reviewed eclipse occurrence
- each bundle entry includes the active accepted baseline revision when one exists
- suspected removals appear in the structured artifact with the last active accepted snapshot
- `ReconciliationReport.review_bundle_path` is populated
- pending review entries expose enough data for `show-review` without reopening accepted catalog files

**Step 2: Run the focused tests**

Run: `pytest tests/test_reconcile_service.py tests/test_review_report_service.py -v`
Expected: FAIL because reconcile currently emits only the Markdown review artifact.

**Step 3: Write the minimal implementation**

- Add a small helper in `reconcile_service.py` that converts eclipse review data into a `ReviewBundle`.
- Write the JSON bundle through `ReportStore.write_json_report(...)`.
- Keep the Markdown renderer human-focused.
- Do not put approval logic into the report writer; the artifact should be data-only.

**Step 4: Run the focused tests again**

Run: `pytest tests/test_reconcile_service.py tests/test_review_report_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/astrocal/services/reconcile_service.py src/astrocal/services/review_report_service.py src/astrocal/repositories/report_store.py tests/test_reconcile_service.py tests/test_review_report_service.py
git commit -m "feat: emit structured eclipse review bundles"
```

### Task 4: Add Review Inspection Commands

**Files:**
- Modify: `src/astrocal/cli.py`
- Modify: `src/astrocal/services/stub_service.py`
- Create: `src/astrocal/services/review_query_service.py`
- Modify: `tests/test_cli.py`

**Step 1: Write the failing tests**

Add CLI coverage that:
- `astrocal list-pending-reviews` prints pending review bundle paths and manifest/year context
- `astrocal show-review --report <path> --format json` prints the structured bundle entry
- `astrocal show-review --report <path> --format markdown` prints a readable summary of the same review state
- missing or malformed review bundle paths fail clearly

**Step 2: Run the focused tests**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL because the CLI has no review inspection commands.

**Step 3: Write the minimal implementation**

- Add a small query service that:
  - discovers pending review bundles under `data/catalog/reports`
  - loads a chosen bundle
  - renders a concise inspection summary
- Keep these commands read-only.
- Make the output deterministic and compact so an LLM can consume it reliably.

**Step 4: Run the focused tests again**

Run: `pytest tests/test_cli.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/astrocal/cli.py src/astrocal/services/stub_service.py src/astrocal/services/review_query_service.py tests/test_cli.py
git commit -m "feat: add review inspection commands"
```

### Task 5: Implement The Approval Promotion Service

**Files:**
- Create: `src/astrocal/services/review_approval_service.py`
- Modify: `src/astrocal/repositories/catalog_store.py`
- Modify: `src/astrocal/models/catalog.py`
- Create: `tests/test_review_approval_service.py`

**Step 1: Write the failing tests**

Add service tests for:
- approving a new reviewed eclipse occurrence creates revision `1`
- approving a changed reviewed eclipse occurrence supersedes the current active revision and appends the new active revision
- accepting generated prose as-is copies the candidate title, summary, description, and provenance
- approving edited prose applies the override fields and records:
  - `description_review.edited = true`
  - `description_review.resolution = "prose-edited"`
  - `description_review.reviewer`
  - `description_review.note`
- approving corrected facts uses `resolution = "facts-corrected"`
- top-level `AcceptedRecord.content_hash` is recomputed from the final accepted payload after edits
- the service rejects stale approvals if the current accepted active revision no longer matches the review bundle baseline

**Step 2: Run the focused tests**

Run: `pytest tests/test_review_approval_service.py -v`
Expected: FAIL because no approval service exists.

**Step 3: Write the minimal implementation**

- Add a single service entry point, for example:

```python
approve_review_entry(
    review_bundle_path: Path,
    reviewer: str,
    occurrence_ids: list[str],
    group_ids: list[str],
    resolution: str,
    note: str | None,
    title: str | None,
    summary: str | None,
    description: str | None,
) -> list[AcceptedRecord]
```

- Keep the promotion flow strict:
  - load the review bundle entry
  - validate that the current accepted baseline still matches
  - create a new accepted payload from the candidate snapshot
  - apply optional prose overrides
  - attach `description_review`
  - preserve `description_provenance` and set `generated_content_hash`
  - supersede the previous active revision if present
  - save the updated catalog file

**Step 4: Run the focused tests again**

Run: `pytest tests/test_review_approval_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/astrocal/services/review_approval_service.py src/astrocal/repositories/catalog_store.py src/astrocal/models/catalog.py tests/test_review_approval_service.py
git commit -m "feat: add eclipse review approval service"
```

### Task 6: Keep Approved Human Edits Stable Across Reconcile

**Files:**
- Modify: `src/astrocal/services/reconcile_service.py`
- Modify: `tests/test_reconcile_service.py`
- Modify: `tests/test_services.py`

**Step 1: Write the failing tests**

Add coverage that:
- a previously approved `prose-edited` eclipse record is treated as unchanged when:
  - the incoming candidate has the same `content_hash` as the reviewed generated candidate
  - the accepted record differs only in human-edited title, summary, or description
- a new review is still required when:
  - the candidate facts hash changes
  - the generated content hash changes
  - non-prose fields such as timing or detail URL change

**Step 2: Run the focused tests**

Run: `pytest tests/test_reconcile_service.py tests/test_services.py -v`
Expected: FAIL because reconcile currently compares accepted and candidate `content_hash` directly.

**Step 3: Write the minimal implementation**

- Add a helper in `reconcile_service.py` that recognizes an approved eclipse review state.
- Treat a reviewed human prose edit as unchanged only when:
  - `description_review.status == "accepted"`
  - accepted `description_provenance.generated_content_hash == candidate.content_hash`
  - the candidate provenance facts hash still matches the accepted provenance facts hash
  - non-generated fields still match
- Keep this behavior scoped to eclipse records with review metadata; do not change moon phase or season reconciliation.

**Step 4: Run the focused tests again**

Run: `pytest tests/test_reconcile_service.py tests/test_services.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/astrocal/services/reconcile_service.py tests/test_reconcile_service.py tests/test_services.py
git commit -m "feat: preserve approved eclipse edits across reconcile"
```

### Task 7: Wire The Minimal Human CLI Workflow

**Files:**
- Modify: `src/astrocal/cli.py`
- Modify: `src/astrocal/services/stub_service.py`
- Modify: `src/astrocal/services/run_service.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_services.py`
- Modify: `README.md`

**Step 1: Write the failing tests**

Add CLI and integration coverage that:
- `astrocal run --calendar astronomy-eclipses --year 2026` prints both review artifact paths and exits cleanly when review is pending
- `astrocal approve-review --report <path> --reviewer tester --occurrence-id <id> --resolution accepted` writes a new accepted revision
- `astrocal approve-review ... --title ... --summary ... --description-file ... --resolution prose-edited` records the edited review metadata correctly
- `astrocal approve-review --group-id <id>` approves multiple occurrences only when no override fields are supplied
- `astrocal show-review` can be used immediately after `run` to inspect the generated review state
- the command exits non-zero with a clear error when the review bundle is stale or the requested occurrence is missing
- the `run` and `reconcile` flows print both the Markdown review path and the structured review bundle path when review is pending

**Step 2: Run the focused tests**

Run: `pytest tests/test_cli.py tests/test_services.py -v`
Expected: FAIL because the CLI lacks the full review-management surface and the report output only mentions Markdown review paths.

**Step 3: Write the minimal implementation**

- Add a new `approve-review` subparser in `src/astrocal/cli.py`.
- Add `list-pending-reviews` and `show-review` subparsers in `src/astrocal/cli.py`.
- Keep the mutation surface explicit and non-interactive for v1.
- Reuse the new approval service from `stub_service.py` so CLI tests stay focused on argument handling and output.
- Keep this PR at the service plus minimal human CLI boundary. Do not add MCP server wiring here.
- Print a short success line that names:
  - approved occurrence count
  - accepted catalog path
  - new revision numbers or count

**Step 4: Run the focused tests again**

Run: `pytest tests/test_cli.py tests/test_services.py -v`
Expected: PASS

**Step 5: Run the full regression suite**

Run: `pytest -q`
Expected: PASS

**Step 6: Commit**

```bash
git add src/astrocal/cli.py src/astrocal/services/stub_service.py src/astrocal/services/run_service.py tests/test_cli.py tests/test_services.py README.md
git commit -m "test: cover minimal review cli workflow end to end"
```

## Notes For Execution

- Prefer approving one occurrence first before adding group-level bulk approval.
- Keep manual prose override support limited to `title`, `summary`, and `description` in v1.
- Reject direct accepted-catalog mutation anywhere outside the approval service.
- Do not change `.ics` generation rules; this issue is about safer accepted-catalog promotion only.
- Treat the persisted review bundle as the pause/resume boundary for both humans and LLM-driven operation.
- Treat Issue #22 as the immediate next step once this service/CLI surface is stable.
