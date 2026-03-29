# Column Alignment Fix — Bugfix Design

## Overview

The interactive selectors in `selector.py` and `tui.py` build display lines by concatenating variable-width fields (the `[installed]` badge and `[scope]` label) without fixed-width allocation. This causes subsequent columns (registry name, etc.) to shift horizontally depending on whether the badge/label is present and how wide it is. The fix allocates fixed-width columns for these variable fields so that all rows align consistently. An existing `_align_columns()` utility in `color.py` already handles ANSI-aware column alignment and should be leveraged where applicable.

## Glossary

- **Bug_Condition (C)**: A rendered selector row where a variable-width badge/scope field causes the next column to start at a different horizontal position than other rows
- **Property (P)**: All rows in a selector output have their columns starting at identical horizontal positions
- **Preservation**: Existing sorting, filtering, multi-select indicators, highlighting, and overall visual layout must remain unchanged
- **`render_add_selector()`**: Function in `src/ksm/selector.py` that builds ANSI-styled lines for the add-bundle fallback selector
- **`render_removal_selector()`**: Function in `src/ksm/selector.py` that builds ANSI-styled lines for the removal fallback selector
- **`BundleSelectorApp._refresh_options()`**: Method in `src/ksm/tui.py` that builds Rich Text labels for the Textual add-bundle selector
- **`RemovalSelectorApp._refresh_options()`**: Method in `src/ksm/tui.py` that builds Rich Text labels for the Textual removal selector
- **`_align_columns()`**: Utility in `src/ksm/color.py` that pads ANSI-containing column tuples to consistent widths

## Bug Details

### Bug Condition

The bug manifests when rows in a selector have different badge/scope field widths. In `render_add_selector`, the `[installed]` badge is either present (13 chars including leading space) or absent (0 chars), so the registry column shifts by 13 characters between rows. In `render_removal_selector`, scope labels like `[global]` (8 chars) vs `[local]` (7 chars) differ by 1 character. The same issues exist in the corresponding TUI `_refresh_options` methods.

**Formal Specification:**
```
FUNCTION isBugCondition(rows)
  INPUT: rows — list of rendered selector lines
  OUTPUT: boolean

  col_positions := SET()
  FOR EACH row IN rows DO
    pos := position of first character of the column AFTER
           the badge/scope field (e.g. registry name column)
    col_positions.ADD(pos)
  END FOR

  RETURN SIZE(col_positions) > 1
END FUNCTION
```

### Examples

- `render_add_selector` with bundles `["aws", "git"]` where `aws` is installed: the `aws` row has `aws  [installed]  default` while `git` row has `git               default` — the `default` column starts at different positions
- `render_add_selector` with bundles `["a", "long_bundle_name"]` both installed: `[installed]` tags start at different positions because name padding alone doesn't account for the badge
- `render_removal_selector` with entries having `[global]` and `[local]` scopes: the `[` bracket starts at the same position (name is padded) but the text after `]` would differ by 1 char if there were subsequent columns
- TUI `BundleSelectorApp`: Rich Text label appends badge with `dim` style directly after padded name, then appends registry — registry text shifts based on badge presence

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Bundle names padded to the width of the longest name in the list
- Alphabetical sorting (case-insensitive) by name then registry
- Filter text narrows the displayed list via case-insensitive substring match
- Multi-select `[✓]`/`[ ]` prefixes render correctly
- Selected line gets `>` prefix and bold name styling
- Removal selector sorts entries alphabetically by bundle name
- All existing alignment tests continue to pass

**Scope:**
All inputs that do NOT involve the badge/scope column layout should be completely unaffected by this fix. This includes:
- Sorting logic
- Filtering logic
- Multi-select toggle behavior
- Keyboard navigation and selection
- Header/instruction/footer rendering

## Hypothesized Root Cause

Based on code analysis, the root causes are:

1. **`render_add_selector` — no fixed-width badge column**: The `label` variable is either `dim(" [installed]", ...)` or `""`. It is concatenated directly: `f"{prefix} {check}{padded}{label}{reg_col}"`. When `label` is empty, the `reg_col` text shifts left by the width of `" [installed]"`.

2. **`BundleSelectorApp._refresh_options` — same issue with Rich Text**: The method does `label.append(badge, style="dim")` only when `badge` is non-empty, then appends the registry name. When badge is absent, no space is reserved.

3. **`render_removal_selector` — scope labels have different widths**: `[global]` is 8 chars, `[local]` is 7 chars. Currently the scope label is appended with a single space after the padded name: `f"{prefix} {check}{padded} {scope_label}"`. If any content followed the scope label, it would misalign. The scope label itself starts at a consistent position (after padded name + space), but the label width varies.

4. **`RemovalSelectorApp._refresh_options` — same scope width issue in TUI**: `label.append(f" [{entry.scope}]", style="dim")` produces labels of different widths.

5. **Unused `_align_columns()` utility**: `color.py` already has `_align_columns()` which takes tuples of column strings and pads them using ANSI-aware width calculation. The fallback render functions could use this instead of manual concatenation.

## Correctness Properties

Property 1: Bug Condition — Registry column alignment in add selector

_For any_ set of bundles with a mix of installed and not-installed entries, the rendered output of `render_add_selector` SHALL have the registry column starting at the same horizontal position across all bundle rows (after stripping ANSI codes).

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation — Existing selector behavior unchanged

_For any_ input where the bug condition does NOT hold (all bundles have the same badge state, or there is only one bundle), the fixed `render_add_selector` SHALL produce output with the same content, sorting, filtering, and prefix behavior as the original function.

**Validates: Requirements 3.1, 3.2, 3.3, 3.5, 3.6**

Property 3: Bug Condition — Scope column alignment in removal selector

_For any_ set of manifest entries with mixed scope values (e.g. "local" and "global"), the rendered output of `render_removal_selector` SHALL have the scope label column occupying a fixed width so that any subsequent content aligns across all rows.

**Validates: Requirements 2.5**

Property 4: Preservation — Removal selector behavior unchanged

_For any_ input to `render_removal_selector`, the fixed function SHALL preserve alphabetical sorting, scope label content, multi-select indicators, and selected-line highlighting.

**Validates: Requirements 3.4, 3.7**

Property 5: Bug Condition — TUI add selector registry alignment

_For any_ set of bundles rendered by `BundleSelectorApp._refresh_options`, the plain text of each Rich Text label SHALL have the registry name starting at the same horizontal position regardless of badge presence.

**Validates: Requirements 2.3, 2.4**

Property 6: Bug Condition — TUI removal selector scope alignment

_For any_ set of entries rendered by `RemovalSelectorApp._refresh_options`, the plain text of each Rich Text label SHALL have the scope label occupying a fixed width.

**Validates: Requirements 2.6**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `src/ksm/selector.py`

**Function**: `render_add_selector`

**Specific Changes**:
1. **Compute max badge width**: Before the loop, determine the badge column width. If any bundle is installed, the badge width is `len(" [installed]")` (13 chars); otherwise 0.
2. **Use `_align_columns` or fixed-width padding**: Build each row as a tuple of column strings (prefix+check, padded_name, badge_padded, registry) and use `_align_columns()` from `color.py`, OR manually pad the badge field to the fixed width using ANSI-aware length calculation via `_strip_ansi`.
3. **Pad empty badges**: When a bundle is not installed, pad the badge column with spaces to match the badge width.

**Function**: `render_removal_selector`

**Specific Changes**:
1. **Compute max scope label width**: Before the loop, compute `max_scope = max(len(f"[{e.scope}]") for e in sorted_entries)`.
2. **Pad scope labels**: Pad each scope label string to `max_scope` width (using ANSI-aware length) so all scope columns occupy the same width.

**File**: `src/ksm/tui.py`

**Method**: `BundleSelectorApp._refresh_options`

**Specific Changes**:
1. **Compute badge column width**: If any bundle in `filtered_items` is installed, set `badge_width = len(" [installed]")`; otherwise 0.
2. **Fixed-width badge in Rich Text**: Always append a badge field of `badge_width` characters. When the bundle is installed, append `" [installed]"` padded to `badge_width`. When not installed, append spaces of `badge_width` length.

**Method**: `RemovalSelectorApp._refresh_options`

**Specific Changes**:
1. **Compute max scope width**: `max_scope = max(len(f"[{e.scope}]") for e in filtered_entries)`.
2. **Pad scope labels**: Pad each `f" [{entry.scope}]"` string to a fixed width before appending to the Rich Text label.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis.

**Test Plan**: Write tests that render selectors with mixed badge/scope states and assert column alignment. Run on UNFIXED code to observe failures.

**Test Cases**:
1. **Add selector mixed installed**: Render with some bundles installed, some not — check registry column position (will fail on unfixed code)
2. **Add selector all installed, different name lengths**: Render with all installed but varying name lengths — check `[installed]` tag position (will fail on unfixed code)
3. **Removal selector mixed scopes**: Render with `[global]` and `[local]` entries — check scope bracket position (will fail on unfixed code)
4. **TUI add selector mixed badges**: Build Rich Text labels with mixed badge states — check plain text alignment (will fail on unfixed code)

**Expected Counterexamples**:
- Registry column starts at position N for installed rows and position N-13 for non-installed rows
- Scope bracket column differs by 1 char between `[global]` and `[local]` rows

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed functions produce aligned columns.

**Pseudocode:**
```
FOR ALL bundles, installed_names WHERE isBugCondition(rows) DO
  rows := render_add_selector_fixed(bundles, installed_names, 0)
  positions := registry_column_positions(rows)
  ASSERT ALL_EQUAL(positions)
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed functions produce the same result as the original.

**Pseudocode:**
```
FOR ALL bundles, installed_names WHERE NOT isBugCondition(rows) DO
  ASSERT content_of(render_add_selector_fixed(...))
         == content_of(render_add_selector_original(...))
END FOR
```

**Testing Approach**: Property-based testing with Hypothesis is recommended because:
- It generates many combinations of bundle names, installed states, and scope values
- It catches edge cases like empty lists, single-item lists, all-installed, none-installed
- It provides strong guarantees that alignment holds across the input domain

**Test Plan**: Observe column positions on UNFIXED code first, then write property-based tests that assert alignment on fixed code.

**Test Cases**:
1. **Registry alignment preservation**: For any bundles with no installed entries, verify columns still align after fix
2. **Sort order preservation**: For any bundles, verify alphabetical sort order is unchanged
3. **Filter preservation**: For any filter text, verify filtered results are unchanged
4. **Multi-select preservation**: For any multi-select state, verify indicators render correctly

### Unit Tests

- Test `render_add_selector` with mixed installed/not-installed bundles — registry column aligned
- Test `render_add_selector` with all installed, varying name lengths — `[installed]` tag aligned
- Test `render_add_selector` with no installed bundles — no extra padding introduced
- Test `render_removal_selector` with mixed `[global]`/`[local]` scopes — scope column aligned
- Test edge cases: single bundle, empty list, all same scope

### Property-Based Tests

- Generate random bundle sets with random installed subsets; assert registry column positions are identical across all rows
- Generate random manifest entries with random scopes; assert scope bracket positions are identical
- Generate random bundles and verify sorting, filtering, and multi-select are preserved

### Integration Tests

- Test that existing alignment tests (`test_render_add_selector_installed_column_aligned`, `test_render_add_selector_columns_aligned`, `test_render_removal_selector_columns_aligned`) continue to pass
- Test full selector rendering pipeline with realistic bundle data
- Test TUI label building produces aligned plain text output
