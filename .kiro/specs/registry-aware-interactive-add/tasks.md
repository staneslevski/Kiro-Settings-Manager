# Implementation Plan: Registry-Aware Interactive Add

## Overview

Make the `ksm add -i` interactive selector registry-aware end-to-end. Changes are scoped to `selector.py`, `tui.py`, and `commands/add.py`. All tests go in `tests/test_registry_aware_selector.py`. TDD: write tests first, then implement.

## Tasks

- [ ] 1. Selector rendering changes

    - [ ] 1.1 Update `render_add_selector` two-column layout

        - [ ] 1.1.1 Write property test for display contains bundle name and registry name
            - **Property 1: Display contains bundle name and registry name**
            - Generate random `BundleInfo` lists with non-empty `registry_name`
            - Call `render_add_selector()`, assert each bundle's `name` and `registry_name` appear in output
            - **Validates: Requirements 1.1, 1.3**

        - [ ] 1.1.2 Write property test for installed detection uses bare name
            - **Property 2: Installed detection uses bare name**
            - Generate random bundles and random `installed_names` subsets
            - Call `render_add_selector()`, assert `[installed]` appears iff `bundle.name in installed_names`
            - **Validates: Requirements 1.4**

        - [ ] 1.1.3 Write property test for duplicate bundle names produce separate items
            - **Property 4: Duplicate bundle names produce separate items**
            - Generate bundles with same `name` but different `registry_name` values
            - Call `render_add_selector()`, assert one selectable line per `BundleInfo`
            - **Validates: Requirements 4.1**

        - [ ] 1.1.4 Implement two-column layout in `render_add_selector` in `selector.py`
            - Remove ambiguity detection logic (`name_counts`, `ambiguous` set)
            - Always display `bundle_name` padded + dimmed `registry_name` as second column
            - Sort by `(bundle_name, registry_name)` for stable ordering
            - Skip registry column when `registry_name` is empty
            - _Requirements: 1.1, 1.2, 1.3, 1.5, 4.1_

        - [ ] 1.1.5 Update fallback path in `interactive_select` to show `bundle_name  (registry_name)` format
            - Pass `(registry_name)` as label to `_numbered_list_select`
            - _Requirements: 1.3_

    - [ ] 1.2 Checkpoint
        - Ensure all tests pass, ask the user if questions arise.

- [ ] 2. Return value changes

    - [ ] 2.1 Update `interactive_select` and TUI `_confirm_selection` to return qualified names

        - [ ] 2.1.1 Write property test for qualified name round-trip
            - **Property 3: Qualified name round-trip**
            - Generate random `(registry_name, bundle_name)` pairs
            - Build qualified name, parse with `parse_qualified_name()`, assert round-trip equality
            - Test empty `registry_name` produces bare name with no leading `/`
            - **Validates: Requirements 2.1, 2.2, 2.4, 2.5, 1.5**

        - [ ] 2.1.2 Implement qualified name return in fallback `interactive_select` in `selector.py`
            - Build `f"{registry_name}/{bundle_name}"` when `registry_name` is non-empty
            - Return bare `bundle_name` when `registry_name` is empty
            - _Requirements: 2.1, 2.5_

        - [ ] 2.1.3 Implement qualified name return in TUI `_confirm_selection` in `tui.py`
            - Set `selected_names` to `f"{bundle.registry_name}/{bundle.name}"` when `registry_name` is non-empty
            - Return bare `bundle.name` when `registry_name` is empty
            - _Requirements: 2.1, 2.2, 2.4_

    - [ ] 2.2 Checkpoint
        - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. TUI display and filter changes

    - [ ] 3.1 Update TUI `_build_display_items` and `_refresh_options`

        - [ ] 3.1.1 Refactor `_build_display_items` in `tui.py`
            - Remove ambiguity detection logic
            - Store `(bundle_name, bundle)` tuples sorted by `(name, registry_name)`
            - _Requirements: 1.1, 1.2, 4.1_

        - [ ] 3.1.2 Update `_refresh_options` in `tui.py` to render two-column layout
            - Render bundle name in bold cyan, registry name in dim style with padding
            - _Requirements: 1.2_

    - [ ] 3.2 Update TUI filter to match both fields

        - [ ] 3.2.1 Write property test for filter matches both bundle name and registry name
            - **Property 5: Filter matches both bundle name and registry name**
            - Generate random bundles and a filter substring
            - Call `render_add_selector()` with filter, assert result matches expected filter logic
            - **Validates: Requirements 5.1**

        - [ ] 3.2.2 Implement dual-field filter in `on_input_changed` in `tui.py`
            - Match filter text against both `bundle.name` and `bundle.registry_name` (case-insensitive)
            - _Requirements: 5.1, 5.2_

        - [ ] 3.2.3 Update filter in `render_add_selector` in `selector.py` to match both fields
            - Filter against both `bundle.name` and `bundle.registry_name`
            - _Requirements: 5.1, 5.2_

    - [ ] 3.3 Checkpoint
        - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Integration wiring

    - [ ] 4.1 Wire `_handle_display` pass-through and end-to-end resolution

        - [ ] 4.1.1 Write property test for qualified name resolves to correct registry
            - **Property 6: Qualified name resolves to correct registry**
            - Build a `RegistryIndex` with duplicate bundles across registries
            - Call `resolve_qualified_bundle()`, assert returned `registry_name` matches input
            - **Validates: Requirements 3.3, 4.2**

        - [ ] 4.1.2 Write unit tests for `_handle_display` pass-through
            - Verify `_handle_display()` returns the qualified name from `interactive_select()` unchanged
            - Test cancellation returns `None`
            - _Requirements: 3.1_

        - [ ] 4.1.3 Write unit tests for empty `registry_name` edge case
            - Display shows bare name, return is bare name, no leading `/`
            - _Requirements: 1.5_

    - [ ] 4.2 Checkpoint
        - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Backward compatibility verification

    - [ ] 5.1 Verify existing non-interactive workflows unchanged

        - [ ] 5.1.1 Write unit tests for backward compatibility
            - `run_add()` with bare name still calls `resolve_bundle()`
            - `run_add()` with `registry/bundle` still calls `resolve_qualified_bundle()`
            - _Requirements: 6.1, 6.2_

    - [ ] 5.2 Final checkpoint
        - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tests go in `tests/test_registry_aware_selector.py`
- Property tests use Hypothesis with existing two-tier profile (dev=15, ci=100)
- Changes are scoped to `selector.py`, `tui.py`, `commands/add.py` only
- Resolver, installer, manifest, and scanner modules remain unchanged
