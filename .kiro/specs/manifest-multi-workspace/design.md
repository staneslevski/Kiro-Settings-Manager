# Manifest Multi-Workspace Bugfix Design

## Overview

The `_update_manifest()` function in `installer.py` and the entry lookup in `rm.py` use `(bundle_name, scope)` as the key when matching manifest entries. For local-scoped bundles, this means installing the same bundle in workspace B silently overwrites the manifest entry for workspace A, and `ksm rm` from workspace A cannot find its entry after the overwrite. The fix adds `workspace_path` to the lookup key for local-scoped entries in both `_update_manifest()` and `run_rm()`.

## Glossary

- **Bug_Condition (C)**: A local-scoped manifest operation (install or remove) where the lookup uses only `(bundle_name, scope)` instead of `(bundle_name, scope, workspace_path)`
- **Property (P)**: Each workspace's local manifest entry is independently tracked; installing in workspace B does not affect workspace A's entry, and removing from workspace A targets only workspace A's entry
- **Preservation**: Global-scoped operations and same-workspace re-installs must continue to behave identically
- **`_update_manifest()`**: The function in `src/ksm/installer.py` that adds or updates a manifest entry after installing a bundle
- **`run_rm()`**: The function in `src/ksm/commands/rm.py` that finds and removes a manifest entry
- **`workspace_path`**: The resolved absolute path of the workspace directory, stored on local-scoped `ManifestEntry` objects

## Bug Details

### Bug Condition

The bug manifests when the same bundle is installed locally in two different workspaces. The `_update_manifest()` function finds an existing entry matching `(bundle_name, scope)` and overwrites it, discarding the first workspace's record. Similarly, `run_rm()` matches entries by `(bundle_name, scope)` without considering `workspace_path`, so it may target the wrong entry or fail to find the correct one.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type ManifestOperation (install or remove)
  OUTPUT: boolean

  RETURN input.scope == "local"
         AND input.workspace_path IS NOT NULL
         AND manifest contains an entry WHERE
             entry.bundle_name == input.bundle_name
             AND entry.scope == "local"
             AND entry.workspace_path != input.workspace_path
END FUNCTION
```

### Examples

- Install bundle "python_dev" locally in `/home/user/projectA`, then install "python_dev" locally in `/home/user/projectB`. Expected: two separate manifest entries. Actual: only the projectB entry exists; projectA's entry is overwritten.
- Run `ksm list --all` after the above. Expected: both workspaces listed. Actual: only projectB shown.
- Run `ksm rm python_dev -l` from projectA after the overwrite. Expected: removes projectA's entry. Actual: entry not found (it was replaced by projectB's entry) or removes projectB's entry incorrectly.
- Install "python_dev" locally in projectA, then re-install "python_dev" locally in projectA again. Expected: entry updated in place (no duplicate). Actual: works correctly today — this is not a bug case.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Global-scoped installs must continue to use `(bundle_name, scope)` as the lookup key since global entries have no workspace_path
- Re-installing the same bundle locally in the same workspace must update the existing entry in place, not create a duplicate
- `ksm list` without `--all` must continue to filter local entries to only the current workspace
- `ksm rm <bundle> -g` must continue to match by `(bundle_name, scope)` without considering workspace_path
- The `remove_bundle()` function in `remover.py` already handles workspace_path in its manifest cleanup filter and needs no changes
- The `backfill_workspace_paths()` function must continue to work for legacy entries

**Scope:**
All inputs that do NOT involve local-scoped operations across different workspaces should be completely unaffected by this fix. This includes:
- All global-scoped install and remove operations
- Local-scoped operations within a single workspace
- List operations (already workspace-aware)
- Manifest serialization/deserialization

## Hypothesized Root Cause

Based on the bug description, the most likely issues are:

1. **`_update_manifest()` lookup key too narrow**: Line `existing = [e for e in manifest.entries if e.bundle_name == bundle_name and e.scope == scope]` does not include `workspace_path` in the filter for local-scoped entries. When a second workspace installs the same bundle, it finds the first workspace's entry and overwrites it.

2. **`run_rm()` lookup key too narrow**: Line `matches = [e for e in manifest.entries if e.bundle_name == bundle_name and e.scope == scope]` in `rm.py` does not include `workspace_path` for local-scoped entries. This means it may match the wrong workspace's entry or fail to find the correct one after an overwrite.

3. **No workspace-aware lookup helper**: There is no shared utility function for workspace-aware entry matching, leading to the same pattern being duplicated (and broken) in multiple places.

## Correctness Properties

Property 1: Bug Condition - Multi-Workspace Local Install Independence

_For any_ sequence of local-scoped install operations where the same bundle is installed in two different workspaces, the manifest SHALL contain separate entries for each workspace, and neither entry SHALL be overwritten or lost.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - Global and Same-Workspace Behavior Unchanged

_For any_ manifest operation that is either (a) global-scoped, or (b) local-scoped within the same workspace as an existing entry, the fixed code SHALL produce the same result as the original code, preserving global lookup by `(bundle_name, scope)` and same-workspace update-in-place behavior.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**


Property 3: Bug Condition - Workspace-Aware Removal

_For any_ `ksm rm <bundle> -l` operation executed from a specific workspace, the fixed code SHALL match the manifest entry using both `bundle_name` and `workspace_path`, removing only the entry for the current workspace and leaving other workspaces' entries intact.

**Validates: Requirements 2.3**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `src/ksm/manifest.py`

**Function**: New helper `find_entries()`

**Specific Changes**:
1. **Add workspace-aware lookup helper**: Create a `find_entries(manifest, bundle_name, scope, workspace_path=None)` function that includes `workspace_path` in the match criteria when `scope == "local"` and `workspace_path` is provided. This centralizes the lookup logic and prevents future duplication of the bug.

**File**: `src/ksm/installer.py`

**Function**: `_update_manifest()`

**Specific Changes**:
2. **Use workspace-aware matching**: Replace the existing filter `e.bundle_name == bundle_name and e.scope == scope` with a call to `find_entries()` (or inline the equivalent logic) that also matches on `workspace_path` when `scope == "local"`. This ensures installing in workspace B does not find and overwrite workspace A's entry.

**File**: `src/ksm/commands/rm.py`

**Function**: `run_rm()`

**Specific Changes**:
3. **Use workspace-aware matching for local removal**: Replace the existing filter `e.bundle_name == bundle_name and e.scope == scope` with logic that also matches on `workspace_path` when `scope == "local"`. The current workspace path should be derived from `target_local.parent.resolve()` (consistent with how `install_bundle` computes it).
4. **Pass workspace context**: Ensure the resolved workspace path is available in `run_rm()` for the lookup. The `target_local` parameter already provides this — `str(target_local.parent.resolve())` gives the workspace path.

**File**: `src/ksm/commands/ls.py`

**No changes required**: The `run_ls()` function already filters local entries by `workspace_path` when `--all` is not set, and displays `workspace_path` when `--all` is set. Once the manifest correctly contains separate entries per workspace, listing will work correctly.

**File**: `src/ksm/remover.py`

**No changes required**: The `remove_bundle()` function already includes `workspace_path` in its manifest cleanup filter (line: `entry.workspace_path is None or e.workspace_path == entry.workspace_path`). Once `run_rm()` passes the correct entry, removal will work correctly.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that create a manifest, call `_update_manifest()` twice with the same bundle name and `scope="local"` but different `workspace_path` values, then assert both entries exist. Run these tests on the UNFIXED code to observe failures.

**Test Cases**:
1. **Dual Workspace Install Test**: Install bundle "X" locally in workspace A, then install "X" locally in workspace B. Assert manifest has 2 entries. (will fail on unfixed code — only 1 entry)
2. **Overwrite Detection Test**: After dual install, check that workspace A's `installed_files` and `workspace_path` are preserved. (will fail on unfixed code — workspace A's data is overwritten)
3. **Rm Wrong Workspace Test**: After dual install, run rm lookup from workspace A. Assert it finds workspace A's entry, not workspace B's. (will fail on unfixed code)
4. **List All Test**: After dual install, run `ksm list --all` and assert both workspace entries appear. (will fail on unfixed code — only 1 entry in manifest)

**Expected Counterexamples**:
- After two local installs of the same bundle in different workspaces, `len(manifest.entries)` is 1 instead of 2
- The surviving entry has `workspace_path` of the second workspace, not the first
- `run_rm()` from workspace A matches workspace B's entry

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := _update_manifest_fixed(input)
  ASSERT manifest contains separate entries for each workspace
  ASSERT each entry's workspace_path matches its install workspace
  ASSERT each entry's installed_files are independent
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT _update_manifest_original(input) = _update_manifest_fixed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for global installs and same-workspace re-installs, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Global Install Preservation**: Verify that global-scoped installs continue to use `(bundle_name, scope)` matching and update in place correctly
2. **Same-Workspace Re-install Preservation**: Verify that re-installing the same bundle in the same workspace updates the existing entry rather than creating a duplicate
3. **Global Rm Preservation**: Verify that `ksm rm <bundle> -g` continues to match by `(bundle_name, scope)` without workspace_path
4. **List Filtering Preservation**: Verify that `ksm list` (without `--all`) continues to filter local entries to the current workspace only

### Unit Tests

- Test `_update_manifest()` with two different workspace paths for the same local bundle
- Test `_update_manifest()` with same workspace path (update-in-place)
- Test `_update_manifest()` with global scope (no workspace_path consideration)
- Test `find_entries()` helper with various combinations of scope and workspace_path
- Test `run_rm()` lookup with local scope and specific workspace_path
- Test `run_rm()` lookup with global scope (unchanged behavior)
- Test edge case: `workspace_path=None` for legacy entries

### Property-Based Tests

- Generate random bundle names, workspace paths, and scopes; verify that local entries with different workspace paths are always stored independently
- Generate random sequences of install operations; verify that global entries are never affected by workspace_path logic
- Generate random manifest states; verify that `find_entries()` returns correct matches for all combinations of scope and workspace_path

### Integration Tests

- Test full install-list-remove flow across two workspaces
- Test that `ksm list --all` shows both workspace entries after multi-workspace install
- Test that `ksm rm` from workspace A only removes workspace A's entry, leaving workspace B intact
