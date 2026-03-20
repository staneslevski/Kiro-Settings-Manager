# Implementation Plan: UX Review Fixes

## Overview

Implements 35 requirements from the ksm CLI UX and engineering reviews across 8 phases ordered by dependency. Each phase builds on previous work. Tests are written as sub-tasks close to implementation. Property-based tests use Hypothesis with the dev profile (15 examples).

## Tasks

- [x] 1. Foundation — Color module, signal handler, typo suggestions

  - [x] 1.1 Color module (`src/ksm/color.py`)

    - [x] 1.1.1 Create `src/ksm/color.py` with `_color_enabled_for_stream()`, `_color_enabled()`, `_color_enabled_stderr()`, `_wrap()`, `green()`, `red()`, `yellow()`, `dim()`, `bold()`
      - Check NO_COLOR env var, TERM=dumb, stream.isatty()
      - Each color function accepts optional `stream` parameter
      - _Requirements: 10.1, 10.2, 10.3, 10.5, 10.6, 10.7_

    - [x] 1.1.2 Write property tests for color module
      - **Property 13: Color disabled returns plain text** (NO_COLOR, non-TTY, TERM=dumb)
      - **Property 14: Color enabled wraps with ANSI codes**
      - **Property 14b: Color checks correct stream TTY status**
      - **Validates: Requirements 10.1, 10.2, 10.3, 10.6, 10.7**

  - [x] 1.2 Signal handler (`src/ksm/signal_handler.py`)

    - [x] 1.2.1 Create `src/ksm/signal_handler.py` with `register_temp_dir()`, `unregister_temp_dir()`, `_sigint_handler()`, `install_signal_handler()`
      - Module-level `_active_temp_dirs: set[Path]` for tracking
      - Handler cleans up tracked dirs, prints to stderr, exits 130
      - _Requirements: 34.1, 34.2, 34.3, 34.4_

    - [x] 1.2.2 Write tests for signal handler
      - **Property 39: SIGINT handler cleans up temp directories**
      - Test no-op when no active dirs (exits 130 immediately)
      - **Validates: Requirements 34.1, 34.2, 34.3, 34.4**

  - [x] 1.3 Typo suggestions (`src/ksm/typo_suggest.py`)

    - [x] 1.3.1 Create `src/ksm/typo_suggest.py` with `levenshtein_distance()` and `suggest_command()`
      - Pure-Python Levenshtein distance, max_distance=2 threshold
      - Returns closest match or None
      - _Requirements: 24.1, 24.2, 24.3_

    - [x] 1.3.2 Write property tests for typo suggestions
      - **Property 29: Typo suggestion returns closest match within edit distance 2**
      - Test specific examples: `ad` → `add`, `synx` → `sync`
      - **Validates: Requirements 24.1, 24.2, 24.3, 24.4**

  - [x] 1.4 Checkpoint — Ensure all tests pass, ask the user if questions arise.

- [x] 2. CLI Structure — Parser restructuring

  - [x] 2.1 KsmArgumentParser and core parser refactor — _Agent: cli-engineer_

    - [x] 2.1.1 Create `KsmArgumentParser` in `cli.py` with `error()` override for typo suggestions
      - Import and call `suggest_command()` on unknown command errors
      - Always include `ksm --help` hint in error messages
      - _Requirements: 24.1, 24.2, 24.3, 24.4_

    - [x] 2.1.2 Add mutually exclusive scope groups for `-l`/`-g` on `add` and `rm`
      - Use `add_mutually_exclusive_group()` in `_build_parser()`
      - _Requirements: 27.1, 27.2, 27.3_

    - [x] 2.1.3 Add global `--verbose`/`-v` and `--quiet`/`-q` as mutually exclusive group on top-level parser
      - _Requirements: 28.1, 28.2, 28.5_

    - [x] 2.1.4 Replace `--skills-only`, `--agents-only`, `--steering-only`, `--hooks-only` with repeatable `--only <type>` flag
      - Use `choices=["skills", "agents", "steering", "hooks"]`, `action="append"`
      - Update `_build_subdirectory_filter()` in `commands/add.py`
      - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

    - [x] 2.1.5 Rename `--display` to `--interactive`/`-i` on `add` and `rm`, keep `--display` as hidden alias with deprecation warning
      - _Requirements: 11.1, 11.2, 11.3_

    - [x] 2.1.6 Write tests for parser changes
      - **Property 5: --only flag builds correct filter set**
      - **Property 6: Invalid --only type produces error**
      - **Property 32: Mutually exclusive -l/-g produces argparse error**
      - **Property 33: Global verbose/quiet mutual exclusion**
      - Test `--display` deprecation warning
      - **Validates: Requirements 5, 11, 27, 28**

  - [x] 2.2 Registry subcommand group — _Agent: cli-engineer_

    - [x] 2.2.1 Restructure parser: add `registry` subcommand with `add`, `ls`, `rm`, `inspect` subparsers; remove top-level `add-registry`
      - _Requirements: 4.1, 4.2, 4.3, 4.4_

    - [x] 2.2.2 Create `commands/registry_add.py` (refactor from `commands/add_registry.py`), update dispatch in `cli.py`
      - Print success to stderr (Req 32.2)
      - _Requirements: 4.2, 32.2_

    - [x] 2.2.3 Write tests for registry subcommand structure
      - Parser accepts `registry add/ls/rm/inspect`, rejects `add-registry`
      - `registry` with no subcommand shows help
      - **Validates: Requirements 4.1, 4.3, 4.4**

  - [x] 2.3 Help text and curated help — _Agent: cli-engineer_

    - [x] 2.3.1 Add `RawDescriptionHelpFormatter` and `epilog` with 2-3 examples to every subparser (add, rm, ls, sync, registry add/ls/rm/inspect, init, info, search, completions)
      - Add footer to top-level parser: `Use "ksm <command> --help" for more info`
      - _Requirements: 23.1, 23.2, 23.3_

    - [x] 2.3.2 Replace default `parser.print_help()` with curated help screen when no command given
      - Show tool name, version, grouped commands, quick-start examples
      - _Requirements: 16.1, 16.2, 16.3_

    - [x] 2.3.3 Write tests for help text
      - **Property 28: Help epilog contains examples for every subcommand**
      - **Property 40: Help examples are syntactically valid commands (round-trip)**
      - Test curated help contains required sections
      - **Validates: Requirements 16, 23, 35**

  - [x] 2.4 Checkpoint — Ensure all tests pass, ask the user if questions arise.

- [x] 3. Error UX — Enriched error classes, actionable messages

  - [x] 3.1 Error class enhancements — _Agent: cli-engineer_

    - [x] 3.1.1 Extend `BundleNotFoundError` to accept `searched_registries` list; format message with name, registries, and suggestions
      - _Requirements: 7.1, 7.3_

    - [x] 3.1.2 Extend `GitError` to accept `url` and `stderr_output`; format cleaned single-line message with URL and suggestion
      - _Requirements: 7.2, 7.4_

    - [x] 3.1.3 Update `resolver.py` to pass searched registry names to `BundleNotFoundError`
      - _Requirements: 7.1_

    - [x] 3.1.4 Write property tests for error classes
      - **Property 11: BundleNotFoundError contains name and all searched registries**
      - **Property 12: GitError contains URL and cleaned summary**
      - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

  - [x] 3.2 Checkpoint — Ensure all tests pass, ask the user if questions arise.

- [x] 4. Safety & Feedback — rm confirmation, rm feedback, TTY checks, stderr messages

  - [x] 4.1 rm confirmation and feedback — _Agent: cli-engineer_

    - [x] 4.1.1 Add `--yes`/`-y` flag to `rm` parser, add `--dry-run` to `add`/`rm`/`sync` parsers
      - _Requirements: 1.4, 12.1, 12.2, 12.3_

    - [x] 4.1.2 Implement confirmation prompt in `run_rm()`: TTY check, format prompt with bundle name/scope/files, handle y/n/EOF
      - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.6, 31.2_

    - [x] 4.1.3 Implement removal feedback: format and print `RemovalResult` summary to stderr
      - _Requirements: 2.1, 2.2, 2.3_

    - [x] 4.1.4 Write property tests for rm confirmation and feedback
      - **Property 1: Confirmation prompt contains all required information**
      - **Property 2: Non-"y" input aborts removal**
      - **Property 3: Removal result formatting**
      - **Property 36: TTY check blocks prompt when stdin is not TTY** (rm path)
      - **Validates: Requirements 1, 2, 31.2**

  - [x] 4.2 Sync TTY check and specific confirmation — _Agent: cli-engineer_

    - [x] 4.2.1 Add TTY check to `run_sync()` confirmation; build specific message with bundle names and file counts
      - _Requirements: 13.1, 13.2, 31.1_

    - [x] 4.2.2 Write property tests for sync confirmation
      - **Property 16: Sync confirmation lists bundle names and file count**
      - **Property 36: TTY check blocks prompt** (sync path)
      - **Validates: Requirements 13, 31.1**

  - [x] 4.3 Dry-run mode — _Agent: cli-engineer_

    - [x] 4.3.1 Implement `--dry-run` logic in `run_add()`, `run_rm()`, `run_sync()` — print preview without modifying filesystem/manifest
      - _Requirements: 12.1, 12.2, 12.3, 12.4_

    - [x] 4.3.2 Write property test for dry-run
      - **Property 15: Dry-run does not modify state**
      - **Validates: Requirements 12.1, 12.2, 12.3, 12.4**

  - [x] 4.4 Informational messages to stderr — _Agent: cli-engineer_

    - [x] 4.4.1 Move `ls` empty-list message to stderr; move `registry add` success to stderr; audit all commands for stdout-only data
      - _Requirements: 32.1, 32.2, 32.3_

    - [x] 4.4.2 Write tests for stderr routing
      - **Property 37: Informational messages go to stderr not stdout**
      - **Validates: Requirements 32.1, 32.2, 32.3**

  - [x] 4.5 Checkpoint — Ensure all tests pass, ask the user if questions arise.

- [x] 5. Interactive Selectors — Headers, stderr, alternate buffer, fallback, filter, multi-select

  - [x] 5.1 Selector rendering to stderr and alternate screen buffer — _Agent: terminal-ui-engineer_

    - [x] 5.1.1 Refactor `selector.py`: change all `sys.stdout.write` to `sys.stderr.write`; add alternate screen buffer enter/exit (`\033[?1049h`/`\033[?1049l`)
      - _Requirements: 25.1, 25.2, 25.3, 30.1, 30.2, 30.3_

    - [x] 5.1.2 Write tests for stderr rendering and alternate buffer
      - **Property 30: Selector renders zero bytes to stdout**
      - **Property 35: Alternate screen buffer sequences emitted on enter/exit**
      - **Validates: Requirements 25, 30**

  - [x] 5.2 Cross-platform fallback and TERM=dumb — _Agent: terminal-ui-engineer_

    - [x] 5.2.1 Add conditional `tty`/`termios` import with `_HAS_TERMIOS` flag; implement `_use_raw_mode()` check; implement `_numbered_list_select()` fallback rendering to stderr
      - _Requirements: 26.1, 26.2, 26.3, 26.4, 29.1, 29.2, 29.3_

    - [x] 5.2.2 Write tests for fallback selector
      - **Property 31: Numbered-list fallback accepts valid numbers and rejects invalid**
      - **Property 34: TERM=dumb disables all ANSI sequences**
      - Test `q` input returns None
      - **Validates: Requirements 26, 29**

  - [x] 5.3 Headers, type-to-filter, and multi-select — _Agent: terminal-ui-engineer_

    - [x] 5.3.1 Add header and instruction lines to `render_add_selector()` and `render_removal_selector()`
      - _Requirements: 3.1, 3.2, 3.3_

    - [x] 5.3.2 Add `filter_text` parameter and filtering logic to render functions; handle alphanumeric keys and Backspace in `process_key()`
      - _Requirements: 14.1, 14.2, 14.3, 14.4_

    - [x] 5.3.3 Add `multi_selected` set parameter; handle Space toggle in `process_key()`; show checkmark/empty indicators; update `interactive_select()` and `interactive_removal_select()` to return lists
      - _Requirements: 15.1, 15.2, 15.3, 15.4_

    - [x] 5.3.4 Write property tests for selector features
      - **Property 4: Selector render includes header and instructions**
      - **Property 17: Type-to-filter produces correct filtered list**
      - **Property 18: Multi-select toggle is symmetric**
      - **Property 19: Multi-select render shows correct indicators**
      - **Validates: Requirements 3, 14, 15**

  - [x] 5.4 Checkpoint — Ensure all tests pass, ask the user if questions arise.

- [x] 6. Output Quality — ls improvements, CopyResult, file-level diff, auto-launch selector

  - [x] 6.1 Copier enhancements — _Agent: general-task-execution_

    - [x] 6.1.1 Add `CopyStatus` enum and `CopyResult` dataclass to `copier.py`; refactor `copy_file()` and `copy_tree()` to return `CopyResult`
      - _Requirements: 22.1, 22.2, 22.3_

    - [x] 6.1.2 Update `installer.py` to propagate `CopyResult` list up to callers
      - _Requirements: 22.1_

    - [x] 6.1.3 Write property test for file diff symbols
      - **Property 22: File diff summary uses distinct status symbols**
      - **Validates: Requirements 22.1, 22.2, 22.3**

  - [x] 6.2 ls improvements — _Agent: cli-output-formatter_

    - [x] 6.2.1 Rewrite `run_ls()`: grouped output by scope with headers, `--verbose` shows files, `--scope` filter, `--format json`, relative timestamps, color output
      - Add `--verbose`/`-v`, `--scope`, `--format` flags to ls parser
      - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 10.4_

    - [x] 6.2.2 Write property tests for ls
      - **Property 7: ls groups by scope and includes metadata**
      - **Property 8: ls verbose includes all installed files**
      - **Property 9: ls scope filter shows only matching scope**
      - **Property 10: ls JSON output round-trips**
      - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

  - [x] 6.3 File-level diff and auto-launch selector — _Agent: cli-engineer_

    - [x] 6.3.1 Add file-level diff output to `run_add()` and `run_sync()` using `CopyResult` data; use `+`/`~`/`=` prefixes
      - _Requirements: 22.1, 22.2, 22.3_

    - [x] 6.3.2 Implement auto-launch interactive selector in `run_add()` when no bundle spec and stdin is TTY; print error with hints when non-TTY
      - _Requirements: 9.1, 9.2, 9.3_

    - [x] 6.3.3 Write tests for auto-launch and diff output
      - Test TTY auto-launch, non-TTY error, quit returns 0
      - **Validates: Requirements 9, 22**

  - [x] 6.4 Checkpoint — Ensure all tests pass, ask the user if questions arise.

- [x] 7. New Commands — Registry ls/rm/inspect, init, info, search, completions, versioned install

  - [x] 7.1 Registry management commands — _Agent: cli-engineer_

    - [x] 7.1.1 Create `commands/registry_ls.py` — list registries with name, URL, path, bundle count
      - _Requirements: 8.1_

    - [x] 7.1.2 Create `commands/registry_rm.py` — remove named registry, block default removal, clean cache
      - _Requirements: 8.2, 8.3_

    - [x] 7.1.3 Create `commands/registry_inspect.py` — list bundles in a registry with subdirectory contents
      - _Requirements: 8.4, 8.5_

    - [x] 7.1.4 Write property tests for registry commands
      - **Property 23: Registry ls output contains all metadata**
      - **Property 24: Registry rm removes exactly the named registry**
      - **Property 25: Registry not-found error lists registered names**
      - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**

  - [x] 7.2 init, info, search commands — _Agent: cli-engineer_

    - [x] 7.2.1 Create `commands/init.py` — create `.kiro/` dir, success message, offer interactive selector on TTY
      - _Requirements: 17.1, 17.2, 17.3, 17.4_

    - [x] 7.2.2 Create `commands/info.py` — display bundle metadata, subdirectory breakdown, installed status
      - _Requirements: 18.1, 18.2, 18.3_

    - [x] 7.2.3 Create `commands/search.py` — case-insensitive name search across registries
      - _Requirements: 19.1, 19.2, 19.3_

    - [x] 7.2.4 Write property tests for init, info, search
      - **Property 27: Init creates .kiro/ directory**
      - **Property 21: Info output contains bundle metadata**
      - **Property 20: Search returns exactly matching bundles**
      - **Validates: Requirements 17, 18, 19**

  - [x] 7.3 Completions and versioned install — _Agent: cli-engineer_

    - [x] 7.3.1 Create `commands/completions.py` — generate shell completion scripts for bash/zsh/fish
      - _Requirements: 21.1, 21.2, 21.3_

    - [x] 7.3.2 Implement versioned install: parse `bundle@version` syntax in `run_add()`, add `checkout_version()` and `list_versions()` to `git_ops.py`, add `version` field to `ManifestEntry`
      - _Requirements: 20.1, 20.2, 20.3_

    - [x] 7.3.3 Write tests for completions and versioned install
      - **Property 26: Version recorded in manifest after versioned install**
      - Test `ksm completions bash/zsh/fish` produces non-empty output
      - Test non-existent version produces error with available versions
      - **Validates: Requirements 20, 21**

  - [x] 7.4 Wire all new commands into `cli.py` dispatch table — _Agent: cli-engineer_
    - Add dispatch functions for init, info, search, completions, registry ls/rm/inspect
    - _Requirements: 4.1, 17, 18, 19, 20, 21_

  - [x] 7.5 Checkpoint — Ensure all tests pass, ask the user if questions arise.

- [x] 8. Cleanup & Polish — Empty dir cleanup, signal handler integration, final validation

  - [x] 8.1 Empty directory cleanup — _Agent: general-task-execution_

    - [x] 8.1.1 Add `_cleanup_empty_dirs()` to `remover.py`; call it after file deletion in `remove_bundle()`; stop at `.kiro/` boundary
      - _Requirements: 33.1, 33.2, 33.3_

    - [x] 8.1.2 Write property test for empty dir cleanup
      - **Property 38: Empty dir cleanup removes only empty dirs up to .kiro/ boundary**
      - **Validates: Requirements 33.1, 33.2, 33.3**

  - [x] 8.2 Signal handler integration — _Agent: general-task-execution_

    - [x] 8.2.1 Call `install_signal_handler()` in `main()`; add `register_temp_dir()`/`unregister_temp_dir()` calls in `git_ops.py` clone operations and `commands/add.py` ephemeral flow
      - _Requirements: 34.1, 34.2_

  - [x] 8.3 Final integration and validation

    - [x] 8.3.1 Run full test suite, verify ≥95% coverage on all new/modified modules, fix any gaps
      - Run `black`, `flake8`, `mypy` on all code
      - _Requirements: all_

  - [x] 8.4 Final checkpoint — Ensure all tests pass, ask the user if questions arise.

## Agent Legend

| Agent | Scope |
|-------|-------|
| `cli-engineer` | Argparse design, command structure, help text, error messages, TTY checks, new commands |
| `terminal-ui-engineer` | Raw terminal mode, ANSI escape sequences, interactive selectors, cross-platform fallbacks |
| `cli-output-formatter` | Structured output formatting, color integration, JSON output, relative timestamps |
| `general-task-execution` | Data model changes, filesystem utilities, integration wiring |

Test sub-tasks within each group use the same agent as the implementation tasks (TDD: the agent writing the code writes the tests).

## Notes

- Each task references specific requirements for traceability
- Property tests use Hypothesis with dev profile (15 examples)
- Checkpoints ensure incremental validation between phases
- Refactoring existing code is preferred over writing new code
