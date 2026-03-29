# ksm list Workspace Scope Bugfix Design

## Overview

`ksm list` shows local bundles from all workspaces because `ManifestEntry` historically lacked a `workspace_path` field. The fix adds workspace tracking to manifest entries, filters local bundles by the current workspace in `run_ls()`, provides an `--all` flag for cross-workspace listing with workspace path annotations, and backfills legacy entries missing `workspace_path`.

## Glossary

- **Bug_Condition (C)**: A `ksm list` invocation (with or without `--scope local`) in a workspace where the manifest contains local entries belonging to other workspaces — those entries are incorrectly shown.
- **Property (P)**: Default `ksm list` output SHALL only include global bundles and local bundles whose `workspace_path` matches the resolved current working directory. `ksm list --all` SHALL show all bundles with workspace path annotations on local entries.
- **Preservation**: Global bundle listing, JSON output structure, verbose file listing, scope grouping, column alignment, and relative timestamps must remain unchanged.
- **ManifestEntry**: Dataclass in `src/ksm/manifest.py` representing a single installed bundle record.
- **install_bundle()**: Function in `src/ksm/installer.py` that copies bundle files and creates/updates manifest entries.
- **run_ls()**: Function in `src/ksm/commands/ls.py` that reads the manifest and prints installed bundles.
- **workspace_path**: Optional field on `ManifestEntry` — the resolved absolute path of the workspace where a local bundle was installed.
- **_format_grouped()**: Function in `src/ksm/commands/ls.py` that renders text output grouped by scope with column alignment.

## Bug Details

### Bug Condition

The bug manifests when a user runs `ksm list` (or `ksm list --scope local`) in any workspace. The manifest (`~/.kiro/ksm/manifest.json`) is global and contains local entries from all workspaces, but `ManifestEntry` historically had no `workspace_path` field, so `run_ls()` could not distinguish which local entries belong to the current workspace.

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
- User runs `ksm list --all` in any workspace. **Expected**: All local bundles from all workspaces shown, with workspace path visible next to each local entry.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Global bundle listing must continue to display all global bundles regardless of workspace.
- `ksm list --scope global` must continue to show only global bundles, unaffected by workspace filtering.
- JSON output must continue to produce valid JSON with all existing fields (`bundle_name`, `scope`, `source_registry`, `installed_files`, `installed_at`, `updated_at`), now additionally including `workspace_path` for local entries.
- Verbose mode (`-v`) must continue to show installed file paths under each bundle.
- Text output must continue to group bundles by scope with bold headers, column alignment, and relative timestamps.
- Global bundle installation must continue to create entries without `workspace_path`.

**Scope:**
All inputs that do NOT involve local-scope workspace filtering should be completely unaffected by this fix. This includes:
- Global bundle operations (install, list, remove, sync)
- `--scope global` filtering
- JSON and text formatting logic (aside from the new `workspace_path` field in JSON and workspace annotations in `--all` text output)
- Verbose file listing
- Relative timestamp formatting

## Hypothesized Root Cause

Based on the bug description, the most likely issues are:

1. **Missing workspace_path field on ManifestEntry**: The `ManifestEntry` dataclass in `src/ksm/manifest.py` historically had no `workspace_path` field, so there was no data to filter on.

2. **install_bundle() did not record workspace**: The `_update_manifest()` helper in `src/ksm/installer.py` created entries without any workspace association, even when `scope="local"`.

3. **run_ls() had no workspace filter**: The `run_ls()` function in `src/ksm/commands/ls.py` applied only a `scope` filter but never checked whether a local entry belonged to the current workspace.

4. **No --all flag existed**: The CLI parser in `src/ksm/cli.py` did not define an `--all` argument for the `list`/`ls` subcommands, so users had no way to explicitly request cross-workspace output.

5. **Legacy entries lack workspace_path**: Existing manifest entries created before this fix have `workspace_path=None`, requiring a backfill mechanism.

6. **No workspace path display in text output**: The `_format_grouped()` function in `src/ksm/commands/ls.py` has no mechanism to display workspace path information for local entries, which is needed for `--all` output to be useful (requirement 2.4).

## Correctness Properties

Property 1: Bug Condition - Local bundles filtered by workspace

_For any_ `ksm list` invocation (without `--all`) in workspace W where the manifest contains local entries with `workspace_path != resolve(W)` or `workspace_path is None` (and not backfillable to W), the fixed `run_ls()` SHALL exclude those entries from the output, showing only local entries whose `workspace_path` matches `resolve(W)`.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - Global and formatting behavior unchanged

_For any_ `ksm list` invocation, the fixed code SHALL produce the same output for global bundles as the original code, preserving scope grouping, column alignment, relative timestamps, verbose file listing, and JSON structure (with the addition of `workspace_path` for local entries in JSON output).

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

Property 3: Workspace Path Visibility - `--all` output shows workspace paths

_For any_ `ksm list --all` invocation, the fixed `run_ls()` SHALL display all global bundles and all local bundles from every workspace. Each local entry in text output SHALL include the workspace path annotation (e.g., the resolved directory path) so the user can identify which workspace each local bundle belongs to. In JSON output, the `workspace_path` field SHALL be present for local entries.

**Validates: Requirements 2.4**

Property 4: Legacy Entry Handling - Backfill and exclusion

_For any_ `ksm` command invocation in workspace W, the system SHALL check for legacy local entries (scope="local", workspace_path=None) whose installed_files match files in W's `.kiro/` directory, backfill their `workspace_path` to resolve(W), and persist the manifest. Legacy entries that cannot be matched SHALL be excluded from default `ksm list` output but included in `--all` output.

**Validates: Requirements 2.5, 2.6**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `src/ksm/manifest.py`

**Changes**:
1. **Add workspace_path to ManifestEntry**: Add `workspace_path: str | None = None` optional field to the dataclass. *(Already done.)*
2. **Update _entry_to_dict()**: Include `workspace_path` in serialized output when not None. *(Already done.)*
3. **Update _dict_to_entry()**: Read `workspace_path` from dict with `.get("workspace_path")` default None. *(Already done.)*
4. **backfill_workspace_paths()**: Function that scans manifest entries with `scope="local"` and `workspace_path is None`, checks if their `installed_files` exist under the current workspace's `.kiro/` directory, and if so sets `workspace_path` to the resolved current workspace path. Returns True if any entries were updated. *(Already done.)*

**File**: `src/ksm/installer.py`

**Function**: `install_bundle()` / `_update_manifest()`

**Changes**:
5. **Accept workspace_path parameter**: Add `workspace_path: str | None = None` to `_update_manifest()` and pass it through from `install_bundle()`. *(Already done.)*
6. **Record workspace_path for local scope**: When `scope="local"`, resolve and store the workspace path (`target_dir.parent.resolve()`). When `scope="global"`, leave it None. *(Already done.)*

**File**: `src/ksm/commands/ls.py`

**Function**: `run_ls()`

**Changes**:
7. **Filter local entries by workspace**: When `--all` is not set, filter local entries to only those whose `workspace_path` matches `os.path.realpath(os.getcwd())`. Global entries pass through unfiltered. *(Already done.)*
8. **Accept workspace_path parameter**: Add a `workspace_path` parameter (defaulting to `Path.cwd()`) so the function is testable without depending on the real cwd. *(Already done.)*
9. **Pass `show_all` flag to `_format_grouped()`**: When `--all` is active, pass a flag so the formatter can annotate local entries with their workspace path.

**Function**: `_format_grouped()`

**Changes**:
10. **Display workspace path for local entries in `--all` mode**: When `show_all=True`, append the workspace path as a muted annotation on each local entry row. For entries with `workspace_path=None` (unmatched legacy), display a placeholder like `(unknown workspace)`. This ensures requirement 2.4 is met — users can see WHICH workspace each local bundle belongs to.
    - The workspace path should appear as an additional column or annotation after the existing columns (name, registry, timestamp).
    - Example text output for `--all`:
      ```
      Local bundles:
        python_dev   built-in   2 days ago   ~/project-a
        aws          built-in   5 days ago   ~/project-b
        git          built-in   1 hour ago   (unknown workspace)
      ```

**Function**: `_format_json()` / `_entry_to_dict()`

**Changes**:
11. **Include workspace_path in JSON output**: The `_entry_to_dict()` function already includes `workspace_path` when not None. No additional changes needed for JSON — the field is present for local entries. *(Already done.)*

**File**: `src/ksm/cli.py`

**Changes**:
12. **Add --all flag**: Add `--all` argument to both `list` and `ls` subparsers via `_add_list_args()`. *(Already done.)*
13. **Pass workspace context to run_ls()**: Pass the resolved current workspace path when dispatching to `run_ls()`. *(Already done.)*
14. **Run backfill on dispatch**: Call `backfill_workspace_paths()` before `run_ls()` and persist if updated. *(Already done.)*

**File**: `src/ksm/cli.py` (broader backfill scope)

**Changes**:
15. **Backfill on all workspace-aware commands**: Requirement 2.5 states backfill should run on ANY `ksm` command within a workspace, not just `list`. Consider running `backfill_workspace_paths()` in the main dispatch path or at least for commands that load the manifest (add, rm, sync, list). Currently only `_dispatch_ls` runs backfill — this should be extended to other dispatch functions that operate on the manifest.

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
4. **No workspace path in --all text output**: Verify that `--all` text output does not show workspace paths for local entries (will fail on unfixed code)

**Expected Counterexamples**:
- `run_ls()` returns local entries from workspace-b when called from workspace-a
- `--all` output shows local entries without any workspace identification
- Possible causes: no `workspace_path` field, no filtering logic in `run_ls()`, no workspace annotation in `_format_grouped()`

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

**Additional fix check for requirement 2.4:**
```
FOR ALL input WHERE input.all_flag == true DO
  result := run_ls_fixed(input)
  ASSERT all local entries from all workspaces appear in result
  ASSERT each local entry in text output includes workspace_path annotation
  ASSERT local entries with workspace_path=None show "(unknown workspace)"
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
- Test `_format_grouped()` includes workspace path annotation for local entries when `show_all=True`
- Test `_format_grouped()` does NOT include workspace path annotation when `show_all=False`
- Test `_format_grouped()` shows `(unknown workspace)` for local entries with `workspace_path=None` in `--all` mode
- Test backfill function correctly identifies and updates legacy entries
- Test backfill function leaves unmatched legacy entries unchanged
- Test `--all` flag is accepted by the CLI parser
- Test legacy entries with `workspace_path=None` are excluded from default output but included in `--all` output

### Property-Based Tests

- Generate random manifests with mixed scopes and workspace paths, verify `run_ls()` output only contains local entries matching the current workspace (or all entries when `--all`)
- Generate random manifests with `--all` flag, verify every local entry in text output has a workspace path annotation
- Generate random global-only manifests, verify output is identical before and after fix
- Generate random manifests and verify JSON output always includes all required fields and is valid JSON

### Integration Tests

- Test full `ksm list` flow with multi-workspace manifest, verifying workspace filtering end-to-end
- Test `ksm list --all` shows cross-workspace bundles with workspace path annotations in text output
- Test `ksm list --all --format json` includes `workspace_path` field for all local entries
- Test `ksm list --scope local` respects workspace filtering
- Test legacy backfill runs transparently during `ksm list` and persists updated manifest
- Test backfill runs on other manifest-aware commands (add, rm, sync) per requirement 2.5
