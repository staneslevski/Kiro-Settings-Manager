# Implementation Plan

- [x] 1. Bug Condition Exploration

    - [x] 1.1 Write bug condition exploration tests

        - [x] 1.1.1 Write bug condition exploration test
          - **Property 1: Bug Condition** - Dispatch Functions Pass Paths Without .kiro Suffix
          - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
          - **DO NOT attempt to fix the test or the code when it fails**
          - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
          - **GOAL**: Surface counterexamples that demonstrate the bug exists
          - **Scoped PBT Approach**: For each dispatch function (`_dispatch_add`, `_dispatch_sync`, `_dispatch_rm`), scope the property to concrete cases: mock `Path.cwd()` and `Path.home()`, invoke the dispatch, and capture the `target_local` and `target_global` values passed to the command runner
          - Create test file `tests/test_dispatch_path_bug.py`
          - Mock `ksm.cli.ensure_ksm_dir`, `ksm.cli.load_registry_index`, `ksm.cli.load_manifest`
          - Mock `ksm.commands.add.run_add`, `ksm.commands.sync.run_sync`, `ksm.commands.rm.run_rm` to capture kwargs
          - Use Hypothesis to generate random `cwd` and `home` path segments via `st.from_regex(r"[a-z][a-z0-9]{0,9}", fullmatch=True)`
          - For each dispatch function, assert `target_local` ends with `.kiro` and `target_global` ends with `.kiro`
          - Patch `Path.cwd` and `Path.home` to return generated paths
          - Run test on UNFIXED code
          - **EXPECTED OUTCOME**: Test FAILS (this is correct — it proves the bug exists)
          - Document counterexamples found (e.g., `target_local = PosixPath('/projects/app')` missing `.kiro` suffix)
          - Mark task complete when test is written, run, and failure is documented
          - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 2. Preservation Testing

    - [x] 2.1 Write preservation property tests

        - [x] 2.1.1 Write preservation property tests (BEFORE implementing fix)
          - **Property 2: Preservation** - Non-Dispatch Commands and Module Interfaces Unchanged
          - **IMPORTANT**: Follow observation-first methodology
          - Observe behavior on UNFIXED code for non-dispatch commands and command module interfaces
          - Create test file `tests/test_dispatch_path_preservation.py`
          - **Non-dispatch command preservation**: Verify `_dispatch_ls`, `_dispatch_registry`, `_dispatch_init`, `_dispatch_info`, `_dispatch_search`, `_dispatch_completions` are not affected by the fix — mock their underlying command runners and confirm they are called with the same arguments as before
          - **Command module interface preservation**: Verify `run_add`, `run_sync`, `run_rm` receive `target_dir` and use it as-is — mock the command runners, invoke dispatch functions, and confirm the `target_local` / `target_global` kwargs are passed through without further `.kiro` appending by the command modules
          - Use Hypothesis to generate random scope flags (`-l`/`-g`) and bundle names for property-based coverage
          - Verify tests pass on UNFIXED code
          - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
          - Mark task complete when tests are written, run, and passing on unfixed code
          - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Fix Implementation

    - [x] 3.1 Implement the fix

        - [x] 3.1.1 Append `/ ".kiro"` to `target_local` and `target_global` in `_dispatch_add`
          - In `src/ksm/cli.py`, change `target_local=Path.cwd()` to `target_local=Path.cwd() / ".kiro"`
          - Change `target_global=Path.home()` to `target_global=Path.home() / ".kiro"`
          - _Bug_Condition: isBugCondition(input) where input.command IN ['add'] AND target_local = Path.cwd() [missing / ".kiro"]_
          - _Expected_Behavior: target_local == Path.cwd() / ".kiro" AND target_global == Path.home() / ".kiro"_
          - _Preservation: Command modules use target_dir as-is without modification_
          - _Requirements: 2.1, 2.2_

        - [x] 3.1.2 Append `/ ".kiro"` to `target_local` and `target_global` in `_dispatch_sync`
          - In `src/ksm/cli.py`, change `target_local=Path.cwd()` to `target_local=Path.cwd() / ".kiro"`
          - Change `target_global=Path.home()` to `target_global=Path.home() / ".kiro"`
          - _Bug_Condition: isBugCondition(input) where input.command IN ['sync'] AND target_local = Path.cwd() [missing / ".kiro"]_
          - _Expected_Behavior: target_local == Path.cwd() / ".kiro" AND target_global == Path.home() / ".kiro"_
          - _Preservation: Command modules use target_dir as-is without modification_
          - _Requirements: 2.3, 2.4_

        - [x] 3.1.3 Append `/ ".kiro"` to `target_local` and `target_global` in `_dispatch_rm`
          - In `src/ksm/cli.py`, change `target_local=Path.cwd()` to `target_local=Path.cwd() / ".kiro"`
          - Change `target_global=Path.home()` to `target_global=Path.home() / ".kiro"`
          - _Bug_Condition: isBugCondition(input) where input.command IN ['rm', 'remove'] AND target_local = Path.cwd() [missing / ".kiro"]_
          - _Expected_Behavior: target_local == Path.cwd() / ".kiro" AND target_global == Path.home() / ".kiro"_
          - _Preservation: Command modules use target_dir as-is without modification_
          - _Requirements: 2.5, 2.6_

    - [x] 3.2 Verify bug condition exploration test now passes

        - [x] 3.2.1 Re-run bug condition exploration test
          - **Property 1: Expected Behavior** - Dispatch Functions Pass Paths With .kiro Suffix
          - **IMPORTANT**: Re-run the SAME test from task 1.1.1 — do NOT write a new test
          - The test from task 1.1.1 encodes the expected behavior
          - When this test passes, it confirms the expected behavior is satisfied
          - Run `tests/test_dispatch_path_bug.py`
          - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
          - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

    - [x] 3.3 Verify preservation tests still pass

        - [x] 3.3.1 Re-run preservation property tests
          - **Property 2: Preservation** - Non-Dispatch Commands and Module Interfaces Unchanged
          - **IMPORTANT**: Re-run the SAME tests from task 2.1.1 — do NOT write new tests
          - Run `tests/test_dispatch_path_preservation.py`
          - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
          - Confirm all tests still pass after fix (no regressions)

- [x] 4. Checkpoint

    - [x] 4.1 Final validation

        - [x] 4.1.1 Ensure all tests pass
          - Run the full test suite to confirm no regressions
          - Ensure all tests pass, ask the user if questions arise
