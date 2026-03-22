# Implementation Plan: UX Visual Overhaul

## Overview

Overhaul the `ksm` CLI visual layer across color utilities, error formatting, diff summary, all command modules, and Textual TUI apps. All changes are additive — existing functions remain as backward-compatible aliases. Implementation follows TDD: tests first, then code.

## Tasks

- [x] 1. Core color system (`color.py`)

  - [x] 1.1 Terminal detection and semantic color foundations

    - [x] 1.1.1 Write tests for `_color_level()` detection logic
      - Test NO_COLOR → 0, TERM=dumb → 0, non-TTY → 0
      - Test COLORTERM=truecolor → 4, TERM containing 256color → 3
      - Test default TTY → 2, priority ordering
      - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

    - [x] 1.1.2 Implement `_color_level()` function
      - Priority: NO_COLOR → TERM=dumb → non-TTY → COLORTERM → TERM 256color → default 2
      - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

    - [x] 1.1.3 Write tests for `_supports_unicode()` and symbol constants
      - Test TERM=dumb → False, non-UTF-8 encoding → False
      - Test Unicode vs ASCII fallback symbol values
      - Test fixed symbols SYM_NEW, SYM_UPDATED, SYM_UNCHANGED
      - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

    - [x] 1.1.4 Implement `_supports_unicode()` and symbol constants
      - Check locale.getpreferredencoding() and TERM env var
      - Define SYM_CHECK, SYM_CROSS, SYM_ARROW, SYM_DOT with fallbacks
      - Define fixed SYM_NEW=+, SYM_UPDATED=~, SYM_UNCHANGED==
      - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

    - [x] 1.1.5 Write property test for `_color_level()` (Property 5)
      - **Property 5: _color_level() returns valid level respecting environment priority**
      - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7**

  - [x] 1.2 Semantic colors, style(), and text utilities

    - [x] 1.2.1 Write tests for semantic color functions and `style()`
      - Test each function produces correct ANSI code on TTY at level ≥ 2
      - Test `style()` joins multiple codes with semicolons
      - Test bright downgrade (90-97 → 30-37) at color level 1
      - Test backward compatibility of green, red, yellow, dim, bold
      - _Requirements: 1.1, 1.2, 1.3, 1.4_

    - [x] 1.2.2 Implement semantic color functions and `style()`
      - Add success(92), error_style(91), warning_style(93), accent(96), info(94), muted(2), subtle(2;3)
      - Add `style(text, *codes, stream=None)` combining codes
      - Update `_wrap()` to use `_color_level()` with bright downgrade
      - Retain existing green/red/yellow/dim/bold unchanged
      - _Requirements: 1.1, 1.2, 1.3, 1.4_

    - [x] 1.2.3 Write tests for `_strip_ansi()` and `_align_columns()`
      - Test strip removes all ANSI sequences, preserves plain text
      - Test align with ANSI-containing strings, empty input, single row
      - Test last column has no trailing padding
      - _Requirements: 1.5, 4.1, 4.2, 4.3, 4.4_

    - [x] 1.2.4 Implement `_strip_ansi()` and `_align_columns()`
      - Regex `r'\033\[[0-9;]*m'` for strip
      - Calculate widths via stripped lengths, pad all but last column
      - _Requirements: 1.5, 4.1, 4.2, 4.3, 4.4_

    - [x] 1.2.5 Write property tests for color functions (Properties 1-4)
      - **Property 1: Color functions produce correct ANSI codes**
      - **Property 2: style() combines multiple ANSI codes**
      - **Property 3: Bright variant downgrade on 8-color terminals**
      - **Property 4: strip_ansi round trip**
      - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

    - [x] 1.2.6 Write property test for `_align_columns()` (Property 6)
      - **Property 6: _align_columns() produces ANSI-aware aligned output**
      - **Validates: Requirements 4.2, 4.3**

  - [x] 1.3 Checkpoint — Core color system
    - Ensure all tests pass, ask the user if questions arise.

- [x] 2. Error formatting (`errors.py`)

  - [x] 2.1 Error message formatting updates

    - [x] 2.1.1 Write tests for updated format_error, format_warning, format_deprecation
      - Test lowercase prefixes: `error:`, `warning:`, `deprecated:`
      - Test semantic colors: error_style prefix, muted why, subtle fix
      - Test bundle name accent styling in error messages
      - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

    - [x] 2.1.2 Update format_error, format_warning, format_deprecation
      - Change prefixes to lowercase
      - Use error_style, warning_style, muted, subtle, accent from color.py
      - Style bundle names with accent when detected in `what` parameter
      - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

    - [x] 2.1.3 Write property tests for error formatting (Properties 7-8)
      - **Property 7: Error/warning/deprecation uses correct prefixes and styles**
      - **Property 8: Error messages style bundle names with accent**
      - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**

  - [x] 2.2 Checkpoint — Error formatting
    - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Diff summary formatting (`copier.py`)

  - [x] 3.1 Diff summary updates

    - [x] 3.1.1 Write tests for updated format_diff_summary
      - Test semantic colors per status (success/warning_style/muted)
      - Test symbol constants (SYM_NEW, SYM_UPDATED, SYM_UNCHANGED)
      - Test relative paths when base_path provided
      - Test muted labels: (new), (updated), (unchanged)
      - _Requirements: 15.1, 15.2, 15.3, 15.4_

    - [x] 3.1.2 Update format_diff_summary with semantic colors and relative paths
      - Add `base_path: Path | None = None` parameter
      - Use success for +, warning_style for ~, muted for =
      - Display paths relative to base_path when provided
      - _Requirements: 15.1, 15.2, 15.3, 15.4_

    - [x] 3.1.3 Write property tests for diff summary (Properties 9-10)
      - **Property 9: Diff summary uses semantic colors per status**
      - **Property 10: Diff summary displays relative paths**
      - **Validates: Requirements 7.2-7.4, 7.5, 9.4, 15.1-15.4**

  - [x] 3.2 Checkpoint — Diff summary
    - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Command output formatting

  - [x] 4.1 `ksm ls` output formatting

    - [x] 4.1.1 Write tests for updated `_format_grouped()`
      - Test accent bundle names, muted registry (no parens), muted timestamps
      - Test column alignment via _align_columns()
      - Test bold scope headers with blank line separator
      - Test verbose mode: 4-space indented muted file paths
      - Test empty state message to stderr
      - _Requirements: 6.1-6.7, 16.1_

    - [x] 4.1.2 Update `_format_grouped()` and `run_ls()` with semantic colors
      - Use accent for names, muted for registry/time, bold headers
      - Remove parentheses from registry names, add _align_columns()
      - _Requirements: 6.1-6.7, 16.1_

    - [x] 4.1.3 Write property tests for ls output (Properties 11-13)
      - **Property 11: ls output uses semantic colors and column alignment**
      - **Property 12: ls output groups by scope with bold headers**
      - **Property 13: ls verbose mode shows indented muted file paths**
      - **Validates: Requirements 6.1-6.6, 16.1**

  - [x] 4.2 `ksm add` output formatting

    - [x] 4.2.1 Write tests for add success output format
      - Test SYM_CHECK + success, accent bundle name, SYM_ARROW, muted scope
      - Test file paths relative to .kiro/
      - _Requirements: 7.1-7.5_

    - [x] 4.2.2 Update add command success output
      - Format: `✓ Installed <name> → <path> (<scope>)`
      - Pass base_path to format_diff_summary for relative paths
      - _Requirements: 7.1-7.5_

    - [x] 4.2.3 Write property test for add output (Property 14)
      - **Property 14: add success output format**
      - **Validates: Requirements 7.1**

  - [x] 4.3 `ksm rm` output formatting

    - [x] 4.3.1 Write tests for rm confirmation and result formatting
      - Test accent bundle name, info scope, muted file count/list
      - Test bold [y/n], SYM_CHECK + success result
      - Test missing file count in result summary
      - _Requirements: 8.1-8.4_

    - [x] 4.3.2 Update rm confirmation and result formatting
      - Use accent, info, muted, success, bold semantic colors
      - Format: `✓ Removed <name> — <count> files deleted (<scope>)`
      - Include missing file count when applicable
      - _Requirements: 8.1-8.4_

    - [x] 4.3.3 Write property tests for rm output (Properties 15-16)
      - **Property 15: rm confirmation uses correct semantic styles**
      - **Property 16: rm result format with missing file handling**
      - **Validates: Requirements 8.1-8.4**

  - [x] 4.4 `ksm sync` output formatting

    - [x] 4.4.1 Write tests for sync confirmation and result formatting
      - Test bold count header, accent names, muted scope/count with SYM_DOT
      - Test bold [y/n], per-bundle SYM_CHECK + success result
      - _Requirements: 9.1-9.4_

    - [x] 4.4.2 Update sync confirmation and result formatting
      - List bundles with accent name, muted scope · file count
      - Per-bundle result: `✓ Synced <name>` with diff details
      - _Requirements: 9.1-9.4_

    - [x] 4.4.3 Write property tests for sync output (Properties 17-18)
      - **Property 17: sync confirmation lists bundles with semantic styles**
      - **Property 18: sync per-bundle result format**
      - **Validates: Requirements 9.1-9.3**

  - [x] 4.5 `ksm info`, `search`, `registry ls`, `registry inspect`, `init`

    - [x] 4.5.1 Write tests for info output format
      - Test accent name, no colons on labels, muted values
      - Test flattened contents with SYM_DOT, no internal path
      - Test installed scope: success when installed, muted when not
      - _Requirements: 10.1-10.5_

    - [x] 4.5.2 Update info command output
      - Remove colons from labels, flatten contents, hide internal path
      - Use accent, muted, success semantic colors
      - _Requirements: 10.1-10.5_

    - [x] 4.5.3 Write tests for search output format
      - Test accent names, muted registry/types, column alignment
      - Test empty state with accent query and subtle suggestion
      - _Requirements: 11.1-11.4_

    - [x] 4.5.4 Update search command output
      - Use _align_columns(), accent names, muted metadata
      - Add empty state message with accent query
      - _Requirements: 11.1-11.4_

    - [x] 4.5.5 Write tests for registry ls and registry inspect output
      - Test single-line format with accent name, muted URL/count, alignment
      - Test inspect: bold name, muted URL, accent bundles, inline contents
      - Test no internal metadata displayed
      - _Requirements: 12.1-12.3, 13.1-13.4_

    - [x] 4.5.6 Update registry ls and registry inspect output
      - Single-line per registry with _align_columns()
      - Inspect: inline comma-separated items, no metadata
      - _Requirements: 12.1-12.3, 13.1-13.4_

    - [x] 4.5.7 Write tests for init output format
      - Test SYM_CHECK + success, info .kiro/, subtle hint
      - Test already-exists muted message
      - _Requirements: 14.1-14.3_

    - [x] 4.5.8 Update init command output
      - Format: `✓ Initialised .kiro/ in current directory`
      - Add subtle next-step hint, muted already-exists message
      - _Requirements: 14.1-14.3_

    - [x] 4.5.9 Write property tests for remaining commands (Properties 19-23)
      - **Property 19: info output format**
      - **Property 20: search output uses semantic colors and alignment**
      - **Property 21: registry ls single-line format with alignment**
      - **Property 22: registry inspect inline format**
      - **Property 23: CLI output has no trailing blank lines**
      - **Validates: Requirements 10.1-10.5, 11.1-11.3, 12.1-12.3, 13.1-13.4, 16.3**

  - [x] 4.6 Checkpoint — Command output formatting
    - Ensure all tests pass, ask the user if questions arise.

- [x] 5. TUI theming (`tui.py`)

  - [x] 5.1 Theme, containers, and footer bar

    - [x] 5.1.1 Write tests for KSM_THEME and app registration
      - Test theme color values match One Dark spec
      - Test all three apps register and activate KSM_THEME
      - _Requirements: 17.1, 17.2_

    - [x] 5.1.2 Implement KSM_THEME and register in all apps
      - Define Theme with primary, secondary, accent, success, warning, error, surface, panel
      - Register and activate in BundleSelectorApp, RemovalSelectorApp, ScopeSelectorApp
      - _Requirements: 17.1, 17.2_

    - [x] 5.1.3 Write tests for Container wrapping and footer bar
      - Test BundleSelectorApp/RemovalSelectorApp have Container#container
      - Test ScopeSelectorApp has Container#scope-container with width 40
      - Test footer bar presence with key hints
      - _Requirements: 18.1-18.3, 19.1-19.3_

    - [x] 5.1.4 Update compose() methods with Container wrapping and footer bar
      - Wrap content in Container(id="container") with border_title="ksm"
      - Add footer Static with key hints, replace instruction Static
      - ScopeSelectorApp: Container(id="scope-container"), width 40, max-height 12
      - _Requirements: 18.1-18.3, 19.1-19.3_

  - [x] 5.2 CSS overhaul and Rich Text

    - [x] 5.2.1 Write tests for CSS properties and OptionList styling
      - Test OptionList transparent background, no border
      - Test highlight/hover/focus background opacity values
      - Test scrollbar colors, Input border states
      - _Requirements: 20.1-20.6_

    - [x] 5.2.2 Update CSS for all three apps
      - BundleSelectorApp/RemovalSelectorApp: full CSS from design
      - ScopeSelectorApp: centered container CSS from design
      - _Requirements: 20.1-20.6_

    - [x] 5.2.3 Write tests for Rich Text OptionList items
      - Test bundle names use bold cyan Rich Text
      - Test installed badges use dim Rich Text
      - Test selected-count styled with bold accent
      - _Requirements: 21.1, 21.2_

    - [x] 5.2.4 Update OptionList items to use Rich Text formatting
      - Use `rich.text.Text` for label construction
      - Bold cyan bundle names, dim badges
      - _Requirements: 21.1, 21.2_

  - [x] 5.3 Checkpoint — TUI theming
    - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Each task references specific requirements for traceability
- Property tests use Hypothesis with dev (15 examples) and ci (100 examples) profiles
- All changes are additive — existing green/red/yellow/dim/bold functions remain unchanged
- Typography rules (Req 16) are enforced across all command updates
