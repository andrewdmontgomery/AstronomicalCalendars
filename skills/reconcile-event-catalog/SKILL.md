---
name: reconcile-event-catalog
description: Reconcile newly normalized event candidates with the accepted event catalog in a git-backed repository. Use when Codex needs to add new dates without modifying accepted existing dates, verify existing dates against fresh source data, stage manual corrections, create correction pull requests in automation, or stop and report source validation failures.
---

# Reconcile Event Catalog

Treat freshly normalized source output as candidate data. Compare those candidates to the
accepted catalog before any `.ics` generation. Treat `specs/` and manifests as the source
of truth for reconciliation behavior.

## Workflow

1. Read candidate occurrence data from source modules.
2. Read the accepted catalog defined in
   [`specs/event-catalog-schema.md`](../../specs/event-catalog-schema.md).
3. Read the active manifest in
   [`config/calendars`](../../config/calendars).
4. Stop immediately if any required candidate has `source_validation.status = failed`.
5. Match candidates to accepted records by `occurrence_id`.
6. Apply the manifest's reconciliation and correction policy.
7. Write updated accepted catalog records plus a reconciliation report.

## Output Expectations

Suggested outputs:

- accepted catalog data under `data/catalog/accepted/...`
- reconciliation reports under `data/catalog/reports/...`

The ICS builder should read only accepted active records from the catalog.
