# Requirements Document

## Introduction

This spec covers two related improvements to the ksm CLI: (1) a comprehensive color scheme that applies the existing but unused `green()`, `red()`, and `yellow()` color functions across all command output, and (2) an interactive scope selection step in the `ksm add` workflow that lets users choose between local and global installation without relying on CLI flags. Together, these changes make the tool's output scannable at a glance and its interactive flows self-contained.

The color module (`src/ksm/color.py`) already defines `green()`, `red()`, `yellow()`, `dim()`, and `bold()` with proper `NO_COLOR`, `TERM=dumb`, and non-TTY detection. The module already accepts an optional `stream` parameter for TTY checks. Only `bold` and `dim` are currently imported anywhere. This spec activates the remaining color functions with a consistent semantic mapping and ensures color is never the sole indicator of meaning (symbols and text labels always accompany color).

The scope selection step addresses a gap in the interactive flow: when using `-i` mode, scope defaults to local with no way to choose global. The `-l`/`-g` flags work for non-interactive use, but interactive users should be able to pick scope as part of the guided flow.

## Glossary

- **Color_Module**: The utility module at `src/ksm/color.py` providing `green()`, `red()`, `yellow()`, `dim()`, and `bold()` ANSI formatting functions with automatic TTY, `NO_COLOR`, and `TERM=dumb` detection. Each function accepts an optional `stream` parameter.
- **Selector**: The interactive terminal UI in `src/ksm/selector.py` that lets users pick bundles via arrow keys (raw mode) or numbered-list fallback
- **Scope**: Either "local" (project `.kiro/`) or "global" (`~/.kiro/`) installation target
- **Scope_Selection_Step**: A new interactive prompt presented after bundle selection that lets the user choose between local and global scope
- **Diff_Summary**: The file-level change summary produced by `format_diff_summary()` in `src/ksm/copier.py`, using `+` (new), `~` (updated), `=` (unchanged) symbols
- **Error_Formatter**: The `format_error()` function in `src/ksm/errors.py` that produces three-line error messages (what, why, fix)
- **Warning_Formatter**: The `format_warning()` function in `src/ksm/errors.py` that produces two-line warning messages (what, detail)
- **Deprecation_Formatter**: The `format_deprecation()` function in `src/ksm/errors.py` that produces deprecation notices with old/new names and timeline
- **Numbered_List_Prompt**: The non-interactive fallback in the Selector that displays numbered items and reads a number from stdin, used when raw terminal mode is unavailable
- **Raw_Mode**: The terminal mode using `tty`/`termios` where keypresses are read individually without line buffering
- **ManifestEntry**: A dataclass representing an installed bundle with `bundle_name`, `scope`, `source_registry`, `installed_files`, and timestamps

## Requirements

### Requirement 1: Colorize Error Messages

**User Story:** As a developer, I want error messages displayed in red, so that I can immediately distinguish errors from normal output when scanning terminal output.

#### Acceptance Criteria

1. WHEN `format_error()` produces an error message, THE Error_Formatter SHALL wrap the "Error:" prefix in red using the Color_Module. The caller is responsible for passing `stream=sys.stderr` at the call site since `format_error()` is a pure string formatter.
2. WHEN the `NO_COLOR` environment variable is set, THE Color_Module SHALL produce plain text without ANSI codes
3. WHEN stderr is not a TTY, THE Color_Module SHALL produce plain text without ANSI codes (when `stream=sys.stderr` is passed)
4. THE Error_Formatter SHALL preserve the existing three-line format (what, why, fix) and only apply color to the "Error:" prefix
5. WHEN `TERM` is set to `dumb`, THE Color_Module SHALL produce plain text without ANSI codes

### Requirement 2: Colorize Warning and Deprecation Messages

**User Story:** As a developer, I want warning and deprecation messages displayed in yellow, so that I can distinguish them from errors and normal output.

#### Acceptance Criteria

1. WHEN `format_warning()` produces a warning message, THE Warning_Formatter SHALL wrap the "Warning:" prefix in yellow using the Color_Module. The caller passes `stream=sys.stderr` at the call site.
2. WHEN `format_deprecation()` produces a deprecation message, THE Deprecation_Formatter SHALL wrap the "Deprecated:" prefix in yellow using the Color_Module. The caller passes `stream=sys.stderr` at the call site.
3. WHEN the `NO_COLOR` environment variable is set, THE Warning_Formatter and Deprecation_Formatter SHALL produce plain text without ANSI codes
4. THE Warning_Formatter SHALL preserve the existing two-line format and only apply color to the "Warning:" prefix
5. THE Deprecation_Formatter SHALL preserve the existing two-line format and only apply color to the "Deprecated:" prefix

### Requirement 3: Colorize Success Messages After Add, Rm, and Sync

**User Story:** As a developer, I want success messages after bundle operations displayed in green, so that I can confirm at a glance that an operation completed successfully.

#### Acceptance Criteria

1. WHEN `ksm add` completes successfully, THE CLI SHALL print a green success prefix (e.g., "Installed:") before the diff summary, using `stream=sys.stderr`
2. WHEN `ksm rm` completes successfully, THE CLI SHALL wrap the "Removed" prefix of the `_format_result()` output in green using the Color_Module with `stream=sys.stderr`
3. WHEN `ksm sync` completes successfully for a bundle, THE CLI SHALL print a green success prefix (e.g., "Synced:") before the diff summary, using `stream=sys.stderr`
4. WHEN the `NO_COLOR` environment variable is set, THE CLI SHALL produce plain text success messages without ANSI codes
5. THE CLI SHALL always include descriptive text alongside the green color so that color is not the sole indicator of success

### Requirement 4: Colorize File Diff Summary Symbols

**User Story:** As a developer, I want the file diff symbols (`+`, `~`, `=`) in color, so that I can quickly scan which files are new, updated, or unchanged.

#### Acceptance Criteria

1. WHEN `format_diff_summary()` renders a line with status `NEW` (`+`), THE Diff_Summary SHALL wrap the `+` symbol and the `(new)` label in green using the Color_Module
2. WHEN `format_diff_summary()` renders a line with status `UPDATED` (`~`), THE Diff_Summary SHALL wrap the `~` symbol and the `(updated)` label in yellow using the Color_Module
3. WHEN `format_diff_summary()` renders a line with status `UNCHANGED` (`=`), THE Diff_Summary SHALL wrap the `=` symbol and the `(unchanged)` label in dim using the Color_Module
4. THE `format_diff_summary()` function SHALL accept an optional `stream` parameter (defaulting to `sys.stderr`) to pass through to Color_Module functions for correct TTY detection
5. WHEN the `NO_COLOR` environment variable is set, THE Diff_Summary SHALL produce plain text without ANSI codes

### Requirement 5: Colorize Bundle Names in List Output (Verify Existing)

**User Story:** As a developer, I want bundle names in `ksm ls` output displayed in bold, so that they stand out from the surrounding metadata.

Note: `ksm ls` already uses `bold()` and `dim()` from the Color_Module. This requirement verifies existing behavior and adds any missing color treatment.

#### Acceptance Criteria

1. THE CLI SHALL wrap bundle names in `ksm ls` output in bold using the Color_Module (already implemented — verify)
2. THE CLI SHALL wrap source registry names and relative timestamps in `ksm ls` output in dim using the Color_Module (already implemented — verify)
3. THE CLI SHALL wrap scope section headers ("Local bundles:" and "Global bundles:") in bold using the Color_Module (already implemented — verify)
4. WHEN the `NO_COLOR` environment variable is set, THE CLI SHALL produce plain text `ksm ls` output without ANSI codes

### Requirement 6: Colorize Interactive Selector UI Elements

**User Story:** As a developer using the interactive selector, I want visual highlighting for the selected item, installed badges, and header text, so that the UI is easy to read and navigate.

#### Acceptance Criteria

1. WHEN rendering the add selector, THE Selector SHALL wrap the currently highlighted bundle name in bold using the Color_Module with `stream=sys.stderr`
2. WHEN rendering the add selector, THE Selector SHALL wrap the `[installed]` badge in dim using the Color_Module with `stream=sys.stderr`
3. WHEN rendering the add or removal selector, THE Selector SHALL wrap the header text ("Select a bundle to install" / "Select a bundle to remove") in bold using the Color_Module with `stream=sys.stderr`
4. WHEN rendering the add or removal selector, THE Selector SHALL wrap the instruction line ("↑/↓ navigate, Enter select, q quit") in dim using the Color_Module with `stream=sys.stderr`
5. WHEN the `NO_COLOR` environment variable is set, THE Selector SHALL produce plain text without ANSI codes
6. WHEN rendering the removal selector, THE Selector SHALL wrap the scope label (e.g., `[local]`) in dim using the Color_Module with `stream=sys.stderr`
7. WHEN the user types filter text in the selector, THE Selector SHALL wrap the filter prompt (e.g., "Filter: ...") in dim using the Color_Module with `stream=sys.stderr`

### Requirement 7: Colorize Rm Confirmation Prompt

**User Story:** As a developer confirming a bundle removal, I want the file list and scope information in the confirmation prompt to use color, so that I can quickly assess what will be deleted.

#### Acceptance Criteria

1. WHEN displaying the rm confirmation prompt, THE CLI SHALL wrap each file path in dim using the Color_Module with `stream=sys.stderr`
2. WHEN displaying the rm confirmation prompt, THE CLI SHALL wrap the scope description (e.g., ".kiro/" or "~/.kiro/") in bold using the Color_Module with `stream=sys.stderr`
3. WHEN the `NO_COLOR` environment variable is set, THE CLI SHALL produce a plain text confirmation prompt without ANSI codes
4. THE CLI SHALL preserve the existing confirmation prompt structure and text content, applying color only as visual enhancement

### Requirement 8: Colorize Registry Commands Output (Verify and Extend)

**User Story:** As a developer managing registries, I want registry names, URLs, and bundle counts in color, so that I can scan registry information quickly.

Note: `ksm registry ls` and `ksm registry inspect` already use `bold()` and `dim()`. This requirement verifies existing behavior and adds any missing color treatment.

#### Acceptance Criteria

1. WHEN `ksm registry ls` displays registry entries, THE CLI SHALL wrap registry names in bold using the Color_Module (already implemented — verify)
2. WHEN `ksm registry ls` displays registry entries, THE CLI SHALL wrap URLs in dim using the Color_Module (verify — currently only `(local)` placeholder is dimmed)
3. WHEN `ksm registry ls` displays registry entries, THE CLI SHALL wrap bundle counts in dim using the Color_Module (already implemented — verify)
4. WHEN `ksm registry inspect` displays bundle details, THE CLI SHALL wrap bundle names in bold and subdirectory details in dim using the Color_Module (already implemented — verify)
5. WHEN the `NO_COLOR` environment variable is set, THE CLI SHALL produce plain text registry output without ANSI codes

### Requirement 9: Colorize Search and Info Command Output (Verify and Extend)

**User Story:** As a developer searching for or inspecting bundles, I want bundle names and metadata styled consistently with the rest of the CLI, so that the output is visually coherent.

Note: `ksm search` and `ksm info` already use `bold()` and `dim()`. This requirement verifies existing behavior and adds the green installed status.

#### Acceptance Criteria

1. WHEN `ksm search` displays results, THE CLI SHALL wrap bundle names in bold and registry names in dim using the Color_Module (already implemented — verify)
2. WHEN `ksm info` displays bundle details, THE CLI SHALL wrap the bundle name in bold, paths in dim, and the installed status in green (if installed) or dim (if not) using the Color_Module
3. WHEN the `NO_COLOR` environment variable is set, THE CLI SHALL produce plain text search and info output without ANSI codes

### Requirement 10: Colorize Sync Confirmation Prompt

**User Story:** As a developer confirming a sync operation, I want the confirmation prompt to use color for bundle names and scope information, so that I can quickly assess what will be synced.

#### Acceptance Criteria

1. WHEN displaying the sync confirmation prompt, THE CLI SHALL wrap bundle names in bold using the Color_Module with `stream=sys.stderr`
2. WHEN displaying the sync confirmation prompt, THE CLI SHALL wrap the scope description (e.g., ".kiro/", "~/.kiro/", or ".kiro/ and ~/.kiro/") in bold using the Color_Module with `stream=sys.stderr`
3. WHEN the `NO_COLOR` environment variable is set, THE CLI SHALL produce a plain text confirmation prompt without ANSI codes

### Requirement 11: Interactive Scope Selection Step in Add Flow

**User Story:** As a developer using `ksm add -i`, I want to choose between local and global installation scope as part of the interactive flow, so that I do not need to remember the `-l`/`-g` flags.

#### Acceptance Criteria

1. WHEN the user selects a bundle in the interactive add flow and neither `-l` nor `-g` was provided on the command line, THE Selector SHALL present a scope selection step with two options: "Local (.kiro/)" and "Global (~/.kiro/)"
2. THE Scope_Selection_Step SHALL default to "Local (.kiro/)" as the pre-selected option
3. WHEN the user presses Enter without changing the selection, THE Scope_Selection_Step SHALL return "local" as the chosen scope
4. WHEN the user selects "Global (~/.kiro/)" and presses Enter, THE Scope_Selection_Step SHALL return "global" as the chosen scope
5. WHEN `-l` or `-g` was explicitly provided on the command line, THE CLI SHALL skip the Scope_Selection_Step and use the flag-specified scope
6. WHEN the user presses `q` or Escape during the Scope_Selection_Step, THE CLI SHALL abort the add operation and return exit code 0
7. WHEN stdin is not a TTY, THE CLI SHALL default to "local" scope and skip the Scope_Selection_Step

### Requirement 12: Scope Selection in Raw Mode

**User Story:** As a developer using a terminal that supports raw mode, I want the scope selection step to use arrow-key navigation, so that the experience is consistent with the bundle selector.

#### Acceptance Criteria

1. WHEN raw mode is available, THE Scope_Selection_Step SHALL render two options with a `>` prefix on the highlighted option and allow navigation with up/down arrow keys
2. WHEN the user presses Enter in raw mode, THE Scope_Selection_Step SHALL return the currently highlighted scope option
3. THE Scope_Selection_Step SHALL render a header line ("Select installation scope:") and an instruction line ("↑/↓ navigate, Enter select, q quit") above the options
4. THE Scope_Selection_Step SHALL render to stderr, not stdout
5. THE Scope_Selection_Step SHALL render inline (not use alternate screen buffer) since it has only two options
6. WHEN the user presses Ctrl+C (SIGINT) during the Scope_Selection_Step, THE CLI SHALL restore terminal settings and abort cleanly with exit code 0

### Requirement 13: Scope Selection in Numbered-List Fallback Mode

**User Story:** As a developer on a platform without raw terminal mode, I want the scope selection step to fall back to a numbered-list prompt, so that I can still choose scope interactively.

#### Acceptance Criteria

1. WHEN raw mode is not available, THE Scope_Selection_Step SHALL display a numbered list: `1. Local (.kiro/)` and `2. Global (~/.kiro/)`
2. WHEN the user enters `1` or presses Enter with no input, THE Scope_Selection_Step SHALL return "local"
3. WHEN the user enters `2`, THE Scope_Selection_Step SHALL return "global"
4. WHEN the user enters `q`, THE Scope_Selection_Step SHALL return no selection (abort)
5. IF the user enters an invalid value, THEN THE Scope_Selection_Step SHALL print an error and re-prompt
6. WHEN `TERM` is set to `dumb`, THE Scope_Selection_Step SHALL use the Numbered_List_Prompt fallback instead of raw mode

### Requirement 14: Interactive Scope Selection Step in Rm Flow

**User Story:** As a developer using `ksm rm -i`, I want the scope selection behavior to be consistent with the add flow, so that the interactive experience is predictable across commands.

#### Acceptance Criteria

1. WHEN the user selects a bundle in the interactive rm flow, THE Selector SHALL use the scope from the selected ManifestEntry (since removal entries already have a known scope)
2. THE CLI SHALL not present a separate scope selection step during `ksm rm -i` because the ManifestEntry already contains the scope
3. WHEN `-l` or `-g` is provided alongside `-i` for `ksm rm`, THE CLI SHALL filter the removal list to only show bundles matching the specified scope

### Requirement 15: Scope Selection Integrates with Add Command

**User Story:** As a developer, I want the scope chosen in the interactive selector to be used for the actual installation, so that the interactive flow is end-to-end.

#### Acceptance Criteria

1. WHEN the Scope_Selection_Step returns "local", THE CLI SHALL install the bundle to the project `.kiro/` directory
2. WHEN the Scope_Selection_Step returns "global", THE CLI SHALL install the bundle to the user `~/.kiro/` directory
3. WHEN the Scope_Selection_Step is skipped because `-l` or `-g` was provided, THE CLI SHALL use the flag-specified scope as before
4. THE CLI SHALL pass the selected scope to `install_bundle()` and record it in the Manifest

### Requirement 16: Scope Selector Color Treatment

**User Story:** As a developer, I want the scope selection step to use the same color conventions as the bundle selector, so that the UI feels consistent.

#### Acceptance Criteria

1. WHEN rendering the scope selector in raw mode, THE Scope_Selection_Step SHALL wrap the header ("Select installation scope:") in bold using the Color_Module with `stream=sys.stderr`
2. WHEN rendering the scope selector in raw mode, THE Scope_Selection_Step SHALL wrap the instruction line in dim using the Color_Module with `stream=sys.stderr`
3. WHEN rendering the scope selector in raw mode, THE Scope_Selection_Step SHALL wrap the highlighted option in bold using the Color_Module with `stream=sys.stderr`
4. WHEN the `NO_COLOR` environment variable is set, THE Scope_Selection_Step SHALL not emit ANSI color codes in its rendered output
5. WHEN `TERM` is set to `dumb`, THE Scope_Selection_Step SHALL use the Numbered_List_Prompt fallback (no ANSI codes)
6. WHEN stderr is not a TTY, THE Scope_Selection_Step SHALL use the Numbered_List_Prompt fallback
