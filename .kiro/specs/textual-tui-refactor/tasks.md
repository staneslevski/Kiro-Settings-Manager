# Implementation Plan: Textual TUI Refactor

## Overview

Replace the hand-rolled raw `tty`/`termios` terminal UI in `src/ksm/selector.py` with the Textual TUI library. 7 phases ordered by dependency: dependency setup → capability detection → Textual apps (bundle, removal, scope) → selector.py rewiring → fallback hardening → cleanup → final integration. New module `src/ksm/tui.py` houses all Textual App subclasses. Public API of `selector.py` is preserved — command modules require zero changes.

## Tasks

- [x] 1. Dependency setup and project configuration

  - [x] 1.1 Add Textual runtime dependency

    - [x] 1.1.1 Add `textual>=0.80.0` to `[project] dependencies` in `pyproject.toml` and reinstall with `pip install -e ".[dev]"`
      _Requirements: 1.1, 1.2, 1.3_

  - [x] 1.2 Checkpoint — Verify `import textual` succeeds and existing tests still pass (Textual 8.1.1 installed, 731/733 tests pass, 2 pre-existing failures unrelated to change)
    → Agent: kiro

- [ ] 2. Capability detection and fallback infrastructure

  - [ ] 2.1 Replace `_use_raw_mode()` with `_can_run_textual()`

    - [ ] 2.1.1 Write property test for `_can_run_textual()` in `tests/test_selector.py`
      → Agent: terminal-ui-engineer
      **Property 9: `_can_run_textual()` returns True iff stdin is TTY, TERM is not dumb, and Textual is importable**
      _Requirements: 7.1, 7.2, 7.3, 8.5, 8.6_

    - [ ] 2.1.2 Implement `_can_run_textual()` in `src/ksm/selector.py`, replacing `_use_raw_mode()`
      → Agent: terminal-ui-engineer
      _Requirements: 7.1, 7.2, 7.3, 8.5, 8.6_

    - [ ] 2.1.3 Run tests and verify all pass
      → Agent: kiro

  - [ ] 2.2 Harden numbered-list fallback

    - [ ] 2.2.1 Write tests for `_numbered_list_select()` invalid input re-prompting and stderr rendering in `tests/test_selector.py`
      → Agent: terminal-ui-engineer
      **Property 10: Numbered-list fallback returns correct item for valid 1-based index, None for q/EOF**
      _Requirements: 7.4, 7.5, 7.6, 7.8_

    - [ ] 2.2.2 Update `_numbered_list_select()` to re-prompt on invalid input with error message to stderr stating valid range
      → Agent: terminal-ui-engineer
      _Requirements: 7.4, 7.5, 7.6_

    - [ ] 2.2.3 Write test for scope fallback defaulting to "local" when stdin is not a TTY
      → Agent: terminal-ui-engineer
      _Requirements: 7.7_

    - [ ] 2.2.4 Run tests and verify all pass
      → Agent: kiro

  - [ ] 2.3 Checkpoint — Run full test suite, verify all tests pass
    → Agent: kiro

- [ ] 3. Textual apps — Bundle and Removal selectors

  - [ ] 3.1 Create `src/ksm/tui.py` with `BundleSelectorApp`

    - [ ] 3.1.1 Implement `BundleSelectorApp` with OptionList, Input filter widget, multi-select via Space, header/instructions Static widgets, and selected-count footer
      - Sort bundles alphabetically (case-insensitive), show `[installed]` badge, disambiguate duplicate names with `registry_name/bundle_name`
      - Render to stderr via `App(output=sys.stderr)`
      - CSS styling via class variable (header bold, instructions dim, installed badge dim, highlight visible without color)
      → Agent: terminal-ui-engineer
      _Requirements: 2.1–2.9, 3.1–3.6, 4.1–4.4, 10.1–10.5, 10.8, 10.9, 11.1, 15.1, 15.2, 15.4_

    - [ ] 3.1.2 Write Textual pilot tests for `BundleSelectorApp` in `tests/test_tui.py`
      → Agent: terminal-ui-engineer
      **Property 4: Filter change resets highlight to 0 and clears multi-select toggles**
      **Property 5: Enter returns toggled items when any are toggled, otherwise returns highlighted item**
      **Property 6: Selected count indicator equals cardinality of toggled set**
      **Property 12: `q` key appends to filter when filter is non-empty and focused, aborts when filter is empty**
      - Example tests: up/down navigation, Home/End, Escape abort, Ctrl+C abort, empty filter state message, disambiguation display
      _Requirements: 2.1–2.9, 3.1–3.6, 4.1–4.4, 15.1, 15.2, 15.4_

    - [ ] 3.1.3 Run tests and verify all pass
      → Agent: kiro

  - [ ] 3.2 Add `RemovalSelectorApp` to `src/ksm/tui.py`

    - [ ] 3.2.1 Implement `RemovalSelectorApp` with OptionList, Input filter, multi-select, scope labels (`[local]`/`[global]`) in dim styling
      - Render to stderr, consistent keybindings with BundleSelectorApp
      → Agent: terminal-ui-engineer
      _Requirements: 5.1–5.9, 10.6, 11.2, 15.1, 15.2, 15.4_

    - [ ] 3.2.2 Write Textual pilot tests for `RemovalSelectorApp` in `tests/test_tui.py`
      → Agent: terminal-ui-engineer
      - Enter returns ManifestEntry, scope labels displayed, filter/multi-select/abort behavior consistent with BundleSelectorApp
      _Requirements: 5.1–5.9_

    - [ ] 3.2.3 Run tests and verify all pass
      → Agent: kiro

  - [ ] 3.3 Checkpoint — Run full test suite, verify all tests pass
    → Agent: kiro

- [ ] 4. Textual apps — Scope selector

  - [ ] 4.1 Add `ScopeSelectorApp` to `src/ksm/tui.py`

    - [ ] 4.1.1 Implement `ScopeSelectorApp` with OptionList (2 items: "Local (.kiro/)", "Global (~/.kiro/)"), inline rendering (no alternate screen buffer), no filter, no multi-select
      - Default highlight on "Local (.kiro/)", header bold, render to stderr
      - `q` always aborts (no filter input to conflict with)
      → Agent: terminal-ui-engineer
      _Requirements: 6.1–6.8, 10.7, 11.3, 15.1, 15.3_

    - [ ] 4.1.2 Write Textual pilot tests for `ScopeSelectorApp` in `tests/test_tui.py`
      → Agent: terminal-ui-engineer
      - Enter returns "local"/"global", Escape/q/Ctrl+C abort, default highlight is Local, no filter/multi-select
      _Requirements: 6.1–6.8_

    - [ ] 4.1.3 Run tests and verify all pass
      → Agent: kiro

  - [ ] 4.2 Checkpoint — Run full test suite, verify all tests pass
    → Agent: kiro

- [ ] 5. Rewire `selector.py` public API to use Textual apps

  - [ ] 5.1 Rewire `interactive_select()`

    - [ ] 5.1.1 Refactor `interactive_select()` to delegate to `BundleSelectorApp` when `_can_run_textual()` is True, otherwise fall back to `_numbered_list_select()`
      - Lazy import of `tui.py` inside the Textual path
      - Wrap `app.run()` in `try/except (KeyboardInterrupt, Exception)` returning None on abort/error
      - Return `None` immediately for empty bundle list
      → Agent: terminal-ui-engineer
      _Requirements: 2.1, 9.1, 14.1–14.4, 16.1_

  - [ ] 5.2 Rewire `interactive_removal_select()`

    - [ ] 5.2.1 Refactor `interactive_removal_select()` to delegate to `RemovalSelectorApp`, same pattern as `interactive_select()`
      - Return `None` immediately for empty entry list
      → Agent: terminal-ui-engineer
      _Requirements: 5.1, 9.2, 14.1–14.4, 16.2_

  - [ ] 5.3 Rewire `scope_select()`

    - [ ] 5.3.1 Refactor `scope_select()` to delegate to `ScopeSelectorApp`, same pattern
      → Agent: terminal-ui-engineer
      _Requirements: 6.1, 9.3, 14.1–14.4_

  - [ ] 5.4 Write stderr-only rendering test

    - [ ] 5.4.1 Write test verifying all three public functions produce zero stdout output in `tests/test_tui.py`
      → Agent: terminal-ui-engineer
      **Property 8: All selector UI renders to stderr only — zero bytes on stdout**
      _Requirements: 2.8, 5.8, 6.5, 11.1–11.4_

  - [ ] 5.5 Run tests and verify all pass
    → Agent: kiro

  - [ ] 5.6 Checkpoint — Run full test suite, verify all tests pass
    → Agent: kiro

- [ ] 6. Remove raw terminal code and update pure render functions

  - [ ] 6.1 Strip raw-mode code from `selector.py`

    - [ ] 6.1.1 Remove `tty`/`termios` imports, `_HAS_TERMIOS`, `_read_key()`, `process_key()`, and all manual ANSI escape sequences from `selector.py`
      - Retain `clamp_index()`, `render_add_selector()`, `render_removal_selector()`, `_numbered_list_select()`
      → Agent: terminal-ui-engineer
      _Requirements: 8.1–8.5, 9.4, 9.5, 12.1–12.4_

  - [ ] 6.2 Write structural verification tests

    - [ ] 6.2.1 Write tests in `tests/test_selector.py` asserting `selector.py` does not import `tty` or `termios`, does not contain `process_key`, and exports `clamp_index`
      → Agent: terminal-ui-engineer
      _Requirements: 8.1–8.4, 9.4, 9.5_

  - [ ] 6.3 Update pure render function tests

    - [ ] 6.3.1 Update existing property tests for `render_add_selector` and `render_removal_selector` in `tests/test_selector.py`
      → Agent: terminal-ui-engineer
      **Property 1: Bundle list sorting and installed-label accuracy**
      **Property 2: Ambiguous bundle name disambiguation**
      **Property 3: Filter produces correct subset**
      **Property 7: Removal selector displays scope labels**
      **Property 11: clamp_index bounds**
      _Requirements: 2.2, 2.3, 3.2, 3.3, 5.2, 9.4, 12.1–12.4_

  - [ ] 6.4 Remove obsolete tests

    - [ ] 6.4.1 Remove `test_process_key_*` tests and any tests mocking `tty`/`termios`/`_read_key` from `tests/test_selector.py` and `tests/test_scope_select.py`
      → Agent: terminal-ui-engineer
      _Requirements: 8.1–8.4, 9.5_

  - [ ] 6.5 Run tests and verify all pass
    → Agent: kiro

  - [ ] 6.6 Checkpoint — Run full test suite, verify all tests pass
    → Agent: kiro

- [ ] 7. Final integration, edge cases, and cleanup

  - [ ] 7.1 Empty list and single-item edge cases

    - [ ] 7.1.1 Write tests verifying empty-list returns None without launching app, and single-item still shows full UI in `tests/test_tui.py`
      → Agent: terminal-ui-engineer
      _Requirements: 16.1, 16.2, 16.3_

  - [ ] 7.2 NO_COLOR support verification

    - [ ] 7.2.1 Write test verifying Textual apps respect `NO_COLOR` env var — structural indicators (reverse-video, `>` prefix) remain visible
      → Agent: terminal-ui-engineer
      _Requirements: 10.5, 10.9, 13.4_

  - [ ] 7.3 Color module coexistence verification

    - [ ] 7.3.1 Write test verifying `color.py` functions are still used by `errors.py` and `copier.py`, and Textual apps use CSS-only styling
      → Agent: terminal-ui-engineer
      _Requirements: 13.1–13.4_

  - [ ] 7.4 Run full test suite, lint with black and flake8, type check with mypy
    → Agent: kiro

  - [ ] 7.5 Create pull request
    → Skill: github-pr

## Notes

- All Textual apps live in `src/ksm/tui.py` — `selector.py` remains the thin public API layer
- Textual is lazily imported inside the Textual code path so `import ksm.selector` never fails without Textual
- Property tests use Hypothesis with dev/ci profiles (conftest.py already configured)
- Each property test references its design property number and validated requirements
- Checkpoints ensure incremental validation after each phase
- Command modules (`add.py`, `rm.py`) require zero changes — public API signatures are preserved
