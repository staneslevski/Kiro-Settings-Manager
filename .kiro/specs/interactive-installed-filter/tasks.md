# Implementation Plan

- [ ] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Cross-Workspace Local Entries Shown as Installed in Interactive Mode
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to manifests containing local entries with workspace_path != current_workspace

  - [ ] 1.1. Write exploration tests for installed-info and rm filtering bugs

    - [ ] 1.1.1. Create test file `tests/test_interactive_installed_filter_bug.py`
      - Import `Manifest`, `ManifestEntry` from `src/ksm/manifest.py`
      - Use Hypothesis to generate bundle names (`st.text` with min_size=1, alphabet=ascii_lowercase+digits+underscore), scope values, and two distinct workspace paths
      - Bug condition: manifest contains a local entry with `workspace_path == workspace_A` and we query from `workspace_B` (where `workspace_A != workspace_B`)

    - [ ] 1.1.2. Write exploration test for `build_installed_info()` cross-workspace exclusion
      - Test that `build_installed_info(manifest, workspace_B)` excludes local entries from `workspace_A`
      - Use Hypothesis to generate manifests with local entries for workspace_A
      - Assert: for each local entry where `entry.workspace_path != current_workspace`, the bundle name is NOT in the result OR `"local"` is NOT in the result's scope set
      - On UNFIXED code: `build_installed_info()` does not exist yet, so simulate the current flat-set logic: `installed_names = {e.bundle_name for e in manifest.entries}` — assert that cross-workspace entries ARE included (confirms bug)
      - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3_

    - [ ] 1.1.3. Write exploration test for `run_rm()` interactive path cross-workspace inclusion
      - Create a manifest with a local entry for workspace_A
      - Simulate the current `entries_to_show` logic: `entries_to_show = manifest.entries` (no workspace filtering)
      - Assert: entries from workspace_A appear in `entries_to_show` when queried from workspace_B context (confirms bug)
      - Use Hypothesis to generate bundle names and two distinct workspace paths
      - _Requirements: 1.4, 2.7_

    - [ ] 1.1.4. Write exploration test for flat badge (no scope distinction)
      - Create a manifest with both a local entry (current workspace) and a global entry for the same bundle
      - Simulate the current flat-set logic: `installed_names = {e.bundle_name for e in manifest.entries}`
      - Assert: the set contains only the bundle name with no scope info (confirms badge bug — no local/global distinction)
      - _Requirements: 1.5, 2.4, 2.5, 2.6_

    - [ ] 1.1.5. Run tests on UNFIXED code
      - Run: `source .venv/bin/activate && pytest tests/test_interactive_installed_filter_bug.py -v`
      - **EXPECTED OUTCOME**: Tests FAIL (this confirms the bug exists)
      - Document counterexamples found (e.g., "local entry from workspace_A appears as installed when queried from workspace_B")
      - Mark task complete when tests are written, run, and failure is documented

  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Global Entries, Current-Workspace Entries, and Non-Interactive Commands Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs (global entries, current-workspace local entries, empty manifests)
  - Write property-based tests capturing observed behavior patterns

  - [ ] 2.1. Write preservation tests

    - [ ] 2.1.1. Create test file `tests/test_interactive_installed_filter_preservation.py`
      - Import `Manifest`, `ManifestEntry` from `src/ksm/manifest.py`

    - [ ] 2.1.2. Write global entry always-included preservation property
      - Use Hypothesis to generate bundle names and workspace paths
      - Observe: on unfixed code, global entries always appear in `installed_names` regardless of workspace
      - Write property: for all manifests containing only global entries, `build_installed_info()` (or simulated flat-set logic) includes every global bundle name
      - This captures the invariant that global entries are always visible
      - _Requirements: 3.1_

    - [ ] 2.1.3. Write current-workspace local entry preservation property
      - Use Hypothesis to generate bundle names and a single workspace path
      - Observe: on unfixed code, local entries for the current workspace appear in `installed_names`
      - Write property: for all manifests where every local entry has `workspace_path == current_workspace`, all bundle names appear in the installed set
      - _Requirements: 3.2_

    - [ ] 2.1.4. Write empty manifest preservation property
      - Observe: on unfixed code, empty manifest produces empty `installed_names` set
      - Write property: for empty manifest, the installed info is empty (no badges)
      - _Requirements: 3.3_

    - [ ] 2.1.5. Write non-interactive command preservation property
      - Observe: `find_entries()` already handles workspace-aware matching for non-interactive `ksm rm <bundle>` and `ksm add <bundle>`
      - Write property: for all manifests, `find_entries(manifest, name, "global")` returns global entries regardless of workspace; `find_entries(manifest, name, "local", ws)` returns only matching workspace entries
      - This ensures the non-interactive paths are unaffected
      - _Requirements: 3.4, 3.5a, 3.5b_

    - [ ] 2.1.6. Run preservation tests on UNFIXED code
      - Run: `source .venv/bin/activate && pytest tests/test_interactive_installed_filter_preservation.py -v`
      - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
      - Mark task complete when tests are written, run, and passing on unfixed code

  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5a, 3.5b, 3.6_

- [ ] 3. Fix for interactive installed filter bug

  - [ ] 3.1. Add `build_installed_info()` and `format_installed_badge()` to `src/ksm/manifest.py`

    - [ ] 3.1.1. Implement `build_installed_info()` function
      - Add function `build_installed_info(manifest: Manifest, workspace_path: str) -> dict[str, set[str]]`
      - Iterate `manifest.entries`: if `scope == "global"`, add `"global"` to `result[entry.bundle_name]`; if `scope == "local"` and `entry.workspace_path == workspace_path`, add `"local"` to `result[entry.bundle_name]`; otherwise skip
      - Returns `defaultdict(set)` converted to plain dict
      - _Bug_Condition: isBugCondition(manifest, ws) where EXISTS entry with scope=="local" AND workspace_path != ws_
      - _Expected_Behavior: cross-workspace local entries excluded from result_
      - _Preservation: Global entries always included; current-workspace local entries included_
      - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3_

    - [ ] 3.1.2. Implement `format_installed_badge()` function
      - Add function `format_installed_badge(scopes: set[str]) -> str`
      - Returns `""` for empty set, `"[installed: local]"` for `{"local"}`, `"[installed: global]"` for `{"global"}`, `"[installed: local, global]"` for `{"local", "global"}`
      - _Requirements: 2.4, 2.5, 2.6_

    - [ ] 3.1.3. Write unit tests for `build_installed_info()` and `format_installed_badge()`
      - Test: cross-workspace local entries excluded
      - Test: current-workspace local entries included as `"local"`
      - Test: global entries included as `"global"`
      - Test: mixed local+global same bundle returns both scopes
      - Test: empty manifest returns empty dict
      - Test: legacy entries with `workspace_path=None` excluded from local scope
      - Test: `format_installed_badge()` for each scope combination
      - Run: `source .venv/bin/activate && pytest tests/test_manifest.py -v -k "build_installed_info or format_installed_badge"`

  - [ ] 3.2. Update `_handle_display()` and `run_add()` in `src/ksm/commands/add.py`

    - [ ] 3.2.1. Add `workspace_path` parameter to `_handle_display()`
      - Change signature to `_handle_display(registry_index, manifest, workspace_path: str)`
      - Replace `installed_names = {e.bundle_name for e in manifest.entries}` with `installed_info = build_installed_info(manifest, workspace_path)`
      - Pass `installed_info` (dict) to `interactive_select()`
      - Import `build_installed_info` from `ksm.manifest`
      - _Requirements: 2.1, 2.4, 2.5, 2.6_

    - [ ] 3.2.2. Update `run_add()` call sites to pass `workspace_path`
      - At both `_handle_display()` call sites, pass `workspace_path=str(target_local.parent.resolve())`
      - _Requirements: 2.1_

  - [ ] 3.3. Update `run_init()` in `src/ksm/commands/init.py`

    - [ ] 3.3.1. Replace flat installed set with workspace-aware info
      - Replace `installed = {e.bundle_name for e in manifest.entries}` with `installed_info = build_installed_info(manifest, str(target_dir.resolve()))`
      - Pass `installed_info` to `interactive_select()`
      - Import `build_installed_info` from `ksm.manifest`
      - _Requirements: 2.3_

  - [ ] 3.4. Update `run_rm()` interactive path in `src/ksm/commands/rm.py`

    - [ ] 3.4.1. Add workspace filtering for `entries_to_show`
      - After building `entries_to_show` (scope-filtered or full), add workspace filtering:
        ```python
        workspace_path = str(target_local.parent.resolve())
        entries_to_show = [
            e for e in entries_to_show
            if e.scope == "global"
            or e.workspace_path == workspace_path
        ]
        ```
      - This ensures `ksm rm -i` only shows globally installed bundles and locally installed bundles in the current workspace
      - _Bug_Condition: entries_to_show includes local entries from other workspaces_
      - _Expected_Behavior: only global + current-workspace local entries shown_
      - _Requirements: 2.7, 3.6_

  - [ ] 3.5. Update `interactive_select()` and `render_add_selector()` in `src/ksm/selector.py`

    - [ ] 3.5.1. Change `interactive_select()` parameter from `set[str]` to `dict[str, set[str]]`
      - Change `installed_names: set[str]` to `installed_info: dict[str, set[str]]`
      - In numbered-list fallback: replace `if b.name in installed_names: label_parts.append("[installed]")` with scope-aware badge using `format_installed_badge(installed_info.get(b.name, set()))`
      - Pass `installed_info` to `BundleSelectorApp`
      - Import `format_installed_badge` from `ksm.manifest`
      - _Requirements: 2.4, 2.5, 2.6_

    - [ ] 3.5.2. Change `render_add_selector()` parameter from `set[str]` to `dict[str, set[str]]`
      - Change `installed_names: set[str]` to `installed_info: dict[str, set[str]]`
      - Replace `badge_text = " [installed]"` with dynamic badge per bundle via `format_installed_badge()`
      - Replace `b.name in installed_names` checks with `b.name in installed_info`
      - Compute `badge_width` as max badge length across all installed bundles for alignment
      - Import `format_installed_badge` from `ksm.manifest`
      - _Requirements: 2.4, 2.5, 2.6_

  - [ ] 3.6. Update `BundleSelectorApp` in `src/ksm/tui.py`

    - [ ] 3.6.1. Change `__init__` parameter from `set[str]` to `dict[str, set[str]]`
      - Change `installed_names: set[str]` to `installed_info: dict[str, set[str]]`
      - Store as `self.installed_info`
      - In `_refresh_options()`: replace `badge_text = " [installed]"` with dynamic per-bundle badge via `format_installed_badge(self.installed_info.get(bundle.name, set()))`
      - Replace `bundle.name in self.installed_names` with `bundle.name in self.installed_info`
      - Compute `badge_width` as max badge length across visible installed bundles
      - Import `format_installed_badge` from `ksm.manifest`
      - _Requirements: 2.4, 2.5, 2.6_

  - [ ] 3.7. Update existing tests for changed signatures

    - [ ] 3.7.1. Update `tests/test_selector.py` for `installed_info: dict` parameter
      - Change all `installed_names` arguments from `set[str]` to `dict[str, set[str]]` in calls to `render_add_selector()` and `interactive_select()`
      - Update assertions for scope-aware badge text (e.g., `"[installed: global]"` instead of `"[installed]"`)
      - Run: `source .venv/bin/activate && pytest tests/test_selector.py -v`

    - [ ] 3.7.2. Update `tests/test_tui.py` for `installed_info: dict` parameter
      - Change all `installed_names` arguments from `set[str]` to `dict[str, set[str]]` in `BundleSelectorApp` instantiation
      - Update assertions for scope-aware badge text
      - Run: `source .venv/bin/activate && pytest tests/test_tui.py -v`

    - [ ] 3.7.3. Update `tests/test_add.py` for `_handle_display()` signature change
      - Update mocks/calls to `_handle_display()` to include `workspace_path` parameter
      - Run: `source .venv/bin/activate && pytest tests/test_add.py -v`

    - [ ] 3.7.4. Run all updated test files together
      - Run: `source .venv/bin/activate && pytest tests/test_selector.py tests/test_tui.py tests/test_add.py tests/test_rm.py -v`
      - Ensure all pass

  - [ ] 3.8. Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Cross-Workspace Local Entries Excluded
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run: `source .venv/bin/activate && pytest tests/test_interactive_installed_filter_bug.py -v`
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [ ] 3.9. Verify preservation tests still pass
    - **Property 2: Preservation** - Global Entries, Current-Workspace Entries, and Non-Interactive Commands Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run: `source .venv/bin/activate && pytest tests/test_interactive_installed_filter_preservation.py -v`
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all preservation tests still pass after fix
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5a, 3.5b, 3.6_

- [ ] 4. Checkpoint - Ensure all tests pass
  - Run full test suite: `source .venv/bin/activate && pytest tests/ -v`
  - Ensure all tests pass, ask the user if questions arise
  - Run formatting: `source .venv/bin/activate && black src/ksm/manifest.py src/ksm/commands/add.py src/ksm/commands/init.py src/ksm/commands/rm.py src/ksm/selector.py src/ksm/tui.py tests/test_interactive_installed_filter_bug.py tests/test_interactive_installed_filter_preservation.py`
  - Run linting: `source .venv/bin/activate && flake8 src/ksm/manifest.py src/ksm/commands/add.py src/ksm/commands/init.py src/ksm/commands/rm.py src/ksm/selector.py src/ksm/tui.py`
  - Run type checking: `source .venv/bin/activate && mypy src/ksm/manifest.py src/ksm/commands/add.py src/ksm/commands/init.py src/ksm/commands/rm.py src/ksm/selector.py src/ksm/tui.py`
  - Verify coverage: `source .venv/bin/activate && pytest --cov=src/ksm tests/ --cov-report=term-missing`
  - Ensure ≥95% coverage for changed modules
