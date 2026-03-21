# Implementation Plan: Color Scheme & Scope Selection

## Overview

This plan wires the existing but unused `green()`, `red()`, `yellow()` color functions across all ksm CLI output (Reqs 1–10) and adds an interactive scope selection step to the `ksm add -i` flow (Reqs 11–16). The plan has 4 phases: color infrastructure (errors.py, copier.py), color wiring across commands, scope selector implementation, and integration verification.

## Tasks

- [ ] 1. Color Infrastructure — errors.py and copier.py

  - [ ] 1.1 Colorize error/warning/deprecation formatters (errors.py)

    - [x] 1.1.1 Write tests for colorized error, warning, and deprecation formatters with stream parameter
      → Agent: general-task-execution
      **Property 1: format_error wraps "Error:" prefix in red when stream is a TTY**
      **Property 2: format_warning wraps "Warning:" prefix in yellow when stream is a TTY**
      **Property 3: format_deprecation wraps "Deprecated:" prefix in yellow when stream is a TTY**
      **Property 4: All formatters return plain text when NO_COLOR is set**
      **Property 5: All formatters return plain text when stream is not a TTY**
      **Property 6: All formatters preserve existing message structure**
      **Property 7: All formatters return plain text when TERM=dumb**
      _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5_

    - [x] 1.1.2 Add stream parameter to format_error, format_warning, format_deprecation and apply red/yellow color to prefixes
      → Agent: general-task-execution
      _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5_

    - [x] 1.1.3 Run errors tests and verify all pass
      → Agent: kiro

  - [ ] 1.2 Colorize diff summary symbols (copier.py)

    - [x] 1.2.1 Write tests for colorized format_diff_summary with stream parameter (green +/new, yellow ~/updated, dim =/unchanged)
      → Agent: general-task-execution
      **Property 8: NEW status wraps + symbol and (new) label in green**
      **Property 9: UPDATED status wraps ~ symbol and (updated) label in yellow**
      **Property 10: UNCHANGED status wraps = symbol and (unchanged) label in dim**
      **Property 11: format_diff_summary returns plain text when NO_COLOR is set**
      _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

    - [x] 1.2.2 Add stream parameter to format_diff_summary and apply green/yellow/dim color to symbols and labels
      → Agent: general-task-execution
      _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

    - [x] 1.2.3 Run copier tests and verify all pass
      → Agent: kiro

  - [x] 1.3 Checkpoint — Run full test suite, verify all tests pass
    → Agent: kiro

- [ ] 2. Color Wiring Across Commands

  - [ ] 2.1 Wire stream=sys.stderr into all format_error/format_warning/format_deprecation call sites

    - [x] 2.1.1 Write tests verifying that command modules pass stream=sys.stderr to error/warning/deprecation formatters (add.py, rm.py, sync.py)
      → Agent: general-task-execution
      _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3_

    - [x] 2.1.2 Update all format_error, format_warning, format_deprecation call sites in add.py, rm.py, sync.py, and other command modules to pass stream=sys.stderr
      → Agent: general-task-execution
      _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3_

    - [x] 2.1.3 Run command tests and verify all pass
      → Agent: kiro

  - [ ] 2.2 Colorize success messages (add, rm, sync)

    - [x] 2.2.1 Write tests for green success prefix in add.py ("Installed:"), rm.py ("Removed"), and sync.py ("Synced:")
      → Agent: general-task-execution
      **Property 12: add success message includes green "Installed:" prefix**
      **Property 13: rm _format_result wraps "Removed" prefix in green**
      **Property 14: sync success message includes green "Synced:" prefix**
      _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

    - [x] 2.2.2 Add green success prefix to add.py, update _format_result in rm.py with stream param and green prefix, add green prefix to sync.py
      → Agent: general-task-execution
      _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

    - [x] 2.2.3 Wire stream=sys.stderr into all format_diff_summary call sites in add.py, sync.py, and ephemeral flow
      → Agent: general-task-execution
      _Requirements: 4.4_

    - [x] 2.2.4 Run add, rm, sync tests and verify all pass
      → Agent: kiro

  - [ ] 2.3 Colorize rm confirmation prompt and sync confirmation prompt

    - [x] 2.3.1 Write tests for colored rm confirmation prompt (dim file paths, bold scope description) and colored sync confirmation (bold bundle names, bold scope)
      → Agent: general-task-execution
      **Property 15: rm confirmation wraps file paths in dim**
      **Property 16: rm confirmation wraps scope description in bold**
      **Property 17: sync confirmation wraps bundle names in bold**
      **Property 18: sync confirmation wraps scope description in bold**
      _Requirements: 7.1, 7.2, 7.3, 7.4, 10.1, 10.2, 10.3_

    - [x] 2.3.2 Add stream parameter to _format_confirmation in rm.py, apply dim to file paths and bold to scope description
      → Agent: general-task-execution
      _Requirements: 7.1, 7.2, 7.3, 7.4_

    - [x] 2.3.3 Add stream parameter to _build_confirmation_message in sync.py, apply bold to bundle names and scope description
      → Agent: general-task-execution
      _Requirements: 10.1, 10.2, 10.3_

    - [x] 2.3.4 Run rm and sync tests and verify all pass
      → Agent: kiro

  - [ ] 2.4 Colorize selector UI elements

    - [x] 2.4.1 Write tests for colored selector elements (bold header, dim instructions, bold highlighted name, dim [installed] badge, dim [scope] label, dim filter prompt)
      → Agent: general-task-execution
      **Property 19: render_add_selector wraps header in bold**
      **Property 20: render_add_selector wraps instructions in dim**
      **Property 21: render_add_selector wraps highlighted bundle name in bold**
      **Property 22: render_add_selector wraps [installed] badge in dim**
      **Property 23: render_removal_selector wraps [scope] label in dim**
      **Property 24: selector wraps filter prompt in dim**
      _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

    - [x] 2.4.2 Apply bold/dim color to render_add_selector and render_removal_selector in selector.py (header, instructions, highlighted name, badges, filter prompt)
      → Agent: general-task-execution
      _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

    - [x] 2.4.3 Run selector tests and verify all pass
      → Agent: kiro

  - [ ] 2.5 Verify and extend info.py and registry_ls.py color

    - [x] 2.5.1 Write tests verifying info.py wraps installed status in green (when installed) and verify existing bold/dim usage; write tests verifying registry_ls.py wraps URLs in dim
      → Agent: general-task-execution
      **Property 25: info installed status uses green when installed**
      **Property 26: registry_ls wraps URLs in dim**
      _Requirements: 9.2, 9.3, 8.2, 8.5_

    - [x] 2.5.2 Update info.py to wrap installed scopes in green; update registry_ls.py to wrap URLs in dim
      → Agent: general-task-execution
      _Requirements: 9.2, 8.2_

    - [x] 2.5.3 Run info and registry command tests and verify all pass
      → Agent: kiro

  - [ ] 2.6 Verify existing color usage (ls, search, registry_inspect)

    - [x] 2.6.1 Verify existing tests cover bold/dim usage in ls.py (Req 5), search.py (Req 9.1), and registry_inspect.py (Req 8.4) — add tests if missing
      → Agent: general-task-execution
      _Requirements: 5.1, 5.2, 5.3, 5.4, 8.1, 8.3, 8.4, 8.5, 9.1, 9.3_

    - [x] 2.6.2 Run ls, search, and registry inspect tests and verify all pass
      → Agent: kiro

  - [x] 2.7 Checkpoint — Run full test suite, verify all tests pass
    → Agent: kiro

- [ ] 3. Scope Selector Implementation

  - [ ] 3.1 Scope selector core function (selector.py)

    - [x] 3.1.1 Write tests for scope_select() — raw mode navigation, Enter returns highlighted scope, q/Escape aborts, default is "local", SIGINT restores terminal
      → Agent: general-task-execution
      **Property 27: scope_select returns "local" when Enter pressed without navigation**
      **Property 28: scope_select returns "global" when user navigates to second option and presses Enter**
      **Property 29: scope_select returns None when user presses q or Escape**
      **Property 30: scope_select restores terminal settings on SIGINT**
      _Requirements: 11.1, 11.2, 11.3, 11.4, 11.6, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

    - [x] 3.1.2 Write tests for scope_select() numbered-list fallback — "1" returns "local", "2" returns "global", "q" aborts, empty input defaults to "local", invalid input re-prompts, TERM=dumb uses fallback
      → Agent: general-task-execution
      **Property 31: numbered-list fallback returns "local" for input "1" or empty**
      **Property 32: numbered-list fallback returns "global" for input "2"**
      **Property 33: numbered-list fallback returns None for input "q"**
      **Property 34: numbered-list fallback re-prompts on invalid input**
      **Property 35: TERM=dumb forces numbered-list fallback**
      _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

    - [x] 3.1.3 Implement scope_select() in selector.py with raw mode and numbered-list fallback, inline rendering (no alternate screen buffer), color treatment for header/instructions/highlighted option
      → Agent: general-task-execution
      _Requirements: 11.1, 11.2, 11.3, 11.4, 11.6, 11.7, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 16.1, 16.2, 16.3, 16.4, 16.5, 16.6_

    - [x] 3.1.4 Run scope selector tests and verify all pass
      → Agent: kiro

  - [ ] 3.2 Integrate scope selector into add command

    - [x] 3.2.1 Write tests for scope selection integration in add.py — scope_select called when -l/-g not provided in interactive mode, skipped when -l or -g provided, skipped when stdin not TTY (defaults to "local"), abort returns exit 0
      → Agent: general-task-execution
      **Property 36: interactive add calls scope_select when no -l/-g flag**
      **Property 37: interactive add skips scope_select when -l or -g provided**
      **Property 38: interactive add defaults to "local" when stdin not TTY**
      **Property 39: scope_select abort returns exit code 0**
      **Property 40: selected scope is passed to install_bundle**
      _Requirements: 11.1, 11.5, 11.7, 15.1, 15.2, 15.3, 15.4_

    - [x] 3.2.2 Integrate scope_select() call into run_add in add.py after bundle selection, respecting -l/-g flag override and non-TTY default
      → Agent: general-task-execution
      _Requirements: 11.1, 11.5, 11.7, 15.1, 15.2, 15.3, 15.4_

    - [ ] 3.2.3 Run add command tests and verify all pass
      → Agent: kiro

  - [ ] 3.3 Verify rm -i scope behavior (no separate scope prompt)

    - [ ] 3.3.1 Write or verify tests confirming rm -i uses scope from ManifestEntry, no separate scope prompt is shown, and -l/-g filters the removal list
      → Agent: general-task-execution
      **Property 41: rm -i uses scope from selected ManifestEntry**
      **Property 42: rm -i does not present scope selection step**
      _Requirements: 14.1, 14.2, 14.3_

    - [ ] 3.3.2 Run rm tests and verify all pass
      → Agent: kiro

  - [ ] 3.4 Checkpoint — Run full test suite, verify all tests pass
    → Agent: kiro

- [ ] 4. Integration Verification and Linting

  - [ ] 4.1 Full verification

    - [ ] 4.1.1 Run full test suite with coverage, verify ≥95% coverage on modified files (errors.py, copier.py, selector.py, add.py, rm.py, sync.py, info.py, registry_ls.py)
      → Agent: kiro
      _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2, 9.3, 10.1, 10.2, 10.3, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 14.1, 14.2, 14.3, 15.1, 15.2, 15.3, 15.4, 16.1, 16.2, 16.3, 16.4, 16.5, 16.6_

    - [ ] 4.1.2 Run black, flake8, and mypy on all modified source and test files, fix any issues
      → Agent: kiro
      _Requirements: 1.1, 2.1, 3.1, 4.1, 6.1, 7.1, 8.2, 9.2, 10.1, 11.1, 12.1, 13.1, 14.1, 15.1, 16.1_

  - [ ] 4.2 Checkpoint — Final full test suite run, confirm all tests pass and coverage ≥95%
    → Agent: kiro
