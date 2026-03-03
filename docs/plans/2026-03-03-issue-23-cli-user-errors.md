# Issue 23 Graceful CLI User Errors Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make expected `astrocal` operator mistakes fail with short, actionable CLI errors and exit code `1`, while still allowing genuine programming failures to surface with a traceback.

**Architecture:** Introduce a dedicated `CliUserError` type for expected human-operator mistakes, then narrow the CLI boundary so `main()` catches only that type instead of every `ValueError`. Convert the current operator-facing validation paths to raise `CliUserError`, and wrap file/report parsing errors at the review workflow boundary so commands such as `build`, `run`, `reconcile`, `show-review`, `list-pending-reviews`, and `approve-review` all report the same `error: ...` shape without swallowing unexpected internal bugs.

**Tech Stack:** Python 3, argparse CLI, pathlib, JSON parsing, existing `astrocal` services, pytest.

---

## Implementation Decisions

- Use a dedicated exception for operator mistakes:
  - create `astrocal.errors.CliUserError`
  - keep it as a `ValueError` subclass so existing service-level tests and call sites do not need broad rewrites
- Narrow the CLI catch in [`src/astrocal/cli.py`](/Users/andrew/Documents/Git/GitHub/andrewdmontgomery/Calendars/src/astrocal/cli.py):
  - catch `CliUserError`
  - stop catching all `ValueError`
  - let uncategorized exceptions keep their traceback for debugging
- Convert known operator-facing validations to `CliUserError` instead of plain `ValueError`:
  - unknown manifest names
  - invalid review approval selections and stale review entries
  - missing or malformed persisted review bundles
  - missing or unreadable `--description-file` inputs
- Fail fast on corrupted persisted review artifacts.
  - `list-pending-reviews` should not silently skip malformed review bundles
  - the error should name the offending file path
- Keep `argparse` usage handling unchanged.
  - parser-level mistakes such as missing required flags already produce clean CLI output
- Use `@python-testing-patterns` to keep the CLI regression matrix table-driven instead of duplicating one test per command and failure mode.
- Use `@python-design-patterns` to keep exception translation near the CLI/review boundary instead of scattering generic `except Exception` blocks throughout the codebase.

## Expected Error Contract

- Unknown manifest:
  - `error: Unknown calendar manifest: astronomy-does-not-exist`
- Missing review bundle:
  - `error: Review bundle not found: /tmp/.../review.astronomy-eclipses.json`
- Invalid JSON review bundle:
  - `error: Review bundle is not valid JSON: /tmp/.../review.astronomy-eclipses.json`
- Malformed review bundle payload:
  - `error: Review bundle is malformed: missing 'calendar_name' in /tmp/.../review.astronomy-eclipses.json`
- Missing prose file:
  - `error: Description file not found: /tmp/.../edited-description.md`

## Recommended Commit Story

1. `test: pin cli operator error contract`
2. `feat: add explicit astrocal cli user errors`
3. `feat: normalize review bundle and file path errors`
4. `docs: note astrocal cli error policy`

### Task 1: Pin The CLI Error Contract

**Files:**
- Modify: `tests/test_cli.py`

**Step 1: Write the failing tests**

Add a small table-driven CLI regression block that covers:
- `build --calendar astronomy-does-not-exist`
- `reconcile --calendar astronomy-does-not-exist --year 2026`
- `run --calendar astronomy-does-not-exist --year 2026`
- `show-review --report <missing path>`
- `approve-review --report <missing path> --reviewer tester --occurrence-id <id>`
- `show-review --report <invalid json file>`
- `list-pending-reviews --report-dir <dir containing malformed bundle>`
- `approve-review --description-file <missing path>` with an otherwise valid bundle

For each case, assert:
- `exit_code == 1` when `main(...)` returns normally
- `captured.err` contains a short `error:` message
- `captured.err` does not contain `Traceback`

For the malformed-bundle case, create two fixtures:
- syntactically invalid JSON
- valid JSON missing required keys such as `calendar_name`

**Step 2: Run the focused tests**

Run: `pytest tests/test_cli.py -k "manifest or review or description_file" -v`
Expected: FAIL because `FileNotFoundError`, `JSONDecodeError`, and malformed review payload errors still escape the CLI boundary.

**Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: pin cli operator error contract"
```

### Task 2: Introduce An Explicit User-Error Boundary

**Files:**
- Create: `src/astrocal/errors.py`
- Modify: `src/astrocal/cli.py`
- Modify: `src/astrocal/manifests.py`
- Modify: `src/astrocal/services/review_approval_service.py`

**Step 1: Write the minimal implementation**

Add a dedicated exception and narrow the catch:

```python
class CliUserError(ValueError):
    """Expected operator-facing CLI error."""
```

Update `main()` to catch only `CliUserError`:

```python
try:
    return int(args.handler(args))
except CliUserError as exc:
    print(f"error: {exc}", file=sys.stderr)
    return 1
```

Change manifest lookup to raise `CliUserError`:

```python
if not manifest_path.exists():
    raise CliUserError(f"Unknown calendar manifest: {name}")
```

Convert the existing operator-facing approval validation paths in
`src/astrocal/services/review_approval_service.py` from `ValueError` to `CliUserError`, including:
- unsupported review resolution
- missing occurrence/group selectors
- no matching entries
- prose override misuse
- suspected-removal approval attempts
- missing candidate payload
- multi-source approval attempts
- stale review entries

Do not add a broad `except Exception` anywhere in this task.

**Step 2: Run the focused tests again**

Run: `pytest tests/test_cli.py -k "unknown_calendar_manifest or approve_review_command_reports_expected_errors_without_traceback" -v`
Expected: PASS for unknown-manifest cases and the existing approve-review validation case. Review bundle file-path cases should still fail until Task 3.

**Step 3: Commit**

```bash
git add src/astrocal/errors.py src/astrocal/cli.py src/astrocal/manifests.py src/astrocal/services/review_approval_service.py
git commit -m "feat: add explicit astrocal cli user errors"
```

### Task 3: Normalize Review Bundle And File Path Failures

**Files:**
- Modify: `src/astrocal/services/review_query_service.py`
- Modify: `src/astrocal/services/stub_service.py`
- Modify: `tests/test_cli.py`

**Step 1: Write the minimal implementation**

Wrap expected persisted-artifact failures in `src/astrocal/services/review_query_service.py`:
- `FileNotFoundError` -> `CliUserError("Review bundle not found: ...")`
- `json.JSONDecodeError` -> `CliUserError("Review bundle is not valid JSON: ...")`
- `KeyError`, `TypeError`, `ValueError` raised while materializing `ReviewBundle.from_dict(...)`
  -> `CliUserError("Review bundle is malformed: ... in ...")`

Keep the conversion localized to bundle loading so:
- `show-review`
- `list-pending-reviews`
- `approve-review`

all get the same behavior through shared code.

In `src/astrocal/services/stub_service.py`, add a tiny helper for `--description-file` reads:

```python
def _read_description_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise CliUserError(f"Description file not found: {path}") from exc
```

Also handle `IsADirectoryError`, `PermissionError`, and `UnicodeDecodeError` with similarly specific messages instead of letting raw OS exceptions leak.

When building malformed-bundle messages, include:
- the report path
- the missing field name when available

Examples:
- `Review bundle is malformed: missing 'calendar_name' in /tmp/...`
- `Review bundle is malformed: invalid year in /tmp/...`

**Step 2: Run the focused tests again**

Run: `pytest tests/test_cli.py -k "review or description_file" -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/astrocal/services/review_query_service.py src/astrocal/services/stub_service.py tests/test_cli.py
git commit -m "feat: normalize review bundle and file path errors"
```

### Task 4: Document The Policy And Run The Regression Sweep

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/2026-03-03-issue-23-cli-user-errors.md`

**Step 1: Add a short maintainer note**

Document the policy in `README.md` near Local Usage or Maintainer Notes:
- expected operator mistakes return `error: ...` and exit non-zero
- unexpected programming failures are still allowed to raise visibly for debugging
- persisted review bundle problems should be fixed at the artifact path named in the error

Keep this note short. Do not document every exact message string.

**Step 2: Run the regression sweep**

Run: `pytest tests/test_cli.py tests/test_review_approval_service.py tests/test_manifests.py -v`
Expected: PASS

Run: `pytest -v`
Expected: PASS

If a broader suite failure reveals another expected operator mistake, either:
- convert that path to `CliUserError` if it is a genuine human-operator error, or
- leave it as a traceback if it is an internal programming/configuration defect

**Step 3: Commit**

```bash
git add README.md docs/plans/2026-03-03-issue-23-cli-user-errors.md
git commit -m "docs: note astrocal cli error policy"
```
