# Implementation Plan: Bundle Registry Grouping

## Overview

Replace flat alphabetical bundle listing with registry-grouped output across all bundle listing UIs. A single `group_bundles_by_registry()` function in `selector.py` drives all rendering paths. Changes are localised to `src/ksm/selector.py`, `src/ksm/tui.py`, `tests/test_selector.py`, and `tests/test_tui.py`.

## Tasks

- [x] 1. Core grouping function

    - [x] 1.1 Implement `group_bundles_by_registry` in `selector.py`

        - [x] 1.1.1 Add `group_bundles_by_registry(bundles: list[BundleInfo]) -> dict[str, list[BundleInfo]]` to `src/ksm/selector.py`
            - Sort keys case-insensitively, empty-string key last
            - Sort bundles within each group case-insensitively by name
            - Return insertion-ordered dict
            - _Requirements: 6.1, 6.2, 6.3, 6.4_

        - [x] 1.1.2 Write property test for grouping sort order (Property 1)
            - **Property 1: Grouping function produces sorted groups with sorted bundles**
            - **Validates: Requirements 1.2, 1.3, 6.1, 6.2, 6.3**
            - Add to `tests/test_selector.py`

        - [x] 1.1.3 Write property test for empty registry name (Property 2)
            - **Property 2: Empty registry name sorts last**
            - **Validates: Requirements 6.4**
            - Add to `tests/test_selector.py`

        - [x] 1.1.4 Write unit tests for `group_bundles_by_registry` edge cases
            - Empty bundle list returns empty dict
            - Single registry returns single-entry dict with header (Req 1.4)
            - All bundles from same registry grouped together
            - _Requirements: 1.4, 6.1, 6.2, 6.3, 6.4_

    - [x] 1.2 Checkpoint
        - Ensure all tests pass, ask the user if questions arise.

- [x] 2. Refactor `render_add_selector` for grouped output

    - [x] 2.1 Update `render_add_selector` in `selector.py`

        - [x] 2.1.1 Refactor `render_add_selector` to use `group_bundles_by_registry`
            - Replace flat `sorted()` with `group_bundles_by_registry()`
            - Insert dimmed registry name header line before each group
            - When `filter_text` provided, filter first then group; omit empty groups
            - `selected` index and `multi_selected` reference flattened bundle positions (excluding headers)
            - _Requirements: 1.1, 1.2, 1.3, 4.1, 4.2, 4.3, 4.4_

        - [x] 2.1.2 Write property test for group headers in rendered output (Property 3)
            - **Property 3: Rendered output contains a group header for each registry**
            - **Validates: Requirements 1.1, 4.1**
            - Add to `tests/test_selector.py`

        - [x] 2.1.3 Write property test for filtering hides empty groups (Property 4)
            - **Property 4: Filtering hides empty groups**
            - **Validates: Requirements 2.4, 4.4**
            - Add to `tests/test_selector.py`

        - [x] 2.1.4 Write unit tests for `render_add_selector` grouped output
            - Single registry shows group header (Req 1.4)
            - Multiple registries show sorted group headers
            - Filter matches nothing shows no group headers (Req 5.4)
            - Installed label still appears correctly within groups
            - _Requirements: 1.1, 1.2, 1.3, 4.1, 4.2, 4.3, 4.4, 5.4_

    - [x] 2.2 Update existing `render_add_selector` tests
        - [x] 2.2.1 Fix existing tests in `tests/test_selector.py` that assume flat output
            - Update assertions to account for group header lines
            - Ensure all existing tests pass with new grouped format
            - _Requirements: 5.3, 5.4_

    - [x] 2.3 Checkpoint
        - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Refactor numbered-list fallback for grouped output

    - [x] 3.1 Update `interactive_select` fallback path

        - [x] 3.1.1 Refactor `interactive_select` numbered-list fallback to use `group_bundles_by_registry`
            - Print text header for each registry group
            - Use continuous 1-based numbering across all groups
            - _Requirements: 3.1, 3.2, 3.3, 3.4_

        - [x] 3.1.2 Write property test for continuous numbering (Property 5)
            - **Property 5: Continuous numbering across groups in fallback**
            - **Validates: Requirements 3.4**
            - Add to `tests/test_selector.py`

        - [x] 3.1.3 Write unit tests for numbered-list fallback grouping
            - Multiple registries show group headers in stderr output
            - Continuous numbering across groups
            - Single registry shows header
            - _Requirements: 3.1, 3.2, 3.3, 3.4_

    - [x] 3.2 Checkpoint
        - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Refactor TUI `BundleSelectorApp` for grouped output

    - [x] 4.1 Update `BundleSelectorApp._build_display_items` in `tui.py`

        - [x] 4.1.1 Refactor `_build_display_items` to use `group_bundles_by_registry`
            - Insert non-selectable disabled `Option` separator rows for registry headers
            - Track mapping from display-row index to bundle index for selection/multi-select
            - On filter change, re-group filtered results and hide empty groups
            - _Requirements: 2.1, 2.2, 2.3, 2.4_

        - [x] 4.1.2 Update `_refresh_options`, `on_input_changed`, `_confirm_selection`, and key handlers
            - Skip separator rows during navigation and selection
            - `multi_selected` indices reference bundle positions, not display rows
            - _Requirements: 2.2, 5.2_

        - [x] 4.1.3 Write property test for selection returns correct qualified name (Property 6)
            - **Property 6: Selection from grouped list returns correct qualified name**
            - **Validates: Requirements 5.1**
            - Add to `tests/test_selector.py` (tests the `_qualified_name` logic with grouped data)

        - [x] 4.1.4 Write unit tests for TUI grouped display
            - Separator rows are non-selectable (Req 2.2)
            - Multi-select across groups tracks correct indices (Req 5.2)
            - Filter preserves grouping and hides empty groups (Req 2.4)
            - Single registry shows separator header (Req 1.4)
            - Add to `tests/test_tui.py`
            - _Requirements: 2.1, 2.2, 2.3, 2.4, 5.2_

    - [x] 4.2 Update existing TUI tests
        - [x] 4.2.1 Fix existing tests in `tests/test_tui.py` that assume flat display
            - Update assertions to account for separator rows
            - Ensure all existing TUI tests pass with grouped format
            - _Requirements: 5.2, 5.3_

    - [x] 4.3 Checkpoint
        - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Integration and final verification

    - [x] 5.1 Wire everything together

        - [x] 5.1.1 Verify `_handle_display` in `src/ksm/commands/add.py` works with grouped selectors
            - No code changes expected; confirm the add command flows through correctly
            - _Requirements: 5.1, 5.3_

        - [x] 5.1.2 Write integration tests for end-to-end grouped selection
            - Test `interactive_select` with multi-registry bundles returns correct qualified names
            - Test filter + selection across groups
            - Add to `tests/test_selector.py`
            - _Requirements: 5.1, 5.2, 5.3_

    - [x] 5.2 Final checkpoint
        - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests use Hypothesis with existing two-tier profiles (dev: 15, ci: 100)
- All new tests go in existing test files (`test_selector.py`, `test_tui.py`)
- The grouping function is the only new function; all other changes are refactors
