# Implementation Plan: Remove Interactive UI Uplift

## Overview

Refactor `render_removal_selector()`, `RemovalSelectorApp._refresh_options()`, `RemovalSelectorApp.on_input_changed()`, and the `interactive_removal_select()` fallback path to display a 3-column layout (name, scope, registry) and extend filtering to match registry names. TDD approach: write tests first, then implement.

## Tasks

- [x] 1. Extend render_removal_selector() with registry column and filter

    - [x] 1.1 Write tests for render_removal_selector() registry column

        - [x] 1.1.1 Write unit tests for 3-column output in render_removal_selector()
          - Test a known 2-entry list (one local, one global, different registries) produces lines containing bundle_name, bracketed scope, and source_registry
          - Test empty source_registry produces no trailing text after scope column
          - Test column order is name → scope → registry (left to right)
          - Add tests to `tests/test_selector.py`
          - _Requirements: 1.1, 1.4, 1.5, 3.1, 3.3, 4.1_

        - [x] 1.1.2 Write unit tests for column alignment in render_removal_selector()
          - Test that all bundle lines have their scope bracket `[` at the same character position
          - Test alignment holds with varying name lengths, scope values, and registry lengths
          - Add tests to `tests/test_selector.py`
          - _Requirements: 1.2, 1.3, 1.6, 3.2_

        - [x] 1.1.3 Write unit tests for filter matching registry in render_removal_selector()
          - Test filtering by a substring of source_registry includes the entry
          - Test filtering is case-insensitive for registry names
          - Test a filter matching neither bundle_name nor source_registry excludes the entry
          - Add tests to `tests/test_selector.py`
          - _Requirements: 5.1, 5.2_

        - [x] 1.1.4 Write property test for three-column content presence
          - **Property 1: Three-column content presence**
          - Build a Hypothesis ManifestEntry strategy (bundle_name: alphanumeric+underscore/hyphen 1-30 chars, scope: sampled from ["local", "global"], source_registry: either empty or alphanumeric 1-20 chars)
          - For any list of entries, each bundle line in render_removal_selector() output contains bundle_name, bracketed scope, and (when non-empty) source_registry
          - **Validates: Requirements 1.1, 1.4, 1.5, 3.1, 3.3**

        - [x] 1.1.5 Write property test for column alignment
          - **Property 2: Column alignment**
          - For any list of entries with any valid filter_text and multi_selected set, all bundle lines have scope bracket `[` at the same character position
          - Column order is name → scope → registry
          - **Validates: Requirements 1.2, 1.3, 1.6, 2.4, 2.5, 3.2, 4.1**

        - [x] 1.1.6 Write property test for filter matching name and registry
          - **Property 3: Filter matches both name and registry**
          - For any ManifestEntry and any case-insensitive substring of bundle_name or source_registry, filtering includes the entry; a substring of neither excludes it
          - **Validates: Requirements 5.1, 5.2**

    - [x] 1.2 Implement render_removal_selector() changes

        - [x] 1.2.1 Add registry column to render_removal_selector()
          - Compute `max_registry` column width from filtered entries
          - Append dim registry text after scope column, padded to max_registry
          - When source_registry is empty, render blank space
          - Modify `src/ksm/selector.py` render_removal_selector()
          - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 3.1, 3.2, 3.3, 4.1_

        - [x] 1.2.2 Extend filter predicate to match source_registry
          - Add `or ft in e.source_registry.lower()` to the filter in render_removal_selector()
          - Modify `src/ksm/selector.py` render_removal_selector()
          - _Requirements: 5.1, 5.2_

        - [x] 1.2.3 Run tests and verify all pass
          - Run `pytest tests/test_selector.py -v` and confirm all new and existing tests pass
          - _Requirements: 1.1–1.6, 3.1–3.3, 4.1, 5.1, 5.2_

    - [x] 1.3 Checkpoint
      - Ensure all tests pass, ask the user if questions arise.

- [x] 2. Extend RemovalSelectorApp TUI with registry column and filter

    - [x] 2.1 Write tests for RemovalSelectorApp registry column and filter

        - [x] 2.1.1 Write unit tests for TUI 3-column rendering
          - Test RemovalSelectorApp renders registry column in option labels with dim styling
          - Test TUI option labels contain bundle_name (bold cyan), scope (dim), and registry (dim)
          - Test empty source_registry omits registry segment
          - Add tests to `tests/test_tui.py`
          - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

        - [x] 2.1.2 Write unit tests for TUI filter matching registry
          - Test TUI filter matches by registry name only (entry with matching registry stays visible)
          - Test TUI filter is case-insensitive for registry
          - Add tests to `tests/test_tui.py`
          - _Requirements: 5.1, 5.2_

    - [x] 2.2 Implement RemovalSelectorApp changes

        - [x] 2.2.1 Add registry column to RemovalSelectorApp._refresh_options()
          - Compute max_name and max_scope across filtered_entries
          - Build rich.text.Text label with three segments: bold cyan name (padded), dim scope bracket (padded), dim registry
          - When source_registry is empty, omit registry segment
          - Modify `src/ksm/tui.py` RemovalSelectorApp._refresh_options()
          - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

        - [x] 2.2.2 Extend filter in RemovalSelectorApp.on_input_changed()
          - Add `or ft in e.source_registry.lower()` to the filter predicate
          - Modify `src/ksm/tui.py` RemovalSelectorApp.on_input_changed()
          - _Requirements: 5.1, 5.2_

        - [x] 2.2.3 Run tests and verify all pass
          - Run `pytest tests/test_tui.py -v` and confirm all new and existing tests pass
          - _Requirements: 2.1–2.5, 5.1, 5.2_

    - [x] 2.3 Checkpoint
      - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Extend fallback selector with registry column

    - [x] 3.1 Write tests for fallback selector registry column

        - [x] 3.1.1 Write unit tests for fallback numbered-list registry column
          - Test interactive_removal_select() fallback builds items with 3-column formatted strings including registry
          - Test empty source_registry produces no registry text in fallback label
          - Test column alignment in fallback output
          - Add tests to `tests/test_selector.py`
          - _Requirements: 3.1, 3.2, 3.3, 4.1, 4.2_

    - [x] 3.2 Implement fallback selector changes

        - [x] 3.2.1 Add registry column to interactive_removal_select() fallback path
          - Compute column widths from sorted_entries
          - Build items tuples with 3-column formatted strings: `(name_padded, "[scope]  registry")`
          - When source_registry is empty, omit registry text
          - Modify `src/ksm/selector.py` interactive_removal_select()
          - _Requirements: 3.1, 3.2, 3.3, 4.1, 4.2_

        - [x] 3.2.2 Run tests and verify all pass
          - Run `pytest tests/test_selector.py tests/test_tui.py -v` and confirm all tests pass
          - _Requirements: 3.1–3.3, 4.1, 4.2_

    - [x] 3.3 Checkpoint
      - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Final validation

    - [x] 4.1 Full test suite and coverage

        - [x] 4.1.1 Run full test suite with coverage
          - Run `pytest tests/ --cov=src/ksm/selector --cov=src/ksm/tui --cov-report=term-missing -v`
          - Verify ≥95% coverage on modified modules
          - Verify all existing tests still pass (no regressions)
          - _Requirements: 1.1–1.6, 2.1–2.5, 3.1–3.3, 4.1, 4.2, 5.1, 5.2_

        - [x] 4.1.2 Run linting
          - Run `black src/ksm/selector.py src/ksm/tui.py tests/test_selector.py tests/test_tui.py`
          - Run `flake8 src/ksm/selector.py src/ksm/tui.py tests/test_selector.py tests/test_tui.py`
          - _Requirements: all_

    - [x] 4.2 Final checkpoint
      - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- No new modules or classes are introduced; all changes refactor existing code
