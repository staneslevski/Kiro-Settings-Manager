# Requirements Document

## Introduction

The `ksm add -i` interactive selector currently loses registry information when returning selected bundle names. When a bundle exists in multiple registries, the unqualified name causes an ambiguity error in the resolver. This feature makes the interactive selection pipeline registry-aware end-to-end so that users always see which registry published each bundle and can select a specific registry's version without errors.

## Glossary

- **Interactive_Selector**: The component (`interactive_select()` in `selector.py`) that presents bundles to the user and returns their selection.
- **TUI**: The Textual-based terminal UI (`BundleSelectorApp` in `tui.py`) used for bundle selection when Textual is available.
- **Fallback_Selector**: The numbered-list prompt in `selector.py` used when Textual is unavailable or stdin is not a TTY.
- **Display_Handler**: The `_handle_display()` function in `commands/add.py` that launches the interactive selector and passes the result back to `run_add()`.
- **Resolver**: The module (`resolver.py`) that locates bundles by name across registries. Contains `resolve_bundle()` for unqualified names and `resolve_qualified_bundle()` for `registry/bundle` format.
- **Qualified_Name**: A bundle identifier in the format `registry/bundle_name` that unambiguously identifies a bundle from a specific registry.
- **BundleInfo**: A dataclass in `scanner.py` holding bundle metadata including `name`, `path`, `subdirectories`, and `registry_name`.

## Requirements

### Requirement 1: Always Display Registry Origin in Interactive Selector

**User Story:** As a user, I want to see which registry every bundle comes from in the interactive selector, so I always know the publisher of each bundle.

#### Acceptance Criteria

1. THE Interactive_Selector SHALL display every bundle with the bundle name as the primary column and the registry name as a secondary column to the right, so users scan bundle names first and see the publisher as context.
2. THE TUI SHALL render the bundle name in the default or bold style and the registry name to the right in a visually subdued style (e.g., dimmed), padded to form a consistent column.
3. THE Fallback_Selector SHALL display each numbered option as the bundle name followed by the registry name in parentheses (e.g., `aws  (my-registry)`).
4. THE `[installed]` indicator SHALL be determined by matching the bundle's bare name against the manifest, regardless of display format.
5. IF a BundleInfo has an empty `registry_name`, THE Interactive_Selector SHALL display and return the bare `bundle_name` without a registry column. THE system SHALL NOT produce qualified names with an empty registry component.

### Requirement 2: Return Qualified Names from Interactive Selector

**User Story:** As a developer, I want the interactive selector to return qualified names that include registry information, so that downstream resolution is unambiguous.

#### Acceptance Criteria

1. WHEN the user selects a bundle, THE Interactive_Selector SHALL return the selection in `registry_name/bundle_name` format.
2. WHEN the user selects multiple bundles via multi-select in the TUI, THE TUI SHALL return each selection in `registry_name/bundle_name` format. Multi-select is available in TUI mode only; the Fallback_Selector supports single selection.
3. WHEN the user cancels the selection, THE Interactive_Selector SHALL return None.
4. THE TUI SHALL set `selected_names` to a list of `registry_name/bundle_name` strings upon confirmation.
5. THE Fallback_Selector SHALL return the qualified name for the chosen item.

### Requirement 3: Display Handler Passes Qualified Names to Resolver

**User Story:** As a developer, I want `_handle_display()` to pass qualified names through to `run_add()`, so that the resolver can find the exact bundle without ambiguity.

#### Acceptance Criteria

1. WHEN the Interactive_Selector returns a qualified name, THE Display_Handler SHALL pass the qualified name as the `bundle_spec` to `run_add()`.
2. WHEN `run_add()` receives a qualified `bundle_spec`, THE Resolver SHALL use `resolve_qualified_bundle()` to locate the bundle in the specified registry.
3. WHEN a bundle exists in multiple registries and the user selects one via the interactive selector, THE Resolver SHALL resolve the bundle from the selected registry without error.

### Requirement 4: Ambiguous Bundle Selection Succeeds End-to-End

**User Story:** As a user, I want to select a bundle that exists in multiple registries via the interactive selector and have it install correctly, so that I am not blocked by ambiguity errors.

#### Acceptance Criteria

1. WHEN a bundle name exists in two or more registries, THE Interactive_Selector SHALL show each registry's version as a separate selectable item.
2. WHEN the user selects one of the ambiguous items, THE system SHALL install the bundle from the selected registry.
3. WHEN the user selects one of the ambiguous items, THE system SHALL record the correct source registry in the manifest.

### Requirement 5: Filter and Search Behavior

**User Story:** As a user, I want to filter the bundle list by typing, and have it match against both registry names and bundle names, so I can find what I need quickly.

#### Acceptance Criteria

1. THE filter/search in the Interactive_Selector SHALL match against both the registry name and the bundle name.
2. WHEN a filter is active, THE Interactive_Selector SHALL apply the same two-column display rules to the filtered result set.

### Requirement 6: Backward Compatibility

**User Story:** As a user, I want existing non-interactive workflows to continue working unchanged, so that this change does not break my current usage.

#### Acceptance Criteria

1. WHEN a user runs `ksm add bundle_name` without `-i`, THE Resolver SHALL continue to use unqualified resolution and report ambiguity errors as before.
2. WHEN a user runs `ksm add registry/bundle_name` without `-i`, THE Resolver SHALL continue to use qualified resolution as before.
