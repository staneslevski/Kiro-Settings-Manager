# Requirements Document

## Introduction

When config bundles are listed in the ksm CLI (interactive selectors, fallback numbered lists, and the `ksm list` command), they are currently sorted as a flat alphabetical list. This feature groups bundles by their source registry and sorts both the registry groups and the bundles within each group alphabetically, making it easier to identify which bundles come from which registry.

## Glossary

- **Bundle_Selector**: The interactive UI (Textual TUI or numbered-list fallback) shown when the user runs `ksm add -i` or `ksm add` on a TTY without a bundle name. Renders available bundles for selection.
- **Removal_Selector**: The interactive UI shown when the user runs `ksm rm -i`. Renders installed bundles for removal selection.
- **Registry_Group**: A visual grouping of bundles that share the same source registry, displayed under a registry name header.
- **Registry_Name**: The name field of a RegistryEntry (e.g. "default", "my-custom-registry").
- **Bundle_List**: Any rendered list of config bundles shown to the user in the terminal.
- **Flat_Sort**: The current sorting behaviour where all bundles are sorted alphabetically without grouping.

## Requirements

### Requirement 1: Group bundles by registry in the add selector

**User Story:** As a user, I want bundles in the add selector to be grouped by registry, so that I can quickly identify which registry each bundle belongs to.

#### Acceptance Criteria

1. WHEN the Bundle_Selector renders available bundles, THE Bundle_Selector SHALL group bundles by Registry_Name and display each Registry_Group under a visible registry name header.
2. WHEN the Bundle_Selector renders Registry_Groups, THE Bundle_Selector SHALL sort Registry_Groups in case-insensitive alphabetical order by Registry_Name.
3. WHEN the Bundle_Selector renders bundles within a Registry_Group, THE Bundle_Selector SHALL sort bundles in case-insensitive alphabetical order by bundle name.
4. WHEN only one registry exists, THE Bundle_Selector SHALL display the single Registry_Group with its registry name header.

### Requirement 2: Group bundles by registry in the TUI selector

**User Story:** As a user, I want the Textual TUI bundle selector to visually separate registry groups, so that I can distinguish bundles from different registries.

#### Acceptance Criteria

1. WHEN the BundleSelectorApp builds display items, THE BundleSelectorApp SHALL group bundles by Registry_Name and sort Registry_Groups in case-insensitive alphabetical order.
2. WHEN the BundleSelectorApp renders a Registry_Group, THE BundleSelectorApp SHALL display a non-selectable separator row containing the Registry_Name before the group's bundles.
3. WHEN the BundleSelectorApp renders bundles within a Registry_Group, THE BundleSelectorApp SHALL sort bundles in case-insensitive alphabetical order by bundle name.
4. WHEN the user filters bundles by typing, THE BundleSelectorApp SHALL preserve registry grouping for matching results and hide Registry_Groups that contain zero matching bundles.

### Requirement 3: Group bundles by registry in the numbered-list fallback

**User Story:** As a user without Textual available, I want the numbered-list fallback to group bundles by registry, so that I get the same organisational benefit.

#### Acceptance Criteria

1. WHEN the numbered-list fallback renders available bundles, THE Bundle_Selector SHALL group bundles by Registry_Name with a text header for each Registry_Group.
2. WHEN the numbered-list fallback renders Registry_Groups, THE Bundle_Selector SHALL sort Registry_Groups in case-insensitive alphabetical order by Registry_Name.
3. WHEN the numbered-list fallback renders bundles within a Registry_Group, THE Bundle_Selector SHALL sort bundles in case-insensitive alphabetical order by bundle name.
4. THE numbered-list fallback SHALL use continuous numbering across all Registry_Groups so that each bundle has a unique selectable number.

### Requirement 4: Group bundles by registry in the render_add_selector function

**User Story:** As a developer, I want the render_add_selector function to produce registry-grouped output, so that all rendering paths produce consistent grouped output.

#### Acceptance Criteria

1. WHEN render_add_selector produces output lines, THE render_add_selector function SHALL group bundles by Registry_Name with a header line for each Registry_Group.
2. WHEN render_add_selector produces Registry_Groups, THE render_add_selector function SHALL sort Registry_Groups in case-insensitive alphabetical order.
3. WHEN render_add_selector produces bundles within a Registry_Group, THE render_add_selector function SHALL sort bundles in case-insensitive alphabetical order by bundle name.
4. WHEN a filter_text is provided, THE render_add_selector function SHALL hide Registry_Groups that contain zero matching bundles.

### Requirement 5: Preserve existing bundle selection behaviour

**User Story:** As a user, I want bundle selection and multi-select to continue working correctly after grouping is introduced, so that the feature does not break existing workflows.

#### Acceptance Criteria

1. WHEN the user selects a bundle from a grouped list, THE Bundle_Selector SHALL return the same qualified name format (registry/bundle) as the current implementation.
2. WHEN the user multi-selects bundles across Registry_Groups, THE BundleSelectorApp SHALL correctly track selections by their position within the filtered list.
3. WHEN the user filters bundles, THE Bundle_Selector SHALL match against both bundle name and Registry_Name, consistent with current behaviour.
4. IF no bundles match the filter, THEN THE Bundle_Selector SHALL display a "no matches" message consistent with current behaviour.

### Requirement 6: Grouping logic as a reusable utility

**User Story:** As a developer, I want the grouping and sorting logic to be a single reusable function, so that all rendering paths use the same logic and stay consistent.

#### Acceptance Criteria

1. THE grouping module SHALL provide a function that accepts a list of BundleInfo objects and returns them organised as an ordered mapping of Registry_Name to list of BundleInfo.
2. THE grouping function SHALL sort Registry_Names in case-insensitive alphabetical order.
3. THE grouping function SHALL sort BundleInfo objects within each group in case-insensitive alphabetical order by bundle name.
4. WHEN a BundleInfo has an empty Registry_Name, THE grouping function SHALL place the bundle in a group keyed by an empty string, sorted last among all Registry_Groups.
