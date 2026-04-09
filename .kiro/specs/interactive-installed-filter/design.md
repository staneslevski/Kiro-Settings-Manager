# Interactive Installed Filter Bugfix Design

## Overview

The interactive bundle selectors (`ksm add -i`, `ksm init`, `ksm rm -i`) do not filter by workspace when determining installed status. `ksm list` already does this correctly. The fix has two parts:

1. Replace the flat `installed_names: set[str]` with a workspace-aware `dict[str, set[str]]` mapping bundle names to scope labels, so the add/init selectors show "[installed: local]", "[installed: global]", or "[installed: local, global]" only for bundles relevant to the current workspace.
2. Filter the `entries_to_show` list in `run_rm()` interactive path to exclude local entries from other workspaces.

## Glossary

- **Bug_Condition (C)**: Interactive mode builds installed info from all manifest entries without filtering local entries by workspace_path
- **Property (P)**: Only global entries and local entries matching the current workspace appear as installed in interactive mode, with scope-specific badges
- **Preservation**: Non-interactive commands, `ksm list`, empty manifests, and global-only manifests are unaffected
- **`_handle_display()`**: Function in `src/ksm/commands/add.py` that builds `installed_names` and launches `interactive_select`
- **`run_init()`**: Function in `src/ksm/commands/init.py` that builds `installed` set and launches `interactive_select`
- **`run_rm()`**: Function in `src/ksm/commands/rm.py` — interactive path passes `manifest.entries` to `interactive_removal_select` without workspace filtering
- **`interactive_select()`**: Function in `src/ksm/selector.py` — accepts `installed_names: set[str]`
- **`interactive_removal_select()`**: Function in `src/ksm/selector.py` — accepts `entries: list[ManifestEntry]`
- **`BundleSelectorApp`**: TUI class in `src/ksm/tui.py` — accepts `installed_names: set[str]`
- **`RemovalSelectorApp`**: TUI class in `src/ksm/tui.py` — accepts `entries: list[ManifestEntry]`
- **`installed_names`**: Currently `set[str]`; will become `dict[str, set[str]]` mapping bundle names to scope sets

## Bug Details

### Bug Condition

Three separate code paths build installed info without workspace filtering:

1. `_handle_display()` in `add.py`: `installed_names = {e.bundle_name for e in manifest.entries}` — flat set, no filtering
2. `run_init()` in `init.py`: `installed = {e.bundle_name for e in manifest.entries}` — flat set, no filtering
3. `run_rm()` in `rm.py` interactive path: `entries_to_show = manifest.entries` (or scope-filtered) — includes local entries from all workspaces

**Formal Specification:**
```
FUNCTION isBugCondition(manifest, current_workspace)
  INPUT: manifest of type Manifest, current_workspace of type str
  OUTPUT: boolean

  RETURN EXISTS entry IN manifest.entries WHERE
         entry.scope == "local"
         AND entry.workspace_path != current_workspace
END FUNCTION
```

### Examples

- Bundle "python_dev" installed locally in `/home/user/project-a`. User runs `ksm add -i` from `/home/user/project-b`. Current: shows "[installed]". Expected: no badge.
- Bundle "aws" installed globally. User runs `ksm add -i` from any workspace. Current: "[installed]". Expected: "[installed: global]".
- Bundle "git" installed locally in current workspace AND globally. Current: "[installed]". Expected: "[installed: local, global]".
- Bundle "hooks" installed locally in current workspace only. Expected: "[installed: local]".
- Bundle "python_dev" installed locally in `/home/user/project-a`. User runs `ksm rm -i` from `/home/user/project-b`. Current: shows as removal candidate. Expected: not listed.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Global entries always appear as installed from any workspace (badge changes to "[installed: global]")
- Local entries for the current workspace continue to appear (badge changes to "[installed: local]")
- Empty manifest produces no installed badges
- Non-interactive commands (`ksm add <bundle>`, `ksm rm <bundle>`, `ksm list`, `ksm sync`) behave identically
- `ksm list` continues to show global + current-workspace local bundles
- `ksm list --all` continues to show global + all local bundles with workspace paths
- The numbered-list fallback selector continues to work

## Hypothesized Root Cause

1. **`_handle_display()` no workspace filtering** (add.py ~line 424): `installed_names = {e.bundle_name for e in manifest.entries}` includes all entries regardless of scope or workspace_path. It also doesn't receive `target_local` so has no workspace context.

2. **`run_init()` no workspace filtering** (init.py ~line 67): `installed = {e.bundle_name for e in manifest.entries}` — same flat set pattern.

3. **`run_rm()` interactive path no workspace filtering** (rm.py ~line 155): `entries_to_show = manifest.entries` includes local entries from all workspaces. The scope filter (`-l`/`-g`) narrows by scope but not by workspace_path.

4. **Flat `set[str]` type**: `installed_names` is `set[str]` — just bundle names with no scope info. Cannot distinguish local vs global.

## Correctness Properties

Property 1: Bug Condition — Cross-Workspace Local Entries Excluded from Add/Init

_For any_ manifest containing local entries with `workspace_path != current_workspace`, `build_installed_info()` SHALL exclude those entries, so they do not appear as installed in the add/init interactive selectors.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Bug Condition — Cross-Workspace Local Entries Excluded from Rm -i

_For any_ manifest containing local entries with `workspace_path != current_workspace`, the `run_rm()` interactive path SHALL exclude those entries from the removal candidate list.

**Validates: Requirements 2.7**

Property 3: Preservation — Global and Current-Workspace Entries Retained

_For any_ manifest entry where `scope == "global"` OR (`scope == "local"` AND `workspace_path == current_workspace`), `build_installed_info()` SHALL include that entry with the correct scope label.

**Validates: Requirements 3.1, 3.2**

Property 4: Badge Accuracy — Scope Labels Match Entry Scopes

_For any_ bundle name in the installed info mapping, the scope set SHALL contain exactly the scopes under which the bundle is installed in the current context ("local" if local in current workspace, "global" if global, both if both).

**Validates: Requirements 2.4, 2.5, 2.6**

Property 5: Preservation — Empty Manifest Produces Empty Info

_For any_ empty manifest, `build_installed_info()` SHALL return an empty mapping.

**Validates: Requirements 3.3**

## Fix Implementation

### Changes Required


**File**: `src/ksm/manifest.py`

**New Function**: `build_installed_info()`

1. Add `build_installed_info(manifest: Manifest, workspace_path: str) -> dict[str, set[str]]`. Iterates `manifest.entries`:
   - If `entry.scope == "global"`: add `"global"` to `result[entry.bundle_name]`
   - If `entry.scope == "local"` and `entry.workspace_path == workspace_path`: add `"local"` to `result[entry.bundle_name]`
   - Otherwise (local entry for different workspace): skip
   Returns the dict.

**New Function**: `format_installed_badge()`

2. Add `format_installed_badge(scopes: set[str]) -> str`. Returns `"[installed: local]"`, `"[installed: global]"`, or `"[installed: local, global]"` based on the scope set contents. Returns `""` if empty set.

---

**File**: `src/ksm/commands/add.py`

**Function**: `_handle_display()`

3. Add `workspace_path: str` parameter.
4. Replace `installed_names = {e.bundle_name for e in manifest.entries}` with `installed_info = build_installed_info(manifest, workspace_path)`.
5. Pass `installed_info` (the dict) to `interactive_select()`.

**Function**: `run_add()`

6. At both call sites of `_handle_display()` (~lines 170 and 180), pass `workspace_path=str(target_local.parent.resolve())`.

---

**File**: `src/ksm/commands/init.py`

**Function**: `run_init()`

7. Replace `installed = {e.bundle_name for e in manifest.entries}` with `installed_info = build_installed_info(manifest, str(target_dir.resolve()))`.
8. Pass `installed_info` to `interactive_select()`.

---

**File**: `src/ksm/commands/rm.py`

**Function**: `run_rm()` (interactive path)

9. After building `entries_to_show`, add workspace filtering for local entries:
   ```python
   workspace_path = str(target_local.parent.resolve())
   entries_to_show = [
       e for e in entries_to_show
       if e.scope == "global"
       or e.workspace_path == workspace_path
   ]
   ```
   This ensures `ksm rm -i` only shows globally installed bundles and locally installed bundles in the current workspace.

---

**File**: `src/ksm/selector.py`

**Function**: `interactive_select()`

10. Change `installed_names: set[str]` parameter to `installed_info: dict[str, set[str]]`.
11. In the numbered-list fallback path, replace `if b.name in installed_names: label_parts.append("[installed]")` with scope-aware badge using `format_installed_badge()`.
12. Pass `installed_info` to `BundleSelectorApp`.

**Function**: `render_add_selector()`

13. Change `installed_names: set[str]` parameter to `installed_info: dict[str, set[str]]`.
14. Replace `badge_text = " [installed]"` with dynamic badge from `format_installed_badge()`.
15. Replace `b.name in installed_names` checks with `b.name in installed_info`.
16. Compute `badge_width` as the max badge length across all installed bundles for alignment.

---

**File**: `src/ksm/tui.py`

**Class**: `BundleSelectorApp`

17. Change `__init__` parameter `installed_names: set[str]` to `installed_info: dict[str, set[str]]`.
18. In `_refresh_options()`:
    - Replace `badge_text = " [installed]"` with dynamic badge per bundle.
    - Replace `bundle.name in self.installed_names` with `bundle.name in self.installed_info`.
    - Compute `badge_width` as max badge length across visible installed bundles.
    - Render per-bundle badge using `format_installed_badge(self.installed_info[bundle.name])`.

**Class**: `RemovalSelectorApp` — No changes needed. The filtering happens upstream in `run_rm()`.

---

**Files with NO changes required:**

- `src/ksm/commands/ls.py` — Already workspace-aware, no interactive installed badge logic
- `src/ksm/remover.py` — Already workspace-aware
- `src/ksm/installer.py` — Already uses `find_entries()` for workspace-aware matching

## Testing Strategy

### Validation Approach

Two-phase: surface counterexamples on unfixed code, then verify fix + preservation.

### Exploratory Bug Condition Checking

**Goal**: Demonstrate the bug exists BEFORE implementing the fix.

**Test Cases**:
1. Build manifest with local entry for workspace-A. Call `build_installed_info(manifest, workspace_B)` (once it exists) or simulate the current flat-set logic. Assert cross-workspace entry appears (confirms bug).
2. Build manifest with local entry for workspace-A. Simulate `run_rm()` interactive `entries_to_show` logic. Assert workspace-A entry appears from workspace-B context (confirms bug).
3. Build manifest with both local and global entries for same bundle. Assert badge is flat "[installed]" with no scope distinction (confirms bug).

### Fix Checking

**Pseudocode:**
```
FOR ALL (manifest, workspace_path) WHERE isBugCondition(manifest, workspace_path) DO
  result := build_installed_info(manifest, workspace_path)
  FOR entry IN manifest.entries WHERE entry.scope == "local"
      AND entry.workspace_path != workspace_path DO
    ASSERT entry.bundle_name NOT IN result
        OR "local" NOT IN result[entry.bundle_name]
  END FOR
END FOR
```

### Preservation Checking

**Pseudocode:**
```
FOR ALL (manifest, workspace_path) WHERE NOT isBugCondition(manifest, workspace_path) DO
  old_names := {e.bundle_name for e in manifest.entries}
  new_info := build_installed_info(manifest, workspace_path)
  ASSERT set(new_info.keys()) == old_names
END FOR
```

### Unit Tests

- `build_installed_info()` with cross-workspace local entries (excluded)
- `build_installed_info()` with current-workspace local entries (included as "local")
- `build_installed_info()` with global entries (included as "global")
- `build_installed_info()` with mixed local+global same bundle (both scopes)
- `build_installed_info()` with empty manifest (empty dict)
- `build_installed_info()` with `workspace_path=None` legacy entries
- `format_installed_badge()` for each scope combination
- `run_rm()` interactive path workspace filtering

### Property-Based Tests

- Generate random manifests with random workspace paths; verify cross-workspace local entries excluded
- Generate random manifests; verify global entries always included
- Generate random manifests where all entries match current workspace; verify all appear
- Generate random scope sets; verify badge formatting correctness

### Integration Tests

- `_handle_display()` end-to-end with workspace filtering
- `run_init()` end-to-end with workspace filtering
- `run_rm()` interactive path end-to-end with workspace filtering
- Full selector rendering with scope-aware badges
