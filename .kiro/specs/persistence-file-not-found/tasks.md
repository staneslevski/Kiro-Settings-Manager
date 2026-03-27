# Implementation Plan

- [x] 1. Explore and confirm the bug

    - [x] 1.1 Write bug condition exploration test

        - [x] 1.1.1 Write bug condition exploration test
          - **Property 1: Bug Condition** - Missing registries.json raises FileNotFoundError
          - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
          - **DO NOT attempt to fix the test or the code when it fails**
          - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
          - **GOAL**: Surface counterexamples that demonstrate the bug exists
          - **Scoped PBT Approach**: Scope the property to the concrete failing case: `load_registry_index(nonexistent_path)` without `default_registry_path`
          - Create `tests/test_persistence_file_not_found.py`
          - Test that calling `load_registry_index(path)` without `default_registry_path` when `registries.json` does not exist raises `FileNotFoundError` (from Bug Condition in design: `isBugCondition` — file missing AND no `default_registry_path`)
          - Write a Hypothesis property test generating arbitrary non-existent paths within `tmp_path`, asserting that `load_registry_index(path, default_registry_path=some_valid_dir)` succeeds (returns a `RegistryIndex` with a default entry) — this assertion encodes the Expected Behavior
          - Run test on UNFIXED code
          - **EXPECTED OUTCOME**: The property assertion FAILS because the six dispatch functions don't pass `default_registry_path` — but the direct `load_registry_index` call with `default_registry_path` should succeed (confirming the fix mechanism works, the bug is in `cli.py` not passing the argument)
          - Document counterexamples: `load_registry_index(missing_path)` raises `FileNotFoundError` when `default_registry_path` is `None`
          - Mark task complete when test is written, run, and failure is documented
          - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

- [x] 2. Preserve existing behavior

    - [x] 2.1 Write preservation property tests (BEFORE implementing fix)

        - [x] 2.1.1 Write preservation property tests
          - **Property 2: Preservation** - Existing registries.json loads unchanged
          - **IMPORTANT**: Follow observation-first methodology
          - Observe: `load_registry_index(existing_path)` returns the saved `RegistryIndex` on unfixed code
          - Observe: `load_registry_index(existing_path, default_registry_path=X)` returns the same result — the `default_registry_path` argument is ignored when the file exists
          - Observe: save/load round-trip preserves all registry entry fields identically
          - Write Hypothesis property test: for all valid `RegistryIndex` instances, `save_registry_index` then `load_registry_index(path, default_registry_path=any_dir)` returns identical data (from Preservation Requirements in design)
          - Write Hypothesis property test: for all valid `RegistryIndex` instances, `load_registry_index` with and without `default_registry_path` returns identical results when file exists
          - Verify tests pass on UNFIXED code
          - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
          - Mark task complete when tests are written, run, and passing on unfixed code
          - _Requirements: 3.1, 3.3, 3.4_

- [x] 3. Implement the fix

    - [x] 3.1 Add CONFIG_BUNDLES_DIR constant and update dispatch calls

        - [x] 3.1.1 Add `CONFIG_BUNDLES_DIR` constant to `src/ksm/persistence.py`
          - Add `CONFIG_BUNDLES_DIR: Path = Path(__file__).resolve().parent.parent.parent / "config_bundles"` after existing constants
          - _Bug_Condition: isBugCondition(input) where NOT registries_file_exists AND command IN [add, sync, add-registry, registry, info, search]_
          - _Expected_Behavior: auto-create registries.json with default entry pointing to config_bundles/_
          - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

        - [x] 3.1.2 Update `src/ksm/cli.py` imports to include `CONFIG_BUNDLES_DIR`
          - Add `CONFIG_BUNDLES_DIR` to the existing import from `ksm.persistence`
          - _Requirements: 2.1_

        - [x] 3.1.3 Pass `default_registry_path=CONFIG_BUNDLES_DIR` to all six `load_registry_index` calls
          - Update `_dispatch_add` call
          - Update `_dispatch_sync` call
          - Update `_dispatch_add_registry` call
          - Update `_dispatch_registry` call
          - Update `_dispatch_info` call
          - Update `_dispatch_search` call
          - Do NOT change `_dispatch_init` (it has its own try/except fallback)
          - _Bug_Condition: isBugCondition(input) from design_
          - _Expected_Behavior: expectedBehavior(result) — no FileNotFoundError, auto-creates registries.json_
          - _Preservation: _dispatch_init unchanged, existing files load unchanged_
          - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2_

    - [x] 3.2 Verify bug condition exploration test now passes

        - [x] 3.2.1 Re-run bug condition exploration test
          - **Property 1: Expected Behavior** - Missing registries.json auto-creates default registry
          - **IMPORTANT**: Re-run the SAME test from task 1.1.1 — do NOT write a new test
          - The test from task 1.1.1 encodes the expected behavior
          - When this test passes, it confirms the expected behavior is satisfied
          - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
          - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

    - [x] 3.3 Verify preservation tests still pass

        - [x] 3.3.1 Re-run preservation property tests
          - **Property 2: Preservation** - Existing registries.json loads unchanged
          - **IMPORTANT**: Re-run the SAME tests from task 2.1.1 — do NOT write new tests
          - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
          - Confirm all preservation tests still pass after fix
          - _Requirements: 3.1, 3.3, 3.4_

- [x] 4. Checkpoint

    - [x] 4.1 Final validation

        - [x] 4.1.1 Run full test suite and verify ≥95% coverage
          - Run `pytest --cov=ksm --cov-report=term-missing tests/`
          - Verify all tests pass
          - Verify ≥95% coverage on `src/ksm/persistence.py` and `src/ksm/cli.py`
          - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2, 3.3, 3.4_

        - [x] 4.1.2 Run linting (black, flake8, mypy)
          - Run `black --check src/ tests/`
          - Run `flake8 src/ tests/`
          - Run `mypy src/ tests/`
          - Fix any issues found
          - _Requirements: all_

        - [x] 4.1.3 Ensure all tests pass, ask the user if questions arise
