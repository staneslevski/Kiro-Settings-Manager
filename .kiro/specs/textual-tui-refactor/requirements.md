# Requirements Document

## Introduction

The ksm CLI tool currently uses a hand-rolled raw terminal UI in `src/ksm/selector.py` built on `tty`/`termios` with manual ANSI escape sequences. This implementation is buggy, hard to maintain, and tightly couples rendering, input handling, and terminal state management. This spec replaces the raw terminal UI with the Textual TUI library while preserving all existing user-facing behavior: bundle selection, scope selection, filtering, multi-select, and non-TTY fallback.

Textual becomes the first external runtime dependency. The refactor targets only the interactive terminal UI layer (`selector.py`). Command modules, CLI argument parsing, and non-interactive output remain unchanged. The existing `color.py` module continues to serve non-Textual output (error messages, diff summaries, success prefixes). Textual's own styling system handles all styling within Textual apps.

## Glossary

- **Textual**: A Python TUI framework (github.com/Textualize/textual) that provides widgets, layout, event handling, and styling for terminal applications
- **Textual_App**: A `textual.app.App` subclass that manages the Textual application lifecycle, screen rendering, and event loop
- **Selector_Module**: The module at `src/ksm/selector.py` containing all interactive terminal UI functions
- **Bundle_Selector_App**: A Textual_App that replaces the raw-mode `interactive_select()` function for bundle selection
- **Removal_Selector_App**: A Textual_App that replaces the raw-mode `interactive_removal_select()` function for removal selection
- **Scope_Selector_App**: A Textual_App that replaces the raw-mode `scope_select()` function for scope selection
- **Raw_Mode**: The current terminal mode using `tty`/`termios` where keypresses are read individually without line buffering
- **Numbered_List_Fallback**: The non-interactive fallback that displays numbered items and reads a number from stdin, used when Textual cannot run (non-TTY, TERM=dumb, etc.)
- **Color_Module**: The utility module at `src/ksm/color.py` providing ANSI formatting functions for non-Textual output
- **BundleInfo**: A dataclass from `scanner.py` representing a discovered bundle with `name`, `registry_name`, and `path`
- **ManifestEntry**: A dataclass representing an installed bundle with `bundle_name`, `scope`, `source_registry`, `installed_files`, and timestamps

## Requirements

### Requirement 1: Add Textual as a Runtime Dependency

**User Story:** As a developer maintaining ksm, I want Textual added as a project dependency, so that the interactive UI can use Textual widgets instead of raw terminal manipulation.

#### Acceptance Criteria

1. THE Build_Configuration SHALL declare `textual` as a runtime dependency in `pyproject.toml`
2. THE Build_Configuration SHALL pin Textual to a minimum version that supports the features used (App, OptionList, Input, Screen), e.g. `textual>=0.80.0`
3. THE Build_Configuration SHALL continue to declare zero other new runtime dependencies beyond Textual and its transitive dependencies

### Requirement 2: Replace Bundle Selection with Textual App

**User Story:** As a developer using `ksm add -i`, I want the bundle selector to use a Textual-based UI, so that the interactive experience is more reliable and maintainable than the raw terminal implementation.

#### Acceptance Criteria

1. WHEN the user launches the interactive add flow and a TTY is available, THE Bundle_Selector_App SHALL present a list of available bundles using Textual widgets
2. THE Bundle_Selector_App SHALL sort bundles alphabetically (case-insensitive) and display each bundle name, with an `[installed]` indicator for already-installed bundles
3. WHEN two or more bundles share the same name across different registries, THE Bundle_Selector_App SHALL disambiguate by displaying `registry_name/bundle_name`
4. THE Bundle_Selector_App SHALL support navigation via up/down arrow keys to highlight a bundle
5. THE Bundle_Selector_App SHALL support Home/End keys to jump to the first/last item in the list
6. WHEN the user presses Enter, THE Bundle_Selector_App SHALL return the name of the highlighted bundle
7. WHEN the user presses `q` or Escape, THE Bundle_Selector_App SHALL return no selection (abort)
8. THE Bundle_Selector_App SHALL render all UI to stderr, keeping stdout clean for piped data
9. WHEN the user presses Ctrl+C during the Bundle_Selector_App, THE Selector_Module SHALL treat it as an abort and return None (no selection), matching the `q`/Escape behavior

### Requirement 3: Bundle Selector Filtering

**User Story:** As a developer with many bundles available, I want to type to filter the bundle list, so that I can quickly find the bundle I need.

#### Acceptance Criteria

1. THE Bundle_Selector_App SHALL provide a text input widget for filtering bundles by name
2. WHEN the user types in the filter input, THE Bundle_Selector_App SHALL show only bundles whose display name contains the typed text (case-insensitive substring match)
3. WHEN the filter text is cleared, THE Bundle_Selector_App SHALL show all bundles
4. WHEN the filter produces zero matches, THE Bundle_Selector_App SHALL display an empty-state message (e.g., "No bundles match '<filter_text>'") and prevent Enter from selecting
5. WHEN the filter changes, THE Bundle_Selector_App SHALL reset the highlight to the first visible item to prevent the cursor from pointing at a stale index
6. WHEN the filter changes, THE Bundle_Selector_App SHALL clear any multi-select toggles, since toggled indices no longer correspond to the same items

### Requirement 4: Bundle Selector Multi-Select

**User Story:** As a developer, I want to select multiple bundles at once, so that I can install several bundles in a single interactive session.

#### Acceptance Criteria

1. WHEN the user presses Space on a highlighted bundle, THE Bundle_Selector_App SHALL toggle that bundle's selection state with a visible `[✓]` or `[ ]` indicator
2. WHEN the user presses Enter with one or more bundles toggled, THE Bundle_Selector_App SHALL return all toggled bundle names
3. WHEN the user presses Enter with no bundles toggled, THE Bundle_Selector_App SHALL return only the currently highlighted bundle name
4. THE Bundle_Selector_App SHALL display a count of toggled items in the footer or instruction area (e.g., "3 selected") so the user knows how many bundles they have queued before confirming

> **Note:** The current `add.py` caller (`_handle_display`) only consumes `result[0]` from the returned list. Multi-select support in the selector is forward-compatible — the caller must be updated separately to iterate over all returned names for multi-install to actually work end-to-end. This requirement covers the selector UI only.

### Requirement 5: Replace Removal Selection with Textual App

**User Story:** As a developer using `ksm rm -i`, I want the removal selector to use a Textual-based UI, so that the experience is consistent with the add selector.

#### Acceptance Criteria

1. WHEN the user launches the interactive rm flow and a TTY is available, THE Removal_Selector_App SHALL present a list of installed bundles using Textual widgets
2. THE Removal_Selector_App SHALL display each bundle name with its scope label (e.g., `[local]`, `[global]`)
3. THE Removal_Selector_App SHALL support navigation via up/down arrow keys and Home/End keys, consistent with the Bundle_Selector_App
4. WHEN the user presses Enter, THE Removal_Selector_App SHALL return the selected ManifestEntry
5. WHEN the user presses `q` or Escape, THE Removal_Selector_App SHALL return no selection (abort)
6. THE Removal_Selector_App SHALL support filtering by bundle name (case-insensitive substring match), with the same empty-state, highlight-reset, and toggle-clear behavior as the Bundle_Selector_App (Requirement 3, criteria 4–6)
7. THE Removal_Selector_App SHALL support multi-select via Space key, consistent with the Bundle_Selector_App, including the selected-count indicator (Requirement 4, criterion 4)
8. THE Removal_Selector_App SHALL render all UI to stderr, keeping stdout clean
9. WHEN the user presses Ctrl+C during the Removal_Selector_App, THE Selector_Module SHALL treat it as an abort and return None, consistent with the Bundle_Selector_App

> **Note:** The current `rm.py` caller only consumes `selected_list[0]`. Same forward-compatibility note as Requirement 4.

### Requirement 6: Replace Scope Selection with Textual App

**User Story:** As a developer using `ksm add -i`, I want the scope selector to use a Textual-based UI, so that the scope selection step is consistent with the bundle selector.

#### Acceptance Criteria

1. WHEN the user needs to choose a scope and a TTY is available, THE Scope_Selector_App SHALL present two options: "Local (.kiro/)" and "Global (~/.kiro/)" using Textual widgets
2. THE Scope_Selector_App SHALL default to "Local (.kiro/)" as the pre-highlighted option
3. WHEN the user presses Enter, THE Scope_Selector_App SHALL return the highlighted scope value ("local" or "global")
4. WHEN the user presses `q` or Escape, THE Scope_Selector_App SHALL return no selection (abort)
5. THE Scope_Selector_App SHALL render all UI to stderr, keeping stdout clean
6. THE Scope_Selector_App SHALL render inline without using alternate screen buffer, since it has only two options
7. THE Scope_Selector_App SHALL NOT support filtering or multi-select, since there are only two options — these features add complexity without value here
8. WHEN the user presses Ctrl+C during the Scope_Selector_App, THE Selector_Module SHALL treat it as an abort and return None, consistent with the other selector apps

### Requirement 7: Non-TTY and Degraded Terminal Fallback

**User Story:** As a developer running ksm in a non-interactive environment (piped input, CI, TERM=dumb, Windows without termios), I want the selectors to fall back to a numbered-list prompt, so that the tool remains usable without a full terminal.

#### Acceptance Criteria

1. WHEN stdin is not a TTY, THE Selector_Module SHALL use the Numbered_List_Fallback instead of launching a Textual_App
2. WHEN the `TERM` environment variable is set to `dumb`, THE Selector_Module SHALL use the Numbered_List_Fallback
3. WHEN Textual is not importable (e.g., not installed), THE Selector_Module SHALL use the Numbered_List_Fallback and log a debug-level message indicating Textual is unavailable
4. THE Numbered_List_Fallback SHALL display items with 1-based indices, read a number from stdin, and return the selected item or None on `q`/EOF
5. IF the user enters an invalid value in the Numbered_List_Fallback, THEN THE Selector_Module SHALL print an error message to stderr stating the valid range and re-prompt
6. THE Numbered_List_Fallback SHALL render to stderr and read from stdin
7. THE Numbered_List_Fallback for scope selection SHALL default to "local" when stdin is not a TTY (non-interactive pipe), since prompting is impossible — this preserves the existing behavior in `scope_select()`
8. THE Numbered_List_Fallback SHALL NOT support multi-select — it returns a single selection only, which is acceptable for the degraded environment

### Requirement 8: Remove Raw Terminal Code

**User Story:** As a developer maintaining ksm, I want all raw `tty`/`termios` code removed from the selector module, so that the codebase is simpler and the Textual library handles terminal management.

#### Acceptance Criteria

1. THE Selector_Module SHALL NOT import `tty` or `termios` for interactive UI rendering
2. THE Selector_Module SHALL NOT contain manual ANSI escape sequences for cursor movement, screen clearing, or alternate screen buffer management
3. THE Selector_Module SHALL NOT call `tty.setraw()` or `termios.tcgetattr()`/`termios.tcsetattr()`
4. THE Selector_Module SHALL NOT contain the `_read_key()` function or equivalent raw keypress reading logic
5. THE Selector_Module SHALL retain the TTY/capability detection logic (renamed from `_use_raw_mode()` to `_can_run_textual()` or similar) for determining whether to use Textual or the Numbered_List_Fallback
6. THE renamed detection function SHALL check: (a) stdin is a TTY, (b) TERM is not `dumb`, and (c) Textual is importable

### Requirement 9: Preserve Public API of Selector Module

**User Story:** As a developer, I want the refactored selector module to maintain the same public function signatures, so that command modules (add.py, rm.py) require no changes to their selector calls.

#### Acceptance Criteria

1. THE Selector_Module SHALL export `interactive_select(bundles: list[BundleInfo], installed_names: set[str]) -> list[str] | None` with the same signature and return semantics
2. THE Selector_Module SHALL export `interactive_removal_select(entries: list[ManifestEntry]) -> list[ManifestEntry] | None` with the same signature and return semantics
3. THE Selector_Module SHALL export `scope_select() -> str | None` with the same signature and return semantics
4. THE Selector_Module SHALL export `clamp_index(index: int, count: int) -> int` for backward compatibility
5. THE Selector_Module SHALL remove `process_key()` since it is tightly coupled to the raw-mode byte-reading approach and has no external callers outside tests — tests should be updated to test behavior through the public API or Textual's test harness instead

### Requirement 10: Textual App Styling

**User Story:** As a developer using the interactive selectors, I want the Textual UI to have clear visual styling, so that headers, instructions, highlighted items, and status badges are easy to distinguish.

#### Acceptance Criteria

1. THE Bundle_Selector_App SHALL display a header ("Select a bundle to install") in bold styling
2. THE Bundle_Selector_App SHALL display an instruction line showing all available keybindings ("↑/↓ navigate, Space toggle, Enter confirm, q/Esc quit") in dim styling
3. THE Bundle_Selector_App SHALL display the currently highlighted item with a distinct visual indicator (e.g., reverse-video highlight bar) that does not rely solely on color
4. THE Bundle_Selector_App SHALL display `[installed]` badges in dim styling
5. WHEN the `NO_COLOR` environment variable is set, THE Textual_App SHALL disable color output while preserving structural indicators (bold as text weight, highlight as reverse-video or bracket markers)
6. THE Removal_Selector_App SHALL display scope labels (e.g., `[local]`) in dim styling
7. THE Scope_Selector_App SHALL display its header ("Select installation scope:") in bold styling
8. ALL three Textual_App selectors SHALL use Textual CSS for styling, defined in a companion `.tcss` file or inline `CSS` class variable — not inline Rich markup scattered through widget code
9. THE highlight indicator SHALL be visible without color (e.g., `>` prefix or reverse-video) so that NO_COLOR and monochrome terminals remain usable

### Requirement 11: Textual App Renders to Stderr

**User Story:** As a developer piping ksm output, I want the Textual UI to render exclusively to stderr, so that stdout remains clean for machine-readable data.

#### Acceptance Criteria

1. THE Bundle_Selector_App SHALL configure Textual to use stderr as its output stream (via the `App(output=sys.stderr)` constructor parameter or equivalent)
2. THE Removal_Selector_App SHALL configure Textual to use stderr as its output stream
3. THE Scope_Selector_App SHALL configure Textual to use stderr as its output stream
4. WHEN a Textual_App is running, THE Selector_Module SHALL NOT write any UI content to stdout

### Requirement 12: Preserve Render Functions for Testing

**User Story:** As a developer writing tests, I want the pure render functions (render_add_selector, render_removal_selector) to remain available, so that selector rendering logic can be unit-tested without launching a Textual app.

#### Acceptance Criteria

1. THE Selector_Module SHALL retain `render_add_selector()` as a pure function that returns a list of string lines representing the add selector UI
2. THE Selector_Module SHALL retain `render_removal_selector()` as a pure function that returns a list of string lines representing the removal selector UI
3. THE render functions SHALL accept the same parameters as before (bundles, installed_names, selected, filter_text, multi_selected)
4. THE render functions SHALL continue to apply color via the Color_Module for non-Textual contexts (e.g., testing, fallback rendering)

### Requirement 13: Color Module Coexistence

**User Story:** As a developer, I want the existing color.py module to continue working for non-Textual output, so that error messages, diff summaries, and success prefixes retain their color treatment.

#### Acceptance Criteria

1. THE Color_Module SHALL remain unchanged and continue to provide `green()`, `red()`, `yellow()`, `dim()`, and `bold()` functions
2. THE Color_Module SHALL continue to be used by `errors.py`, `copier.py`, and command modules for non-Textual output
3. THE Textual_App instances SHALL use Textual's own CSS-based styling system for all in-app styling, not the Color_Module
4. WHEN the `NO_COLOR` environment variable is set, THE Color_Module SHALL continue to produce plain text without ANSI codes

### Requirement 14: Terminal Cleanup and Resilience

**User Story:** As a developer, I want the Textual apps to leave the terminal in a clean state regardless of how they exit, so that my shell session is never corrupted by a selector crash or interruption.

#### Acceptance Criteria

1. WHEN a Textual_App exits normally (Enter, q, Escape), THE Selector_Module SHALL restore the terminal to its pre-app state
2. WHEN a Textual_App exits via Ctrl+C, THE Selector_Module SHALL restore the terminal to its pre-app state before returning None
3. WHEN a Textual_App raises an unexpected exception, THE Selector_Module SHALL catch the exception, restore the terminal, and re-raise or return None with an error message to stderr
4. THE Selector_Module SHALL NOT leave the cursor hidden, alternate screen buffer active, or raw mode enabled after any exit path

> **Rationale:** The current raw-mode implementation has a `finally` block that restores terminal state, but edge cases (e.g., SIGKILL, OOM) can leave the terminal broken. Textual handles this more robustly via its application lifecycle, but the requirement makes the expectation explicit.

### Requirement 15: Consistent Keybinding Behavior Across All Selectors

**User Story:** As a developer, I want all three selector apps to respond to the same keys in the same way, so that I don't have to learn different controls for each selector.

#### Acceptance Criteria

1. ALL three Textual_App selectors SHALL use the following shared keybinding scheme:
   - `↑`/`↓` — navigate highlight
   - `Home`/`End` — jump to first/last item
   - `Enter` — confirm selection
   - `Escape` — abort (return None)
   - `q` — abort (return None)
   - `Ctrl+C` — abort (return None)
2. THE Bundle_Selector_App and Removal_Selector_App SHALL additionally support:
   - `Space` — toggle multi-select on highlighted item
   - Typing — filter the list (via the filter input widget)
3. THE Scope_Selector_App SHALL NOT respond to Space (no multi-select) or typing (no filter), since it has only two fixed options
4. THE `q` key SHALL only trigger abort when the filter input is empty or unfocused — if the user is typing a filter containing `q`, it SHALL be treated as a filter character, not an abort

> **Rationale:** Criterion 4 fixes a real usability bug in the current implementation where typing `q` in a filter string (e.g., searching for "sql-queries") would abort the selector instead of filtering.

### Requirement 16: Empty List Edge Cases

**User Story:** As a developer, I want the selectors to handle empty inputs gracefully, so that I see a helpful message instead of a blank screen or crash.

#### Acceptance Criteria

1. WHEN `interactive_select()` is called with an empty bundle list, THE Selector_Module SHALL return None without launching a Textual_App (preserving existing behavior)
2. WHEN `interactive_removal_select()` is called with an empty entry list, THE Selector_Module SHALL return None without launching a Textual_App (preserving existing behavior)
3. WHEN a single item is in the list, THE Bundle_Selector_App and Removal_Selector_App SHALL still display the full UI (header, instructions, item) rather than auto-selecting, so the user can review and abort if needed
