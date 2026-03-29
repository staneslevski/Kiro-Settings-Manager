# Implementation Plan

- [x] 1. Explore bug condition

    - [x] 1.1 Write bug condition exploration tests

        - [x] 1.1.1 Write bug condition exploration test for add selector registry column shift
          - **Property 1: Bug Condition** - Registry Column Misalignment in Add Selector
          - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
          - **DO NOT attempt to fix the test or the code when it fails**
          - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
          - **GOAL**: Surface counterexamples that demonstrate the registry column shifts when `[installed]` badge is present on some rows but not others
          - **Scoped PBT Approach**: Generate bundles where at least one is installed and at least one is not; both have registry names
          - Test: for all such bundle sets, strip ANSI from rendered lines, find the start position of the registry name column on each bundle row — assert all positions are equal
          - Bug condition from design: `isBugCondition(rows)` returns true when `SIZE(col_positions) > 1` for the registry column
          - Expected behavior: all registry columns start at the same horizontal position regardless of badge presence
          - Run test on UNFIXED code — expect FAILURE (confirms bug exists)
          - Document counterexamples found (e.g., "registry 'default' starts at col 22 on installed row vs col 9 on non-installed row")
          - Mark task complete when test is written, run, and failure is documented
          - _Requirements: 1.1, 1.2, 2.1, 2.2_

        - [x] 1.1.2 Write bug condition exploration test for removal selector scope column width
          - **Property 1: Bug Condition** - Scope Column Width Inconsistency in Removal Selector
          - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
          - **DO NOT attempt to fix the test or the code when it fails**
          - **Scoped PBT Approach**: Generate entries with mixed scope values ("local" and "global") that have different string widths
          - Test: for all such entry sets, strip ANSI from rendered lines, measure the width of the scope field (from `[` to character after `]`) — assert all scope fields occupy the same width
          - Run test on UNFIXED code — expect FAILURE (confirms scope fields have different widths)
          - Document counterexamples found (e.g., "`[global]` is 8 chars but `[local]` is 7 chars")
          - _Requirements: 1.5, 2.5_

        - [x] 1.1.3 Write bug condition exploration test for TUI add selector registry alignment
          - **Property 1: Bug Condition** - TUI Registry Column Misalignment
          - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
          - **DO NOT attempt to fix the test or the code when it fails**
          - **Scoped PBT Approach**: Build Rich Text labels via `BundleSelectorApp._refresh_options` logic with mixed installed/not-installed bundles
          - Test: extract plain text from each Rich Text label, find registry name start position — assert all positions are equal
          - Since `_refresh_options` requires a running Textual app, test the label-building logic directly by simulating the same Rich Text construction used in the method
          - Run test on UNFIXED code — expect FAILURE
          - _Requirements: 1.3, 1.4, 2.3, 2.4_

        - [x] 1.1.4 Write bug condition exploration test for TUI removal selector scope alignment
          - **Property 1: Bug Condition** - TUI Scope Column Width Inconsistency
          - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
          - **Scoped PBT Approach**: Build Rich Text labels via `RemovalSelectorApp._refresh_options` logic with mixed scope values
          - Test: extract plain text from each label, measure scope field width — assert all equal
          - Run test on UNFIXED code — expect FAILURE
          - _Requirements: 1.6, 2.6_

- [x] 2. Preserve existing behavior

    - [x] 2.1 Write preservation property tests

        - [x] 2.1.1 Write preservation test for add selector sorting, filtering, and prefix behavior
          - **Property 2: Preservation** - Add Selector Core Behavior Unchanged
          - **IMPORTANT**: Follow observation-first methodology
          - Observe on UNFIXED code: bundles are sorted alphabetically (case-insensitive) by name then registry, filter narrows list by case-insensitive substring, selected line has `>` prefix, `[✓]`/`[ ]` indicators render correctly
          - Write property-based test: for all bundle sets with random installed subsets and optional filter text, verify sorting order, filter correctness, prefix on selected line, and multi-select indicators are unchanged
          - Verify test passes on UNFIXED code
          - _Requirements: 3.1, 3.2, 3.3, 3.5, 3.6_

        - [x] 2.1.2 Write preservation test for removal selector sorting and scope content
          - **Property 2: Preservation** - Removal Selector Core Behavior Unchanged
          - **IMPORTANT**: Follow observation-first methodology
          - Observe on UNFIXED code: entries sorted alphabetically by bundle name, scope label content `[global]`/`[local]` is correct, multi-select indicators work
          - Write property-based test: for all entry sets with random scopes, verify sort order, scope label presence, and multi-select indicators
          - Verify test passes on UNFIXED code
          - _Requirements: 3.4, 3.7_

        - [x] 2.1.3 Write preservation test for existing alignment tests
          - **Property 2: Preservation** - Existing Alignment Tests Still Pass
          - **IMPORTANT**: This is a verification step, not a new test
          - Run existing tests: `test_render_add_selector_installed_column_aligned`, `test_render_add_selector_columns_aligned`, `test_render_removal_selector_columns_aligned`
          - Verify all three pass on UNFIXED code (they test name-column alignment which already works)
          - _Requirements: 3.7_

- [x] 3. Fix column alignment

    - [x] 3.1 Implement the fix in selector.py and tui.py

        - [x] 3.1.1 Fix `render_add_selector` in `src/ksm/selector.py`
          - Compute `badge_width = len(" [installed]")` if any bundle is installed, else 0
          - Pad the badge field to `badge_width` on every row: installed rows get `dim(" [installed]", ...)`, non-installed rows get `" " * badge_width`
          - This ensures `reg_col` always starts at the same horizontal position
          - Consider using `_align_columns()` from `color.py` if it simplifies the implementation
          - _Bug_Condition: isBugCondition(rows) where some rows have badge and some don't_
          - _Expected_Behavior: all registry columns start at identical horizontal positions_
          - _Preservation: sorting, filtering, multi-select, highlighting unchanged_
          - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.3, 3.5, 3.6_

        - [x] 3.1.2 Fix `render_removal_selector` in `src/ksm/selector.py`
          - Compute `max_scope = max(len(f"[{e.scope}]") for e in sorted_entries)` before the loop
          - Pad each scope label to `max_scope` width using ANSI-aware length calculation
          - _Bug_Condition: isBugCondition(rows) where scope labels have different widths_
          - _Expected_Behavior: scope fields occupy identical width across all rows_
          - _Preservation: sorting, scope content, multi-select unchanged_
          - _Requirements: 2.5, 3.4, 3.7_

        - [x] 3.1.3 Fix `BundleSelectorApp._refresh_options` in `src/ksm/tui.py`
          - Compute `badge_width = len(" [installed]")` if any bundle in `filtered_items` is installed, else 0
          - Always append a badge field of `badge_width` characters to the Rich Text label: installed bundles get `" [installed]"` padded to width, non-installed get spaces
          - _Bug_Condition: Rich Text labels have registry at different positions based on badge presence_
          - _Expected_Behavior: registry name starts at same position in all labels_
          - _Requirements: 2.3, 2.4_

        - [x] 3.1.4 Fix `RemovalSelectorApp._refresh_options` in `src/ksm/tui.py`
          - Compute `max_scope = max(len(f"[{e.scope}]") for e in filtered_entries)` before the loop
          - Pad each scope label string to `max_scope` width in the Rich Text label
          - _Bug_Condition: Rich Text labels have scope fields of different widths_
          - _Expected_Behavior: scope fields occupy identical width in all labels_
          - _Requirements: 2.6_

    - [x] 3.2 Verify bug condition exploration tests now pass

        - [x] 3.2.1 Verify add selector registry alignment test passes
          - **Property 1: Expected Behavior** - Registry Column Alignment in Add Selector
          - **IMPORTANT**: Re-run the SAME test from task 1.1.1 — do NOT write a new test
          - Run bug condition exploration test from step 1.1.1
          - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
          - _Requirements: 2.1, 2.2_

        - [x] 3.2.2 Verify removal selector scope alignment test passes
          - **Property 1: Expected Behavior** - Scope Column Alignment in Removal Selector
          - **IMPORTANT**: Re-run the SAME test from task 1.1.2 — do NOT write a new test
          - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
          - _Requirements: 2.5_

        - [x] 3.2.3 Verify TUI add selector registry alignment test passes
          - **Property 1: Expected Behavior** - TUI Registry Column Alignment
          - **IMPORTANT**: Re-run the SAME test from task 1.1.3 — do NOT write a new test
          - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
          - _Requirements: 2.3, 2.4_

        - [x] 3.2.4 Verify TUI removal selector scope alignment test passes
          - **Property 1: Expected Behavior** - TUI Scope Column Alignment
          - **IMPORTANT**: Re-run the SAME test from task 1.1.4 — do NOT write a new test
          - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
          - _Requirements: 2.6_

    - [x] 3.3 Verify preservation tests still pass

        - [x] 3.3.1 Verify add selector preservation test still passes
          - **Property 2: Preservation** - Add Selector Core Behavior Unchanged
          - **IMPORTANT**: Re-run the SAME test from task 2.1.1 — do NOT write a new test
          - **EXPECTED OUTCOME**: Test PASSES (confirms no regressions)

        - [x] 3.3.2 Verify removal selector preservation test still passes
          - **Property 2: Preservation** - Removal Selector Core Behavior Unchanged
          - **IMPORTANT**: Re-run the SAME test from task 2.1.2 — do NOT write a new test
          - **EXPECTED OUTCOME**: Test PASSES (confirms no regressions)

        - [x] 3.3.3 Verify existing alignment tests still pass
          - **Property 2: Preservation** - Existing Alignment Tests Still Pass
          - **IMPORTANT**: Re-run the SAME verification from task 2.1.3 — do NOT write new tests
          - **EXPECTED OUTCOME**: All three existing alignment tests PASS (confirms no regressions)
          - _Requirements: 3.7_

- [x] 4. Checkpoint

    - [x] 4.1 Final validation

        - [x] 4.1.1 Run full test suite and confirm all tests pass
          - Run `source .venv/bin/activate && pytest tests/test_selector.py -v`
          - Ensure all existing tests plus new property tests pass
          - Ensure no warnings or errors
          - Ask the user if questions arise
