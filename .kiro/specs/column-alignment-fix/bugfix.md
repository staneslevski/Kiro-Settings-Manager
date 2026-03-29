# Bugfix Requirements Document

## Introduction

The interactive bundle selector columns are misaligned in both the fallback raw-mode selector (`render_add_selector` in `src/ksm/selector.py`) and the Textual TUI (`BundleSelectorApp._refresh_options` in `src/ksm/tui.py`). When a bundle has the "[installed]" marker, it is appended directly after the padded name, pushing the registry column to the right. Bundles without "[installed]" lack this offset, so the registry column does not line up across rows. The same class of issue affects the removal selector's "[scope]" column in `render_removal_selector` and `RemovalSelectorApp._refresh_options`. A utility function `_align_columns()` already exists in `src/ksm/color.py` that handles ANSI-aware column alignment but is not used by the selector code.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a bundle has the "[installed]" marker in `render_add_selector` THEN the system appends "[installed]" directly after the padded name, pushing the registry column to the right relative to rows without the marker

1.2 WHEN a bundle does not have the "[installed]" marker in `render_add_selector` THEN the system omits the marker text entirely, causing the registry column to start at a different position than rows with the marker

1.3 WHEN a bundle has the "[installed]" marker in `BundleSelectorApp._refresh_options` (TUI) THEN the system appends the badge after the padded name in the Rich Text label, pushing the registry name to the right relative to rows without the badge

1.4 WHEN a bundle does not have the "[installed]" marker in `BundleSelectorApp._refresh_options` (TUI) THEN the system omits the badge, causing the registry column to start at a different position than rows with the badge

1.5 WHEN entries have different scope labels (e.g. "[global]" vs "[local]") in `render_removal_selector` THEN the system appends the scope label after the padded name with a single space, but varying scope label widths may cause subsequent columns to misalign

1.6 WHEN entries have different scope labels in `RemovalSelectorApp._refresh_options` (TUI) THEN the system appends the scope label directly after the name without fixed-width allocation for the scope column

### Expected Behavior (Correct)

2.1 WHEN a bundle has the "[installed]" marker in `render_add_selector` THEN the system SHALL allocate a fixed-width column for the installed badge so that the registry column always starts at the same position regardless of whether the badge is present

2.2 WHEN a bundle does not have the "[installed]" marker in `render_add_selector` THEN the system SHALL pad the installed badge column with blank spaces equal to the badge width so that the registry column aligns with rows that have the badge

2.3 WHEN a bundle has the "[installed]" marker in `BundleSelectorApp._refresh_options` (TUI) THEN the system SHALL allocate a fixed-width column for the installed badge so that the registry column always starts at the same position

2.4 WHEN a bundle does not have the "[installed]" marker in `BundleSelectorApp._refresh_options` (TUI) THEN the system SHALL pad the installed badge column with blank spaces so that the registry column aligns with rows that have the badge

2.5 WHEN entries have different scope labels in `render_removal_selector` THEN the system SHALL allocate a fixed-width column for the scope label (based on the widest scope label) so that any subsequent content aligns across all rows

2.6 WHEN entries have different scope labels in `RemovalSelectorApp._refresh_options` (TUI) THEN the system SHALL allocate a fixed-width column for the scope label so that any subsequent content aligns across all rows

### Unchanged Behavior (Regression Prevention)

3.1 WHEN bundles are rendered in `render_add_selector` without any installed bundles THEN the system SHALL CONTINUE TO display bundle names padded to the same width with the registry column aligned

3.2 WHEN bundles are rendered in `render_add_selector` with a filter applied THEN the system SHALL CONTINUE TO filter bundles by case-insensitive substring match and display the filter text

3.3 WHEN bundles are rendered with multi-select indicators THEN the system SHALL CONTINUE TO show "[✓]" or "[ ]" prefixes correctly

3.4 WHEN the removal selector renders entries THEN the system SHALL CONTINUE TO sort entries alphabetically by bundle name (case-insensitive)

3.5 WHEN the add selector renders bundles THEN the system SHALL CONTINUE TO sort bundles alphabetically by name then registry (case-insensitive)

3.6 WHEN the selected bundle is highlighted THEN the system SHALL CONTINUE TO show the ">" prefix on the selected line and bold the selected name

3.7 WHEN existing alignment tests run (test_render_add_selector_installed_column_aligned, test_render_add_selector_columns_aligned, test_render_removal_selector_columns_aligned) THEN the system SHALL CONTINUE TO pass all of them
