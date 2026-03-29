# Implementation Plan

- [ ] 1. Explore the bug condition

    - [ ] 1.1 Write bug condition exploration test

        - [x] 1.1.1 Write bug condition exploration test
          - **Property 1: Bug Condition** - Local Bundles Shown From Other Workspaces
          - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
          - **DO NOT attempt to fix the test or the code when it fails**
          - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
          - **GOAL**: Surface counterexamples that demonstrate `run_ls()` shows local entries from other workspaces
          - **Scoped PBT Approach**: Generate manifests containing local entries with varying `workspace_path` values (including None and paths different from cwd). Assert that `run_ls()` output only contains local entries whose `workspace_path` matches the resolved cwd.
          - Bug Condition from design: `isBugCondition(input)` — `input.command IN ["list", "ls"] AND input.all_flag == false AND EXISTS entry IN manifest.entries WHERE entry.scope == "local" AND (entry.workspace_path IS NULL OR resolve(entry.workspace_path) != resolve(input.cwd))`
          - Create a manifest with local entries for workspace-a (`/tmp/project-a`) and workspace-b (`/tmp/project-b`), call `run_ls()` with cwd context of workspace-a
          - On unfixed code: both workspace-a and workspace-b local entries appear (test FAILS — confirms bug)
          - Also test `--scope local` variant: all local entries from all workspaces shown (test FAILS — confirms bug)
          - Run test on UNFIXED code
          - **EXPECTED OUTCOME**: Test FAILS (this is correct — it proves the bug exists)
          - Document counterexamples found (e.g., "run_ls() returns 'aws' from workspace-b when called from workspace-a")
          - Mark task complete when test is written, run, and failure is documented
          - _Requirements: 1.1, 1.2, 2.1, 2.2_


- [ ] 2. Preserve existing behavior

    - [ ] 2.1 Write preservation property tests (BEFORE implementing fix)

        - [x] 2.1.1 Write preservation property tests
          - **Property 2: Preservation** - Global Listing and Formatting Unchanged
          - **IMPORTANT**: Follow observation-first methodology
          - **Step 1 — Observe** on UNFIXED code:
            - Observe: `run_ls()` with global-only manifest shows all global bundles grouped under "Global bundles:" header
            - Observe: `run_ls()` with `--scope global` shows only global entries, no local entries
            - Observe: `run_ls()` with `--format json` produces valid JSON with fields `bundle_name`, `scope`, `source_registry`, `installed_files`, `installed_at`, `updated_at`
            - Observe: `run_ls()` with `-v` shows installed file paths indented under each bundle
            - Observe: `run_ls()` text output groups by scope with bold headers, column alignment, and relative timestamps
          - **Step 2 — Write property-based tests** capturing observed behavior:
            - Property: for all global-only manifests (no local entries), `run_ls()` output contains every global bundle name and "Global bundles:" header
            - Property: for all manifests with `--scope global`, output contains only global entries and no local entry names (where names are unique)
            - Property: for all manifests with `--format json`, output is valid JSON array where each item has all required fields
            - Property: for all manifests with `-v`, every `installed_files` path appears in output
            - Property: for all manifests with mixed scopes, text output contains scope headers for present scopes
          - **Step 3 — Verify** tests PASS on UNFIXED code
          - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
          - Mark task complete when tests are written, run, and passing on unfixed code
          - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_


- [ ] 3. Fix `ksm list` to scope local bundles by workspace

    - [ ] 3.1 Add `workspace_path` field to `ManifestEntry` and update serialization

        - [x] 3.1.1 Add `workspace_path: str | None = None` field to `ManifestEntry` dataclass in `src/ksm/manifest.py`
          - Add the field after `version` with default `None`
          - _Bug_Condition: isBugCondition(input) — ManifestEntry has no workspace_path field, so run_ls() cannot filter_
          - _Expected_Behavior: ManifestEntry stores workspace_path for local entries_
          - _Requirements: 1.3, 2.3_

        - [x] 3.1.2 Update `_entry_to_dict()` in `src/ksm/manifest.py` to include `workspace_path` when not None
          - Serialize `workspace_path` alongside `version` (only when not None)
          - _Requirements: 2.3, 3.3_

        - [x] 3.1.3 Update `_dict_to_entry()` in `src/ksm/manifest.py` to read `workspace_path` from dict
          - Use `.get("workspace_path")` with default None for backward compatibility with legacy manifests
          - _Requirements: 2.3, 2.5_

        - [x] 3.1.4 Write tests for ManifestEntry serialization/deserialization with `workspace_path`
          - Test round-trip: entry with workspace_path serializes and deserializes correctly
          - Test backward compat: entry dict without workspace_path deserializes with workspace_path=None
          - Test omission: entry with workspace_path=None does not include workspace_path in serialized dict
          - _Requirements: 2.3, 3.3_

    - [ ] 3.2 Update `install_bundle()` to record workspace path

        - [x] 3.2.1 Add `workspace_path: str | None = None` parameter to `_update_manifest()` in `src/ksm/installer.py`
          - Set `workspace_path` on both new entries and existing entry updates
          - _Bug_Condition: _update_manifest() creates entries without workspace association_
          - _Expected_Behavior: _update_manifest() records workspace_path when provided_
          - _Preservation: Global entries continue to have workspace_path=None_
          - _Requirements: 1.3, 2.3, 3.5_

        - [x] 3.2.2 Update `install_bundle()` and `_install_dot_selection()` in `src/ksm/installer.py` to pass workspace_path
          - When `scope="local"`, resolve workspace path as `str(target_dir.parent.resolve())`
          - When `scope="global"`, pass `None`
          - _Requirements: 2.3, 3.5_

        - [x] 3.2.3 Write tests for `_update_manifest()` workspace_path recording
          - Test: local scope install records resolved workspace_path on new entry
          - Test: local scope install updates workspace_path on existing entry
          - Test: global scope install leaves workspace_path as None
          - _Requirements: 2.3, 3.5_

    - [ ] 3.3 Filter local entries by workspace in `run_ls()`

        - [x] 3.3.1 Add `workspace_path: str | None = None` parameter to `run_ls()` in `src/ksm/commands/ls.py`
          - Default to `None`; when None, resolve from `Path.cwd()` at call time
          - Read `all_flag` from `args` (getattr with default False)
          - _Requirements: 2.1, 2.2_

        - [x] 3.3.2 Implement workspace filtering logic in `run_ls()`
          - After scope filter, when `all_flag` is False: keep only entries where `entry.scope == "global"` OR (`entry.scope == "local"` AND `entry.workspace_path == resolved_workspace_path`)
          - When `all_flag` is True: skip workspace filtering (show all entries)
          - _Bug_Condition: run_ls() applies only scope filter, never checks workspace_path_
          - _Expected_Behavior: run_ls() excludes local entries from other workspaces unless --all_
          - _Preservation: Global entries always pass through unfiltered_
          - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.4, 2.6, 3.1, 3.2_

        - [x] 3.3.3 Update `_entry_to_dict()` in `src/ksm/commands/ls.py` to include `workspace_path`
          - Include `workspace_path` in JSON output when not None
          - _Requirements: 2.4, 3.3_

        - [x] 3.3.4 Write tests for workspace filtering in `run_ls()`
          - Test: default list excludes local entries from other workspaces
          - Test: default list includes local entries matching current workspace
          - Test: `--scope local` only shows current workspace's local entries
          - Test: `--all` shows local entries from all workspaces
          - Test: global entries always shown regardless of workspace
          - Test: entries with workspace_path=None excluded from default list
          - Test: JSON output includes workspace_path for local entries
          - _Requirements: 2.1, 2.2, 2.4, 2.6, 3.1, 3.3_

    - [ ] 3.4 Add `--all` flag to CLI and pass workspace context

        - [x] 3.4.1 Add `--all` argument to `_add_list_args()` in `src/ksm/cli.py`
          - Add `parser.add_argument("--all", dest="show_all", action="store_true", help="Show bundles from all workspaces")`
          - Use `dest="show_all"` to avoid conflict with Python builtin
          - _Requirements: 1.4, 2.4_

        - [x] 3.4.2 Update `_dispatch_ls()` in `src/ksm/cli.py` to pass workspace_path to `run_ls()`
          - Pass `workspace_path=str(Path.cwd().resolve())` to `run_ls()`
          - _Requirements: 2.1, 2.2_

        - [x] 3.4.3 Write tests for `--all` flag parsing and dispatch
          - Test: `--all` flag is accepted by list/ls parser
          - Test: `_dispatch_ls()` passes workspace_path to `run_ls()`
          - _Requirements: 1.4, 2.4_

    - [ ] 3.5 Add backfill function for legacy entries

        - [x] 3.5.1 Implement `backfill_workspace_paths()` in `src/ksm/manifest.py`
          - Scan entries with `scope="local"` and `workspace_path is None`
          - For each, check if any `installed_files` exist under `workspace_dir / ".kiro/"`
          - If match found, set `workspace_path` to `str(workspace_dir.resolve())`
          - Return True if any entries were updated (caller should persist)
          - _Requirements: 2.5, 2.6_

        - [x] 3.5.2 Call `backfill_workspace_paths()` from `_dispatch_ls()` before calling `run_ls()`
          - If backfill returns True, save manifest with `save_manifest()`
          - _Requirements: 2.5_

        - [x] 3.5.3 Write tests for `backfill_workspace_paths()`
          - Test: legacy entry with matching files gets workspace_path set
          - Test: legacy entry with no matching files left unchanged
          - Test: entry already having workspace_path is not modified
          - Test: global entries are not touched
          - Test: returns True when entries updated, False otherwise
          - _Requirements: 2.5, 2.6_

    - [ ] 3.6 Verify bug condition exploration test now passes

        - [x] 3.6.1 Re-run bug condition exploration test from task 1.1.1
          - **Property 1: Expected Behavior** - Local Bundles Filtered By Workspace
          - **IMPORTANT**: Re-run the SAME test from task 1.1.1 — do NOT write a new test
          - The test from task 1.1.1 encodes the expected behavior
          - When this test passes, it confirms the expected behavior is satisfied
          - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
          - _Requirements: 2.1, 2.2_

    - [ ] 3.7 Verify preservation tests still pass

        - [x] 3.7.1 Re-run preservation property tests from task 2.1.1
          - **Property 2: Preservation** - Global Listing and Formatting Unchanged
          - **IMPORTANT**: Re-run the SAME tests from task 2.1.1 — do NOT write new tests
          - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
          - Confirm all preservation tests still pass after fix
          - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [ ] 4. Checkpoint

    - [ ] 4.1 Final validation

        - [x] 4.1.1 Ensure all tests pass
          - Run full test suite: `source .venv/bin/activate && pytest tests/ -x`
          - Verify bug condition test (Property 1) passes
          - Verify preservation tests (Property 2) pass
          - Verify all new unit tests pass
          - Verify all existing tests pass (no regressions)
          - Check coverage meets ≥95% for changed files
          - Ask the user if questions arise
