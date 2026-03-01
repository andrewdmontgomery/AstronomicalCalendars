---
name: reconcile-event-catalog
description: Reconcile newly normalized event candidates with the accepted event catalog in a git-backed repository. Use when Codex needs to add new dates without modifying accepted existing dates, verify existing dates against fresh source data, stage manual corrections, create correction pull requests in automation, or stop and report source validation failures.
---

# Reconcile Event Catalog

Treat freshly normalized source output as candidate data. Compare those candidates to the
accepted catalog before any `.ics` generation.

## Workflow

1. Read candidate occurrence data from source modules.
2. Read the accepted catalog defined in
   [`specs/event-catalog-schema.md`](../../specs/event-catalog-schema.md).
3. Stop immediately if any required candidate has `source_validation.status = failed`.
4. Match candidates to accepted records by `occurrence_id`.
5. Add new occurrences automatically.
6. Mark unchanged occurrences as verified.
7. Detect changed existing occurrences by comparing `content_hash`.
8. Apply correction handling according to the manifest and run context.
9. Write updated accepted catalog records plus a reconciliation report.

## Correction Rules

- Never silently modify accepted existing dates.
- In manual git-backed runs, apply approved corrections to the working tree and stage them.
- In automation runs, prepare correction changes and open a pull request.
- If a source validation failure occurs in automation, open an issue and stop.
- Do not auto-delete missing events. Mark them as `suspected-removed` until reviewed.

## Report Rules

Every reconciliation run should produce a report that includes:

- source validation failures
- new dates added
- existing dates verified unchanged
- corrections staged for review
- corrections opened as a pull request
- suspected removals
- unresolved conflicts

## Output Expectations

Suggested outputs:

- accepted catalog data under `data/catalog/accepted/...`
- reconciliation reports under `data/catalog/reports/...`

The ICS builder should read only accepted active records from the catalog.
