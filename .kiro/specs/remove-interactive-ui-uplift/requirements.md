# Requirements Document

## Introduction

Uplift the interactive UI for `ksm remove -i` to display a 3-column layout showing bundle name, installation scope (local/global), and source registry. Currently the removal selector shows only the bundle name and scope. The registry column is missing, making it harder for users to identify which registry a bundle was installed from when deciding what to remove.

## Glossary

- **Removal_Selector**: The interactive UI component (both Textual TUI `RemovalSelectorApp` and the numbered-list fallback) displayed when the user runs `ksm remove -i` or `ksm rm -i`.
- **ManifestEntry**: A data record representing an installed bundle, containing `bundle_name`, `source_registry`, `scope`, `installed_files`, timestamps, and optional `version`.
- **Bundle_Name_Column**: The first column in the Removal_Selector displaying the bundle name.
- **Scope_Column**: The second column in the Removal_Selector displaying whether the bundle is installed locally or globally.
- **Registry_Column**: The third column in the Removal_Selector displaying the name of the registry the bundle was added from.
- **Textual_TUI**: The rich terminal UI rendered via the Textual library (`RemovalSelectorApp`).
- **Fallback_Selector**: The numbered-list prompt used when Textual is unavailable, stdin is not a TTY, or TERM=dumb.

## Requirements

### Requirement 1: Three-Column Layout in Removal Selector

**User Story:** As a user, I want the interactive removal selector to show the bundle name, scope, and source registry in aligned columns, so that I can make informed decisions about which bundle to remove.

#### Acceptance Criteria

1. THE Removal_Selector SHALL display three columns for each entry: Bundle_Name_Column, Scope_Column, and Registry_Column.
2. THE Bundle_Name_Column SHALL display the `bundle_name` from the ManifestEntry, padded to align all rows.
3. THE Scope_Column SHALL display the `scope` value from the ManifestEntry (either "local" or "global"), formatted as a bracketed label (e.g. `[local]` or `[global]`), padded to align all rows.
4. THE Registry_Column SHALL display the `source_registry` value from the ManifestEntry.
5. WHEN a ManifestEntry has an empty `source_registry`, THE Registry_Column SHALL display nothing for that row.
6. THE Removal_Selector SHALL pad each column so that all rows are visually aligned.

### Requirement 2: Textual TUI Three-Column Layout

**User Story:** As a user running `ksm rm -i` in a capable terminal, I want the Textual TUI removal selector to show all three columns with proper styling, so that the information is easy to scan.

#### Acceptance Criteria

1. THE Textual_TUI SHALL render the Bundle_Name_Column with bold cyan styling.
2. THE Textual_TUI SHALL render the Scope_Column with dim styling.
3. THE Textual_TUI SHALL render the Registry_Column with dim styling.
4. THE Textual_TUI SHALL maintain column alignment when the filter input narrows the displayed entries.
5. THE Textual_TUI SHALL maintain column alignment when multi-select checkboxes are displayed.

### Requirement 3: Fallback Selector Three-Column Layout

**User Story:** As a user running `ksm rm -i` in a limited terminal (no Textual), I want the numbered-list fallback to also show all three columns, so that I get the same information regardless of terminal capability.

#### Acceptance Criteria

1. THE Fallback_Selector SHALL display the Bundle_Name_Column, Scope_Column, and Registry_Column for each entry in the numbered list.
2. THE Fallback_Selector SHALL pad columns so that all rows are visually aligned.
3. WHEN a ManifestEntry has an empty `source_registry`, THE Fallback_Selector SHALL display nothing for the Registry_Column of that row.

### Requirement 4: Column Ordering

**User Story:** As a user, I want the columns to appear in a consistent order, so that I can quickly scan the information I need.

#### Acceptance Criteria

1. THE Removal_Selector SHALL display columns in the following order from left to right: Bundle_Name_Column, Scope_Column, Registry_Column.
2. THE Removal_Selector SHALL maintain the column order across the Textual_TUI and the Fallback_Selector.

### Requirement 5: Filter Includes Registry

**User Story:** As a user, I want to filter bundles by registry name in addition to bundle name, so that I can quickly find bundles from a specific registry.

#### Acceptance Criteria

1. WHEN a filter is applied in the Removal_Selector, THE Removal_Selector SHALL match against both the `bundle_name` and the `source_registry` fields (case-insensitive).
2. WHEN a filter matches a ManifestEntry by `source_registry` only, THE Removal_Selector SHALL include that entry in the filtered results.
