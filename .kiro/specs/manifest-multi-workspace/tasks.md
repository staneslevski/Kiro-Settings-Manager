# Implementation Plan

- [ ] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Multi-Workspace Local Install Overwrites Entry
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to concrete failing cases: same bundle name installed locally with two different workspace paths

  - [ ] 1.1. Write exploration test for `_update_manifest()` overwrite bug

    - [x] 1.1.1. Create test file `tests/test_manifest_multi_workspace_bug.py`
      - Import `Manifest`, `ManifestEntry` from `src/ksm/manifest.py`
      - Import `_update_manifest` from `src/ksm/installer.py`
      - Use Hypothesis to generate bundle names (`st.text` with min_size=1, alphabet=ascii_lowercase+digits+underscore) and two distinct workspace paths
      - Bug condition: `scope == "local"` AND two calls to `_update_manifest()` with same `(bundle_name, scope)` but different `workspace_path` values
      - Assert: after both calls, `len(manifest.entries) == 2` (one per workspace)
      - Assert: each entry's `workspace_path` matches its respective install workspace
      - Assert: each entry's `installed_files` are independent

    - [x] 1.1.2. Write exploration test for `run_rm()` wrong-workspace match
      - In the same test file, write a test that creates a manifest with two local entries for the same bundle in different workspaces
      - Simulate the `run_rm()` lookup: `[e for e in manifest.entries if e.bundle_name == name and e.scope == scope]`
      - Assert: the lookup from workspace A should return only workspace A's entry (not workspace B's)
      - This test demonstrates that the current lookup returns both/wrong entries

    - [x] 1.1.3. Run tests on UNFIXED code
      - Run: `source .venv/bin/activate && pytest tests/test_manifest_multi_workspace_bug.py -v`
      - **EXPECTED OUTCOME**: Tests FAIL (this confirms the bug exists)
      - Document counterexamples found (e.g., "after two local installs of same bundle in different workspaces, manifest has 1 entry instead of 2")
      - Mark task complete when tests are written, run, and failure is documented

  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.3_

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Global and Same-Workspace Behavior Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs (global installs, same-workspace re-installs, global rm)
  - Write property-based tests capturing observed behavior patterns

  - [ ] 2.1. Write preservation tests

    - [x] 2.1.1. Create test file `tests/test_manifest_multi_workspace_preservation.py`
      - Import `Manifest`, `ManifestEntry` from `src/ksm/manifest.py`
      - Import `_update_manifest` from `src/ksm/installer.py`

    - [x] 2.1.2. Write global install preservation property
      - Use Hypothesis to generate bundle names and source registries
      - Observe: calling `_update_manifest()` with `scope="global"` uses `(bundle_name, scope)` matching
      - Observe: calling it twice with same `(bundle_name, "global")` updates in place (1 entry, not 2)
      - Write property: for all global-scoped installs, re-installing same bundle updates existing entry; `len(entries) == 1` after two calls with same bundle name

    - [x] 2.1.3. Write same-workspace re-install preservation property
      - Use Hypothesis to generate bundle names and workspace paths
      - Observe: calling `_update_manifest()` twice with same `(bundle_name, "local", workspace_path)` updates in place
      - Write property: for all same-workspace local re-installs, `len(entries) == 1` and entry is updated (not duplicated)

    - [x] 2.1.4. Write global rm lookup preservation property
      - Observe: `run_rm()` lookup for global scope matches by `(bundle_name, "global")` without workspace_path
      - Write property: for all global entries, lookup by `(bundle_name, "global")` returns the correct entry regardless of any workspace_path values in the manifest

    - [x] 2.1.5. Run preservation tests on UNFIXED code
      - Run: `source .venv/bin/activate && pytest tests/test_manifest_multi_workspace_preservation.py -v`
      - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
      - Mark task complete when tests are written, run, and passing on unfixed code

  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 3. Fix for manifest multi-workspace local entry overwrite

  - [ ] 3.1. Add `find_entries()` helper to `src/ksm/manifest.py`

    - [x] 3.1.1. Implement `find_entries()` function
      - Add function `find_entries(manifest, bundle_name, scope, workspace_path=None) -> list[ManifestEntry]`
      - When `scope == "local"` and `workspace_path is not None`, match on `(bundle_name, scope, workspace_path)`
      - When `scope == "global"` or `workspace_path is None`, match on `(bundle_name, scope)` only
      - This centralizes workspace-aware lookup logic
      - _Bug_Condition: isBugCondition(input) where scope == "local" AND manifest contains entry with same bundle_name and scope but different workspace_path_
      - _Expected_Behavior: find_entries returns only entries matching the specific workspace, not all entries with same (bundle_name, scope)_
      - _Preservation: Global lookups and same-workspace lookups unchanged_
      - _Requirements: 2.1, 2.3, 3.1, 3.2_

    - [x] 3.1.2. Write unit tests for `find_entries()`
      - Test: global scope returns match by `(bundle_name, scope)` only
      - Test: local scope with workspace_path returns only matching workspace entry
      - Test: local scope with `workspace_path=None` falls back to `(bundle_name, scope)` matching
      - Test: no match returns empty list
      - Test: multiple entries, only correct one returned
      - Run: `source .venv/bin/activate && pytest tests/test_manifest.py -v -k find_entries`

  - [ ] 3.2. Update `_update_manifest()` in `src/ksm/installer.py`

    - [x] 3.2.1. Refactor `_update_manifest()` to use `find_entries()`
      - Replace `existing = [e for e in manifest.entries if e.bundle_name == bundle_name and e.scope == scope]` with `existing = find_entries(manifest, bundle_name, scope, workspace_path)`
      - Import `find_entries` from `ksm.manifest`
      - No other changes needed — the rest of the function already handles update-in-place vs append correctly
      - _Bug_Condition: isBugCondition(input) where scope == "local" AND existing entry has different workspace_path_
      - _Expected_Behavior: new entry appended instead of overwriting existing entry from different workspace_
      - _Preservation: Global installs and same-workspace re-installs behave identically_
      - _Requirements: 2.1, 2.2, 3.1, 3.2_

  - [ ] 3.3. Update `run_rm()` in `src/ksm/commands/rm.py`

    - [x] 3.3.1. Refactor `run_rm()` lookup to use workspace-aware matching
      - Replace `matches = [e for e in manifest.entries if e.bundle_name == bundle_name and e.scope == scope]` with workspace-aware logic
      - For local scope: derive `workspace_path = str(target_local.parent.resolve())` and use `find_entries(manifest, bundle_name, scope, workspace_path)`
      - For global scope: use `find_entries(manifest, bundle_name, scope)` (no workspace_path)
      - Import `find_entries` from `ksm.manifest`
      - _Bug_Condition: isBugCondition(input) where scope == "local" AND rm from workspace A should not match workspace B's entry_
      - _Expected_Behavior: rm targets only the current workspace's entry_
      - _Preservation: Global rm unchanged_
      - _Requirements: 2.3, 3.4_

  - [x] 3.4. Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Multi-Workspace Local Install Independence
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run: `source .venv/bin/activate && pytest tests/test_manifest_multi_workspace_bug.py -v`
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.5. Verify preservation tests still pass
    - **Property 2: Preservation** - Global and Same-Workspace Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run: `source .venv/bin/activate && pytest tests/test_manifest_multi_workspace_preservation.py -v`
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all preservation tests still pass after fix
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Checkpoint - Ensure all tests pass
  - Run full test suite: `source .venv/bin/activate && pytest tests/ -v`
  - Ensure all tests pass, ask the user if questions arise
  - Run linting: `source .venv/bin/activate && black src/ksm/manifest.py src/ksm/installer.py src/ksm/commands/rm.py tests/test_manifest_multi_workspace_bug.py tests/test_manifest_multi_workspace_preservation.py`
  - Run type checking: `source .venv/bin/activate && flake8 src/ksm/manifest.py src/ksm/installer.py src/ksm/commands/rm.py`
  - Verify coverage: `source .venv/bin/activate && pytest --cov=src/ksm tests/ --cov-report=term-missing`
