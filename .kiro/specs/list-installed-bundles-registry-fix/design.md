# List Installed Bundles Registry Fix — Bugfix Design

## Overview

The `remove_bundle()` function in `src/ksm/remover.py` filters manifest entries by `bundle_name` and `scope` only, ignoring `workspace_path`. When a local-scoped bundle is installed in multiple workspaces, removing it from one workspace incorrectly removes all manifest entries for that bundle across every workspace. The fix adds `workspace_path` to the filter predicate for local-scoped entries so that only the targeted workspace's entry is removed.

## Glossary

- **Bug_Condition (C)**: A local-scoped bundle is installed in two or more workspaces and `remove_bundle()` is called for one of them — the filter removes entries for all workspaces instead of just the target
- **Property (P)**: After removal, only the manifest entry matching `bundle_name`, `scope`, AND `workspace_path` of the removed entry is deleted; entries for other workspaces remain
- **Preservation**: Global-scoped removal, single-workspace local removal, file deletion, and empty directory cleanup must all continue to work exactly as before
- **`remove_bundle()`**: The function in `src/ksm/remover.py` that deletes installed files and removes the manifest entry
- **`ManifestEntry`**: Dataclass in `src/ksm/manifest.py` with fields `bundle_name`, `scope`, `workspace_path`, etc.
- **`workspace_path`**: Optional string on `ManifestEntry` identifying which workspace a local-scoped bundle belongs to

## Bug Details

### Bug Condition

The bug manifests when a local-scoped bundle is installed in multiple workspaces and `remove_bundle()` is called for one workspace. The manifest entry filter on lines 62–65 of `src/ksm/remover.py` matches on `bundle_name` and `scope` only, so it removes ALL entries for that bundle name and scope — including entries belonging to other workspaces.

**Formal Specification:**
```
FUNCTION isBugCondition(entry, manifest)
  INPUT: entry of type ManifestEntry, manifest of type Manifest
  OUTPUT: boolean

  other_entries := [e FOR e IN manifest.entries
                    WHERE e.bundle_name == entry.bundle_name
                    AND e.scope == entry.scope
                    AND e.workspace_path != entry.workspace_path]

  RETURN entry.scope == "local"
         AND entry.workspace_path IS NOT None
         AND LEN(other_entries) >= 1
END FUNCTION
```

### Examples

- Bundle "aws" installed locally in `/projects/alpha` and `/projects/beta`. Removing from `/projects/alpha` deletes both manifest entries. After removal, `ksm list --all` shows "aws" is not installed anywhere — expected: still installed in `/projects/beta`.
- Bundle "git" installed locally in `/workspace/a`, `/workspace/b`, and `/workspace/c`. Removing from `/workspace/b` deletes all three entries — expected: entries for `/workspace/a` and `/workspace/c` remain.
- Bundle "aws" installed locally in only `/projects/alpha`. Removing it correctly deletes the single entry — this case works fine today (no bug).
- Bundle "aws" installed globally (no `workspace_path`). Removing it correctly deletes the single global entry — this case works fine today (no bug).

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Removing a bundle installed in only one workspace must continue to delete files and remove the manifest entry
- Removing a global-scoped bundle must continue to match on `bundle_name` and `scope` (global entries have `workspace_path=None`)
- File deletion from disk and empty subdirectory cleanup must remain unchanged
- All other bundle entries in the manifest must be preserved when one bundle is removed

**Scope:**
All inputs that do NOT involve a local-scoped bundle installed in multiple workspaces should be completely unaffected by this fix. This includes:
- Global-scoped bundle removal
- Local-scoped bundle removal when installed in only one workspace
- Any removal where `workspace_path` is `None` (legacy entries)
- File deletion and directory cleanup logic (untouched by this fix)

## Hypothesized Root Cause

Based on the bug description and code analysis, the root cause is a single missing predicate in the manifest entry filter.

1. **Incomplete Filter Predicate**: The list comprehension on lines 62–65 of `src/ksm/remover.py` filters entries using only `e.bundle_name == entry.bundle_name and e.scope == entry.scope`. It does not compare `e.workspace_path == entry.workspace_path`, so all entries sharing the same name and scope are removed regardless of which workspace they belong to.

2. **Global Scope Consideration**: For global-scoped entries, `workspace_path` is `None`, so the fix must only apply the `workspace_path` comparison when the scope is `"local"` and the entry has a non-`None` `workspace_path`. Otherwise, global removal and legacy local entries (with `workspace_path=None`) would break.

## Correctness Properties

Property 1: Bug Condition — Multi-workspace local removal preserves other workspaces

_For any_ manifest containing two or more local-scoped entries with the same `bundle_name` but different `workspace_path` values, when `remove_bundle()` is called for one entry, the fixed function SHALL remove only the entry whose `workspace_path` matches the removed entry, leaving all other entries intact.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation — Single-workspace and global removal unchanged

_For any_ input where the bug condition does NOT hold (single local entry, global entry, or legacy entry with `workspace_path=None`), the fixed function SHALL produce the same manifest state as the original function, preserving all existing removal behavior.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `src/ksm/remover.py`

**Function**: `remove_bundle()`

**Specific Changes**:
1. **Add `workspace_path` to filter predicate**: Modify the list comprehension on lines 62–65 to also compare `workspace_path` when the entry being removed has a non-`None` `workspace_path`. The filter should keep entries that do NOT match on all three fields (`bundle_name`, `scope`, and `workspace_path`).

2. **Handle `None` workspace_path gracefully**: When `entry.workspace_path` is `None` (global scope or legacy local entries), the filter should fall back to the current behavior of matching on `bundle_name` and `scope` only. This ensures backward compatibility.

The change is a single predicate addition to the existing list comprehension — no new functions, no structural changes.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Create a manifest with two local-scoped entries for the same bundle name but different `workspace_path` values. Call `remove_bundle()` for one entry and assert the other entry remains. Run on UNFIXED code to observe the failure.

**Test Cases**:
1. **Two-workspace removal**: Install "aws" locally in `/ws/a` and `/ws/b`, remove from `/ws/a` — assert `/ws/b` entry remains (will fail on unfixed code)
2. **Three-workspace removal**: Install "aws" locally in three workspaces, remove from one — assert the other two remain (will fail on unfixed code)
3. **Same name different scope**: Install "aws" locally and globally, remove local — assert global entry remains (may pass on unfixed code since scopes differ)

**Expected Counterexamples**:
- After removing one workspace's entry, `manifest.entries` is empty instead of containing the other workspace's entry
- Root cause confirmed: the filter `e.bundle_name == entry.bundle_name and e.scope == entry.scope` matches all entries with the same name and scope

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL (entry, manifest) WHERE isBugCondition(entry, manifest) DO
  other_entries_before := [e FOR e IN manifest.entries
                           WHERE e.bundle_name == entry.bundle_name
                           AND e.scope == entry.scope
                           AND e.workspace_path != entry.workspace_path]
  result := remove_bundle_fixed(entry, target_dir, manifest)
  ASSERT entry NOT IN manifest.entries
  FOR EACH other IN other_entries_before DO
    ASSERT other IN manifest.entries
  END FOR
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL (entry, manifest) WHERE NOT isBugCondition(entry, manifest) DO
  manifest_copy := deep_copy(manifest)
  remove_bundle_original(entry, target_dir, manifest)
  remove_bundle_fixed(entry, target_dir, manifest_copy)
  ASSERT manifest.entries == manifest_copy.entries
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many manifest configurations automatically
- It catches edge cases around `None` workspace paths and mixed scopes
- It provides strong guarantees that single-workspace and global removal are unchanged

**Test Plan**: Observe behavior on UNFIXED code first for single-workspace local removal and global removal, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Single local entry preservation**: Verify removing a local bundle installed in only one workspace still works correctly after fix
2. **Global entry preservation**: Verify removing a global bundle still works correctly after fix
3. **Other entries preservation**: Verify unrelated bundle entries are never affected by removal
4. **Legacy None workspace_path**: Verify entries with `workspace_path=None` are handled correctly

### Unit Tests

- Test multi-workspace local removal: two entries, remove one, other remains
- Test multi-workspace local removal: three entries, remove one, other two remain
- Test single-workspace local removal still works
- Test global-scoped removal still works
- Test mixed scope entries (local + global for same bundle name)
- Test legacy entries with `workspace_path=None`

### Property-Based Tests

- Generate random manifests with multiple local entries for the same bundle across different workspaces; verify only the targeted entry is removed
- Generate random manifests with single entries (local or global); verify removal behavior matches original
- Generate manifests mixing local and global entries; verify cross-scope isolation

### Integration Tests

- Test full `run_rm` flow with multi-workspace local bundles
- Test `ksm list --all` after partial removal shows remaining workspace entries
- Test removal + list round-trip preserves correct state
