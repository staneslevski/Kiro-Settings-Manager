# ksm list Workspace Scope Bugfix Design

## Overview

`ksm list` shows local bundles from all workspaces because `ManifestEntry` lacks a `workspace_path` field. The fix adds workspace tracking to manifest entries, filters local bundles by the current workspace in `run_ls()`, provides an `--all` flag for cross-workspace listing, and backfills legacy entries missing `workspace_path`.

## Glossary

- **Bug_Condition (C)**: A `ksm list` invocation (with or without `--scope local`) in a workspace where the manifest contains local entries belonging to other workspaces — those entries are incorrectly shown.
- **Property (P)**: Default `ksm list` output SHALL only include global bundles and local bundles whose `workspace_path` matches the resolved current working directory.
- **Preservation**: Global bundle listing, JSON output structure, verbose file listing, scope grouping, column alignment, and relative timestamps must remain unchanged.
- **ManifestEntry**: Dataclass in `src/ksm/manifest.py` representing a single installed bundle record.
- **install_bundle()**: Function in `src/ksm/installer.py` that copies bundle files and creates/updates manifest entries.
- **run_ls()**: Function in `src/ksm/commands/ls.py` that reads the manifest and prints installed bundles.
- **workspace_path**: New optional field on `ManifestEntry` — the resolved absolute path of the workspace where a local bundle was installed.

## Bug Details

### Bug Condition

The bug manifests when a user runs `ksm list` (or `ksm list --scope local`) in any workspace. The manifest (`~/.kiro/ksm/manifest.json`) is global and contains local entries from all workspaces, but `ManifestEntry` has no `workspace_path` field, so `run_ls()` cannot distinguish which local entries belong to the current workspace.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type { command: str, cwd: Path, manifest: Manifest, all_flag: bool }
  OUTPUT: boolean

  RETURN input.command IN ["list", "ls"]
         AND input.all_flag == false
         AND EXISTS entry IN input.manifest.entries WHERE
             entry.scope == "local"
             AND (entry.workspace_path IS NULL
                  OR resolve(entry.workspace_path) != resolve(input.cwd))
END FUNCTION
```

### Examples

- User installs bundle "python_dev" locally in `/home/user/project-a`. Then runs `ksm list` in `/home/user/project-b`. **Actual**: "python_dev" appears in the local section. **Expected**: "python_dev" should not appear.
- User installs "aws" locally in `/home/user/project-a` and "git" locally in `/home/user/project-b`. Runs `ksm list` in project-b. **Actual**: Both "aws" and "git" appear. **Expected**: Only "git" appears.
- User runs `ksm list --scope local` in project-a. **Actual**: Local bundles from all workspaces shown. **Expected**: Only project-a's local bundles shown.
- User runs `ksm list --all` in any workspace. **Expected**: All local bundles from all workspaces shown, with workspace path visible.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Global bundle listing must continue to display all global bundles regardless of workspace.
- `ksm list --scope global` must continue to show only global bundles, unaffected by workspace filtering.
- JSON output must continue to produce valid JSON with all existing fields (`bundle_name`, `scope`, `source_registry`, `installed_files`, `installed_at`, `updated_at`).
- Verbose mode (`-v`) must continue to show installed file paths under each bundle.
- Text output must continue to group bundles by scope with bold headers, column alignment, and relative timestamps.
- Global bundle installation must continue to create entries without `workspace_path`.

**Scope:**
All inputs that do NOT involve local-scope workspace filtering should be completely unaffected by this fix. This includes:
- Global bundle operations (install, list, remove, sync)
- `--scope global` filtering
- JSON and text formatting logic (aside from the new `workspace_path` field in JSON)
- Verbose file listing
- Relative timestamp formatting

## Hypothesized Root Cause

Based on the bug description, the most likely issues are:

1. **Missing workspace_path field on ManifestEntry**: The `ManifestEntry` dataclass in `src/ksm/manifest.py` has no `workspace_path` field, so there is no data to filter on.

2. **install_bundle() does not record workspace**: The `_update_manifest()` helper in `src/ksm/installer.py` creates entries without any workspace association, even when `scope="local"`.

3. **run_ls() has no workspace filter**: The `run_ls()` function in `src/ksm/commands/ls.py` applies only a `scope` filter but never checks whether a local entry belongs to the current workspace.

4. **No --all flag exists**: The CLI parser in `src/ksm/cli.py` does not define an `--all` argument for the `list`/`ls` subcommands, so users have no way to explicitly request cross-workspace output.

5. **Legacy entries lack workspace_path**: Existing manifest entries created before this fix will have `workspace_path=None`, requiring a backfill mechanism.

## Correctness Properties

Property 1: Bug Condition - Local bundles filtered by workspace

_For any_ `ksm list` invocation (without `--all`) in workspace W where the manifest contains local entries with `workspace_path != resolve(W)` or `workspace_path is None` (and not backfillable to W), the fixed `run_ls()` SHALL exclude those entries from the output, showing only local entries whose `workspace_path` matches `resolve(W)`.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - Global and formatting behavior unchanged

_For any_ `ksm list` invocation, the fixed code SHALL produce the same output for global bundles as the original code, preserving scope grouping, column alignment, relative timestamps, verbose file listing, and JSON structure (with the addition of `workspace_path` for local entries in JSON output).

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `src/ksm/manifest.py`

**Changes**:
1. **Add workspace_path to ManifestEntry**: Add `workspace_path: str | None = None` optional field to the dataclass.
2. **Update _entry_to_dict()**: Include `workspace_path` in serialized output when not None.
3. **Update _dict_to_entry()**: Read `workspace_path` from dict with `.get("workspace_path")` default None.

**File**: `src/ksm/installer.py`

**Function**: `install_bundle()` / `_update_manifest()`

**Changes**:
4. **Accept workspace_path parameter**: Add `workspace_path: str | None = None` to `_update_manifest()` and pass it through from `install_bundle()`.
5. **Record workspace_path for local scope**: When `scope="local"`, resolve and store the workspace path (parent of `target_dir`). When `scope="global"`, leave it None.
6. **Set workspace_path on new and existing entries**: Both new entry creation and existing entry updates should set `workspace_path`.

**File**: `src/ksm/commands/ls.py`

**Function**: `run_ls()`

**Changes**:
7. **Filter local entries by workspace**: When `--all` is not set, filter local entries to only those whose `workspace_path` matches `os.path.realpath(os.getcwd())`. Global entries pass through unfiltered.
8. **Accept workspace_path parameter**: Add a `workspace_path` parameter (defaulting to `Path.cwd()`) so the function is testable without depending on the real cwd.
9. **Update _entry_to_dict()**: Include `workspace_path` in JSON serialization.

**File**: `src/ksm/cli.py`

**Changes**:
10. **Add --all flag**: Add `--all` argument to both `list` and `ls` subparsers via `_add_list_args()`.
11. **Pass workspace context to run_ls()**: Pass the resolved current workspace path when dispatching to `run_ls()`.

**File**: `src/ksm/manifest.py` (or new utility)

**Changes**:
12. **Backfill legacy entries**: Add a function that scans manifest entries with `scope="local"` and `workspace_path is None`, checks if their `installed_files` exist under the current workspace's `.kiro/` directory, and if so sets `workspace_path` to the resolved current workspace path and persists the manifest.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Create a manifest with local entries from multiple workspaces and call `run_ls()` from a specific workspace. On unfixed code, all local entries will appear regardless of workspace.

**Test Cases**:
1. **Cross-workspace local entries shown**: Create manifest with local entries for workspace-a and workspace-b, call `run_ls()` from workspace-a — unfixed code shows both (will fail on unfixed code)
2. **Scope local filter ignores workspace**: Call `run_ls()` with `--scope local` from workspace-a — unfixed code shows all local entries (will fail on unfixed code)
3. **No workspace_path on ManifestEntry**: Verify that `ManifestEntry` has no `workspace_path` field, confirming root cause (will fail on unfixed code)

**Expected Counterexamples**:
- `run_ls()` returns local entries from workspace-b when called from workspace-a
- Possible causes: no `workspace_path` field, no filtering logic in `run_ls()`

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := run_ls_fixed(input)
  ASSERT all local entries in result have workspace_path == resolve(input.cwd)
  ASSERT no local entries from other workspaces appear in result
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT run_ls_original(input) == run_ls_fixed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for global-only manifests, `--scope global` filtering, JSON output, and verbose mode, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Global bundle listing preservation**: Verify global bundles display identically before and after fix
2. **Scope global filter preservation**: Verify `--scope global` output is unchanged
3. **JSON output preservation**: Verify JSON structure remains valid with existing fields
4. **Verbose mode preservation**: Verify `-v` file listing continues to work
5. **Text formatting preservation**: Verify scope grouping, column alignment, and relative timestamps are unchanged

### Unit Tests

- Test `ManifestEntry` serialization/deserialization with `workspace_path`
- Test `_update_manifest()` records `workspace_path` for local scope and omits it for global
- Test `run_ls()` filters local entries by workspace when `--all` is not set
- Test `run_ls()` shows all local entries when `--all` is set
- Test `run_ls()` with `--scope local` only shows current workspace's local entries
- Test backfill function correctly identifies and updates legacy entries
- Test backfill function leaves unmatched legacy entries unchanged
- Test `--all` flag is accepted by the CLI parser

### Property-Based Tests

- Generate random manifests with mixed scopes and workspace paths, verify `run_ls()` output only contains local entries matching the current workspace (or all entries when `--all`)
- Generate random global-only manifests, verify output is identical before and after fix
- Generate random manifests and verify JSON output always includes all required fields and is valid JSON

### Integration Tests

- Test full `ksm list` flow with multi-workspace manifest, verifying workspace filtering end-to-end
- Test `ksm list --all` shows cross-workspace bundles
- Test `ksm list --scope local` respects workspace filtering
- Test legacy backfill runs transparently during `ksm list` and persists updated manifest
