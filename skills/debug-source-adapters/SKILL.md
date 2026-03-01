---
name: debug-source-adapters
description: Debug validation, fetch, parsing, normalization, and reconciliation failures at the external-source boundary for astronomy and future source adapters. Use when Codex needs to inspect validation reports, diagnostics under data/diagnostics, raw payload snapshots, normalized candidate output, or reconciliation reports to classify why a source-backed run failed.
---

# Debug Source Adapters

Debug the source boundary in a fixed order. Treat [`specs/`](../../specs) as the source of
truth for contracts and expected artifacts.

## Workflow

1. Read [`specs/source-policy.md`](../../specs/source-policy.md).
2. Read the relevant JSON report under [`data/catalog/reports/`](../../data/catalog/reports).
3. Read the source summary under `data/diagnostics/<source-type>/<year>/<source-name>/`:
   - `validate-summary.json`
   - `fetch-summary.json` or `fetch-failure.json`
   - `normalize-summary.json` or `normalize-failure.json`
4. If fetch succeeded, inspect the raw snapshot under [`data/raw/`](../../data/raw).
5. If normalization succeeded, inspect the normalized candidates under
   [`data/normalized/`](../../data/normalized).
6. If reconciliation ran, inspect the reconciliation report and accepted catalog output.
7. Classify the failure before proposing a fix.

## Failure Classes

Use one primary classification:

- `network-or-reachability`
- `source-shape-drift`
- `detail-url-derivation`
- `fetch-failure`
- `parsing-or-extraction`
- `normalization-failure`
- `reconciliation-mismatch`

## What To Check

### Validation

- `status`
- `reason`
- `checks`
- `canary_ok`
- `detail_url_ok`
- `source_url`

If validation failed, stop there unless the raw payload was already saved by a previous run.

### Fetch

- whether `fetch-summary.json` exists
- `raw_ref`
- source adapter and source URL
- any `fetch-failure.json` reason

### Normalize

- `candidate_count`
- `event_types`
- `variants`
- `titles_sample`
- `metadata_keys`
- `extraction_summary`
- any `normalize-failure.json` reason

Use `extraction_summary` to quickly sanity-check what the parser claims it found before
opening the full candidate file.

### Reconciliation

- whether the candidate set got far enough to reconcile
- whether the accepted catalog changed unexpectedly
- whether a source failure should have stopped reconciliation earlier

## Output Expectations

When reporting a debugging result:

1. Name the failure class.
2. Cite the exact artifact(s) inspected.
3. State the concrete failing field, page marker, or parser assumption.
4. Identify the smallest likely fix location.

Keep the diagnosis artifact-driven. Do not speculate about upstream payload shape when a
saved raw snapshot or diagnostic artifact exists.
