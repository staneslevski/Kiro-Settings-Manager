# Requirements Document

## Introduction

The `ksm` CLI tool's visual presentation is outdated and visually flat — basic ANSI colors (green/red/yellow/dim/bold), no TUI theming, inconsistent output formatting, and no column alignment. This feature overhauls the entire UX visual layer across both CLI output and Textual TUI selectors to produce a modern, polished, scannable interface inspired by Toad (batrachianai/toad) and contemporary CLI tools like `gh`, `cargo`, and `pnpm`.

The full UX design recommendation is documented in `docs/ux-visual-design-recommendation.md`.

## Glossary

- **Color_Module**: The `src/ksm/color.py` module providing ANSI color wrapping functions and terminal capability detection
- **CLI_Output**: Text printed to stdout/stderr by ksm commands (ls, add, rm, sync, info, search, registry ls, registry inspect, init)
- **TUI**: The Textual-based terminal user interface apps in `src/ksm/tui.py` (BundleSelectorApp, RemovalSelectorApp, ScopeSelectorApp)
- **Semantic_Color**: A color function named by meaning (success, error, warning, accent, info, muted, subtle) rather than visual appearance (green, red, yellow)
- **ANSI_16**: The base 16-color ANSI palette (codes 30-37 standard, 90-97 bright) supported by all color-capable terminals
- **Bright_Variant**: ANSI codes 90-97 that render more vibrantly and consistently across terminal themes than standard codes 30-37
- **Column_Alignment**: Padding tabular output so that columns line up vertically using calculated max-width per column
- **Symbol_System**: A centralized set of Unicode glyphs (✓, ✗, →, ·) with ASCII fallbacks (*, x, ->, -) for non-Unicode terminals
- **Footer_Bar**: A Toad-inspired bottom bar in TUI apps showing contextual key hints (Navigate, Toggle, Confirm, Cancel)
- **KSM_Theme**: A custom Textual Theme with One Dark-inspired colors registered in all TUI apps
- **Graceful_Degradation**: Adapting visual output based on terminal capabilities (full color, 8-color, NO_COLOR, TERM=dumb, non-TTY)
- **Error_Module**: The `src/ksm/errors.py` module providing standardized error, warning, and deprecation message formatting
- **Diff_Summary**: The file-level change summary produced by `src/ksm/copier.py` showing new/updated/unchanged files after install or sync

## Requirements

### Requirement 1: Semantic Color Palette

**User Story:** As a developer using ksm, I want output colors to convey meaning through a modern, vibrant palette, so that I can quickly distinguish success states, errors, warnings, and informational content at a glance.

#### Acceptance Criteria

1. THE Color_Module SHALL provide semantic color functions: `success` (bright green, code 92), `error_style` (bright red, code 91), `warning_style` (bright yellow, code 93), `accent` (bright cyan, code 96), `info` (bright blue, code 94), `muted` (dim, code 2), and `subtle` (dim italic, code 2;3)
2. THE Color_Module SHALL provide a `style()` function that accepts multiple ANSI code strings and combines them into a single escape sequence
3. THE Color_Module SHALL retain the existing `green`, `red`, `yellow`, `dim`, and `bold` functions as backward-compatible aliases
4. WHEN the Color_Module applies a Bright_Variant code (90-97) on an 8-color terminal, THE Color_Module SHALL downgrade the code to the corresponding standard code (30-37)
5. THE Color_Module SHALL provide a `_strip_ansi()` function that removes all ANSI escape sequences from a string for accurate width calculation

### Requirement 2: Terminal Capability Detection

**User Story:** As a developer running ksm in diverse environments (SSH, CI, piped output, legacy terminals), I want the tool to detect my terminal's capabilities and adapt its output, so that I always get readable output regardless of environment.

#### Acceptance Criteria

1. THE Color_Module SHALL provide a `_color_level()` function that returns an integer: 0 (no color), 1 (8-color), 2 (16-color), 3 (256-color), or 4 (true color)
2. WHEN the `NO_COLOR` environment variable is set, THE Color_Module SHALL return color level 0
3. WHEN the `TERM` environment variable equals `dumb`, THE Color_Module SHALL return color level 0
4. WHEN the output stream is not a TTY, THE Color_Module SHALL return color level 0
5. WHEN the `COLORTERM` environment variable equals `truecolor` or `24bit`, THE Color_Module SHALL return color level 4
6. WHEN the `TERM` environment variable contains `256color`, THE Color_Module SHALL return color level 3
7. THE Color_Module SHALL default to color level 2 (16-color) for TTY streams that do not match higher levels

### Requirement 3: Unicode Symbol System

**User Story:** As a developer, I want ksm to use meaningful Unicode symbols (✓, ✗, →, ·) in its output with automatic ASCII fallbacks, so that output is both visually polished on modern terminals and readable on legacy ones.

#### Acceptance Criteria

1. THE Color_Module SHALL provide a `_supports_unicode()` function that checks terminal encoding and the `TERM` environment variable
2. WHEN the terminal supports Unicode, THE Color_Module SHALL export symbol constants using Unicode glyphs: `SYM_CHECK` = ✓, `SYM_CROSS` = ✗, `SYM_ARROW` = →, `SYM_DOT` = ·
3. WHEN the terminal does not support Unicode, THE Color_Module SHALL export ASCII fallback symbols: `SYM_CHECK` = *, `SYM_CROSS` = x, `SYM_ARROW` = ->, `SYM_DOT` = -
4. WHEN `TERM` equals `dumb`, THE `_supports_unicode()` function SHALL return False
5. THE Color_Module SHALL also export `SYM_NEW` = +, `SYM_UPDATED` = ~, and `SYM_UNCHANGED` = = as fixed symbols that do not require Unicode detection

### Requirement 4: Column Alignment Utility

**User Story:** As a developer reading ksm list output, I want tabular data (bundle names, registries, timestamps) to be column-aligned, so that I can scan information quickly without visual noise.

#### Acceptance Criteria

1. THE Color_Module SHALL provide an `_align_columns()` function that accepts a list of row tuples and a gap parameter
2. WHEN aligning columns, THE `_align_columns()` function SHALL calculate column widths using ANSI-stripped string lengths
3. THE `_align_columns()` function SHALL pad all columns except the last column in each row
4. WHEN the input list is empty, THE `_align_columns()` function SHALL return an empty list

### Requirement 5: Error and Warning Message Formatting

**User Story:** As a developer encountering errors in ksm, I want error and warning messages to use lowercase prefixes and semantic colors with clear visual hierarchy, so that messages feel conversational and modern rather than alarming.

#### Acceptance Criteria

1. THE Error_Module SHALL format error messages with a lowercase `error:` prefix styled using the `error_style` semantic color
2. THE Error_Module SHALL format warning messages with a lowercase `warning:` prefix styled using the `warning_style` semantic color
3. THE Error_Module SHALL format deprecation messages with a lowercase `deprecated:` prefix styled using the `warning_style` semantic color
4. WHEN formatting error messages, THE Error_Module SHALL style the explanatory "why" line using the `muted` semantic color
5. WHEN formatting error messages, THE Error_Module SHALL style the actionable "fix" line using the `subtle` semantic color
6. WHEN an error message references a bundle name, THE Error_Module SHALL style the bundle name using the `accent` semantic color

### Requirement 6: `ksm ls` Output Formatting

**User Story:** As a developer listing installed bundles, I want the output to be column-aligned with color-coded bundle names and muted metadata, so that I can scan my installed bundles at a glance.

#### Acceptance Criteria

1. THE `ls` command SHALL display bundle names styled with the `accent` semantic color
2. THE `ls` command SHALL display registry names and relative timestamps styled with the `muted` semantic color
3. THE `ls` command SHALL column-align bundle names, registry names, and timestamps using `_align_columns()`
4. THE `ls` command SHALL display registry names without parentheses
5. THE `ls` command SHALL group output by scope with bold section headers (`Local bundles:`, `Global bundles:`) separated by one blank line
6. WHEN the `-v` flag is provided, THE `ls` command SHALL display installed file paths indented 4 spaces and styled with the `muted` semantic color
7. WHEN no bundles are installed, THE `ls` command SHALL print a helpful message to stderr and exit 0

### Requirement 7: `ksm add` Success Output Formatting

**User Story:** As a developer installing a bundle, I want the success output to clearly show what was installed, where it went, and what changed per file, so that I have immediate confidence the operation succeeded.

#### Acceptance Criteria

1. THE `add` command SHALL display a success line in the format: `✓ Installed <bundle-name> → <scope-path> (<scope>)` using `SYM_CHECK` styled with `success`, the bundle name styled with `accent`, and the scope indicator styled with `muted`
2. THE `add` command SHALL display new files with a `+` symbol styled with `success` and a `(new)` label styled with `muted`
3. THE `add` command SHALL display updated files with a `~` symbol styled with `warning_style` and an `(updated)` label styled with `muted`
4. THE `add` command SHALL display unchanged files with a `=` symbol styled with `muted` and an `(unchanged)` label styled with `muted`
5. THE `add` command SHALL display file paths relative to `.kiro/`, not as absolute paths

### Requirement 8: `ksm rm` Confirmation and Result Formatting

**User Story:** As a developer removing a bundle, I want a clear confirmation prompt showing what will be deleted and a concise result summary, so that I can make informed decisions and verify the outcome.

#### Acceptance Criteria

1. THE `rm` command SHALL display a confirmation prompt showing the bundle name styled with `accent`, the scope styled with `info`, the file count styled with `muted`, and the list of files to be removed styled with `muted`
2. THE `rm` command SHALL display the confirmation question `Continue? [y/n]` with the `[y/n]` styled with `bold`
3. THE `rm` command SHALL display a result line in the format: `✓ Removed <bundle-name> — <count> files deleted (<scope>)` using `SYM_CHECK` styled with `success`, the bundle name styled with `accent`, and the summary styled with `muted`
4. WHEN some files were already missing, THE `rm` command SHALL include the count of missing files in the result summary (e.g., `3 files deleted, 1 already missing`)

### Requirement 9: `ksm sync` Confirmation and Result Formatting

**User Story:** As a developer syncing bundles, I want a clear confirmation listing each bundle with its scope and file count, and per-bundle results showing what changed, so that I understand the impact before and after syncing.

#### Acceptance Criteria

1. THE `sync` command SHALL display a confirmation prompt listing each bundle to be synced with the bundle name styled with `accent` and scope/file count styled with `muted`, preceded by a header showing the total bundle count styled with `bold`
2. THE `sync` command SHALL display the confirmation question `This will overwrite configuration files. Continue? [y/n]` with `[y/n]` styled with `bold`
3. THE `sync` command SHALL display per-bundle results in the format: `✓ Synced <bundle-name>` using `SYM_CHECK` styled with `success` and the bundle name styled with `accent`
4. THE `sync` command SHALL display per-file change details using the same `+`/`~`/`=` symbol and color conventions as the `add` command (Requirement 7)

### Requirement 10: `ksm info` Output Formatting

**User Story:** As a developer inspecting a bundle, I want a clean, compact summary showing the bundle name, registry, contents, and install status without internal implementation details, so that I get only the information I need.

#### Acceptance Criteria

1. THE `info` command SHALL display the bundle name styled with `accent`
2. THE `info` command SHALL display metadata labels (Registry, Contents, Installed) aligned without colons, with values styled with `muted`
3. THE `info` command SHALL flatten the contents listing to a single line with subdirectory names and item counts separated by `SYM_DOT` (e.g., `steering/ 2 items · skills/ 1 item`)
4. THE `info` command SHALL NOT display the internal file path of the bundle
5. THE `info` command SHALL display the installed scope styled with `success` when installed, or `muted` when not installed

### Requirement 11: `ksm search` Output Formatting

**User Story:** As a developer searching for bundles, I want results to be column-aligned with highlighted bundle names and muted metadata, and a helpful message when no results are found, so that I can quickly find what I need.

#### Acceptance Criteria

1. THE `search` command SHALL display bundle names styled with `accent`
2. THE `search` command SHALL display registry names and content type lists styled with `muted`
3. THE `search` command SHALL column-align bundle names, registry names, and content types using `_align_columns()`
4. WHEN no results are found, THE `search` command SHALL display the search term styled with `accent` and a next-step suggestion styled with `subtle`

### Requirement 12: `ksm registry ls` Output Formatting

**User Story:** As a developer listing registries, I want a compact single-line-per-registry format showing the name, URL, and bundle count, so that I can quickly see all my configured sources.

#### Acceptance Criteria

1. THE `registry ls` command SHALL display each registry on a single line with the name styled with `accent`, the URL (or `(local)`) styled with `muted`, and the bundle count styled with `muted`
2. THE `registry ls` command SHALL column-align registry names, URLs, and bundle counts using `_align_columns()`
3. THE `registry ls` command SHALL NOT display the internal cache path by default

### Requirement 13: `ksm registry inspect` Output Formatting

**User Story:** As a developer inspecting a registry, I want to see each bundle's contents listed compactly with items inline, so that I can quickly understand what a registry offers without excessive vertical space.

#### Acceptance Criteria

1. THE `registry inspect` command SHALL display the registry name styled with `bold` and the URL styled with `muted` on the header line
2. THE `registry inspect` command SHALL display each bundle name styled with `accent`
3. THE `registry inspect` command SHALL display subdirectory contents inline as comma-separated item names on a single line per subdirectory, with the subdirectory name styled with `muted`
4. THE `registry inspect` command SHALL NOT display internal metadata (Default, Path, Bundles count)

### Requirement 14: `ksm init` Output Formatting

**User Story:** As a developer initialising a workspace, I want a clear success message with a next-step hint, so that I know the operation succeeded and what to do next.

#### Acceptance Criteria

1. THE `init` command SHALL display a success line in the format: `✓ Initialised .kiro/ in current directory` using `SYM_CHECK` styled with `success` and `.kiro/` styled with `info`
2. THE `init` command SHALL display a next-step hint styled with `subtle` (e.g., `Run 'ksm add' to install your first bundle.`)
3. WHEN `.kiro/` already exists, THE `init` command SHALL display a muted message: `Already initialised — .kiro/ exists.`

### Requirement 15: Diff Summary Formatting

**User Story:** As a developer installing or syncing bundles, I want the file change summary to use relative paths and semantic colors, so that the output is concise and meaningful.

#### Acceptance Criteria

1. THE Diff_Summary SHALL display file paths relative to `.kiro/`, not as absolute paths
2. THE Diff_Summary SHALL style new file entries with `SYM_NEW` styled with `success` and the `(new)` label styled with `muted`
3. THE Diff_Summary SHALL style updated file entries with `SYM_UPDATED` styled with `warning_style` and the `(updated)` label styled with `muted`
4. THE Diff_Summary SHALL style unchanged file entries with `SYM_UNCHANGED` styled with `muted` and the `(unchanged)` label styled with `muted`

### Requirement 16: Typography and Spacing Rules

**User Story:** As a developer reading ksm output, I want consistent spacing, indentation, and separators across all commands, so that the output feels cohesive and professionally designed.

#### Acceptance Criteria

1. ALL CLI_Output SHALL use one blank line between scope groups (e.g., between Local and Global sections in `ls`)
2. ALL CLI_Output SHALL use 2-space indentation for first-level content and 4-space indentation for nested content (e.g., file lists)
3. ALL CLI_Output SHALL NOT produce trailing blank lines
4. ALL CLI_Output SHALL use `SYM_DOT` (· or -) as the inline metadata separator character
5. ALL section headers in CLI_Output SHALL be styled with `bold`

### Requirement 17: Textual TUI Custom Theme

**User Story:** As a developer using ksm's interactive selectors, I want a polished, branded dark theme with One Dark-inspired colors, so that the TUI feels modern and visually cohesive with the CLI output.

#### Acceptance Criteria

1. THE TUI SHALL define a `KSM_THEME` using Textual's `Theme` class with One Dark-inspired color values: primary `#56b6c2` (cyan), secondary `#61afef` (blue), accent `#56b6c2` (cyan), success `#98c379` (green), warning `#e5c07b` (yellow), error `#e06c75` (red), surface `#282c34` (dark background), panel `#21252b` (darker panels)
2. ALL three TUI apps (BundleSelectorApp, RemovalSelectorApp, ScopeSelectorApp) SHALL register and activate the `KSM_THEME` on initialisation

### Requirement 18: TUI Container and Border Styling

**User Story:** As a developer using ksm's interactive selectors, I want the TUI content wrapped in a bordered container with a title, so that the interface feels structured and polished rather than bare.

#### Acceptance Criteria

1. THE BundleSelectorApp and RemovalSelectorApp SHALL wrap their content in a `Container` widget with id `container`
2. THE `#container` widget SHALL have a rounded border styled with the accent color and a bold border title of `ksm`
3. THE ScopeSelectorApp SHALL wrap its content in a centered `Container` with id `scope-container`, a rounded accent border, a bold border title, a fixed width of 40, and auto height with max-height of 12

### Requirement 19: TUI Footer Bar with Key Hints

**User Story:** As a developer using ksm's interactive selectors, I want a footer bar at the bottom showing contextual key hints (Navigate, Toggle, Confirm, Cancel), so that I always know what keys to press without guessing.

#### Acceptance Criteria

1. THE BundleSelectorApp and RemovalSelectorApp SHALL display a Footer_Bar docked to the bottom with key hints: `↑↓ Navigate`, `Space Toggle`, `Enter Confirm`, `Esc Cancel`
2. THE Footer_Bar SHALL have a background of accent color at 15% opacity and key names styled with bold accent color
3. THE Footer_Bar SHALL have a height of 1 row

### Requirement 20: TUI OptionList and Input Styling

**User Story:** As a developer browsing bundles in the TUI, I want the option list and filter input to have visible focus states, subtle hover effects, and styled scrollbars, so that the interactive experience feels responsive and polished.

#### Acceptance Criteria

1. THE `OptionList` widget SHALL have a transparent background with no border
2. THE highlighted option in `OptionList` SHALL have a background of accent color at 15% opacity with bold text, increasing to 25% when the `OptionList` is focused
3. THE hovered option in `OptionList` SHALL have a background of accent color at 8% opacity
4. THE `OptionList` scrollbar SHALL use accent color at 30% opacity, increasing to 60% on hover and 100% on active
5. THE `Input` widget SHALL have a tall border styled with accent color at 30% opacity, increasing to full accent on focus
6. THE `Input` widget SHALL have an error state border styled with the error color

### Requirement 21: TUI OptionList Rich Text Formatting

**User Story:** As a developer browsing bundles in the TUI selector, I want bundle names to be color-highlighted and installed badges to be visually muted, so that I can quickly distinguish available bundles and their status.

#### Acceptance Criteria

1. THE OptionList items SHALL use Rich Text formatting with bundle names styled in bold cyan and installed/status badges styled in dim
2. THE selected-count indicator SHALL be styled with bold accent color and right-aligned at the bottom of the container

