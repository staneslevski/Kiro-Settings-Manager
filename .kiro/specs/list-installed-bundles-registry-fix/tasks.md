# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Multi-workspace local removal removes all entries
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to concrete failing cases: same `bundle_name`, same `scope="local"`, two or more distinct `workspace_path` values
  - Write a property-based test (Hypothesis) that:
    - Generates a manifest with 2+ local-scoped entries sharing the same `bundle_name` but with different `workspace_path` values
    - Calls `remove_bundle()` for one entry
    - Asserts the removed entry is gone from `manifest.entries`
    - Asserts all other entries with different `workspace_path` values remain in `manifest.entries`
  - Bug Condition from design: `isBugCondition(entry, manifest)` returns true when `entry.scope == "local"` AND `entry.workspace_path IS NOT None` AND there exists at least one other entry with the same `bundle_name` and `scope` but different `workspace_path`
  - Expected behavior assertions: after `remove_bundle(entry, target_dir, manifest)`, only the entry matching `bundle_name + scope + workspace_path` is removed; other entries with different `workspace_path` remain
  - Create test files on disk under a temp directory so `remove_bundle()` can delete them
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found: e.g. "After removing entry for `/ws/a`, manifest.entries is empty instead of containing the `/ws/b` entry"
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 2.1, 2.2_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Single-workspace and global removal unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs:
    - Observe: single local-scoped entry removal deletes the entry and files
    - Observe: global-scoped entry removal deletes the entry and files
    - Observe: removal of one bundle preserves other unrelated bundle entries
    - Observe: entries with `workspace_path=None` (legacy) are removed correctly
  - Write a property-based test (Hypothesis) that:
    - Generates manifests where the bug condition does NOT hold (single local entry, global entry, or `workspace_path=None`)
    - Calls `remove_bundle()` and asserts:
      - The target entry is removed from `manifest.entries`
      - All other entries remain unchanged
      - `RemovalResult` contains correct `removed_files` and `skipped_files`
    - Uses strategies for `bundle_name`, `scope` (sampled from `["local", "global"]`), and `workspace_path` (either `None` or a generated path)
  - Preservation Requirements from design: global removal matches on `bundle_name` + `scope`; single local removal works; file deletion and cleanup unchanged; other entries preserved
  - Verify tests pass on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Fix for multi-workspace local bundle removal

  - [x] 3.1 Implement the fix
    - Modify the list comprehension in `remove_bundle()` in `src/ksm/remover.py` (lines 62-65)
    - Add `workspace_path` comparison to the filter predicate for local-scoped entries with non-`None` `workspace_path`
    - The filter should keep entries that do NOT match on all three fields (`bundle_name`, `scope`, and `workspace_path`) when `entry.workspace_path` is not `None`
    - When `entry.workspace_path` is `None` (global scope or legacy local entries), fall back to current behavior matching on `bundle_name` and `scope` only
    - _Bug_Condition: isBugCondition(entry, manifest) where entry.scope == "local" AND entry.workspace_path IS NOT None AND other entries exist with same bundle_name/scope but different workspace_path_
    - _Expected_Behavior: After removal, only the entry matching bundle_name + scope + workspace_path is removed; entries for other workspaces remain_
    - _Preservation: Global removal, single-workspace local removal, legacy None workspace_path removal, file deletion, and directory cleanup all unchanged_
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 3.3, 3.4_

  - [x] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Multi-workspace local removal preserves other workspaces
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2_

  - [x] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Single-workspace and global removal unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Checkpoint - Ensure all tests pass
  - Run the full test suite (`pytest tests/`) to verify no regressions
  - Run linting (`black`, `flake8`, `mypy`) on changed files
  - Ensure all tests pass, ask the user if questions arise
