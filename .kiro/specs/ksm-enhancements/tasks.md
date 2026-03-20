# Implementation Plan: KSM Enhancements

## Overview

Refactor existing ksm modules to add CLI restructuring, registry improvements, bundle disambiguation, and message standardisation. 8 phases ordered by dependency: error helpers → CLI parser → registry add → registry remove → bundle resolution → --only consolidation → legacy/rm/inspect → final integration. All changes target existing files under `src/ksm/` — no new modules except test files. TDD approach throughout.

## Tasks

- [x] 1. Standardised message formatting and error helpers

    - [x] 1.1 Explore existing error handling patterns
        - [x] 1.1.1 Analyse `src/ksm/errors.py`, command files, and `tests/test_errors.py` to catalogue current error message patterns and identify migration points
            → Agent: context-gatherer
            _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

    - [x] 1.2 Add format helpers to errors.py

        - [x] 1.2.1 Write unit tests for `format_error`, `format_warning`, `format_deprecation` in `tests/test_errors.py`
            - Test three-line format, prefix correctness, version string inclusion, stderr output
            → Agent: general-task-execution
            _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

        - [x] 1.2.2 Write property test for message formatters
            → Agent: hypothesis-test-writer
            **Property 14: Message formatters produce correctly prefixed output**
            _Requirements: 13.1, 13.3, 13.4, 13.5_

        - [x] 1.2.3 Implement `format_error`, `format_warning`, `format_deprecation` in `src/ksm/errors.py`
            - Add three helper functions per design section 2
            → Agent: general-task-execution
            _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

        - [x] 1.2.4 Run tests and verify all pass
            → Agent: kiro

    - [x] 1.3 Checkpoint — Run full test suite, verify all tests pass
        → Agent: kiro

- [x] 2. CLI parser restructuring

    - [x] 2.1 Full-word top-level aliases

        - [x] 2.1.1 Write tests for `list`/`ls` and `remove`/`rm` alias dispatch in `tests/test_cli.py`
            - Verify both forms dispatch to the same handler, help text shows full-word primary with short alias
            → Agent: general-task-execution
            _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_

        - [x] 2.1.2 Write property test for alias dispatch equivalence
            → Agent: hypothesis-test-writer
            **Property 9: Full-word and short command aliases produce identical dispatch**
            _Requirements: 9.5, 9.6_

        - [x] 2.1.3 Refactor `_build_parser()` in `src/ksm/cli.py` to add `list`/`remove` as primary commands with `ls`/`rm` aliases
            - Add both names to dispatch table, use `argparse.SUPPRESS` on short alias help
            → Agent: argparse-cli-refactorer
            _Requirements: 9.1, 9.2, 9.3, 9.4, 9.7_

        - [x] 2.1.4 Run tests and verify all pass
            → Agent: kiro

    - [x] 2.2 Registry subcommand group restructuring

        - [x] 2.2.1 Write tests for `registry` subcommand group in `tests/test_cli.py`
            - `registry remove`/`rm` and `registry list`/`ls` aliases, `registry` without subcommand → exit 2, `registry --help` → exit 0, `registry <sub> --help` → exit 0
            → Agent: general-task-execution
            _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 7.11_

        - [x] 2.2.2 Refactor `_build_parser()` registry subparsers to use `remove`/`list` as primaries with `rm`/`ls` aliases, add `inspect` subcommand
            - Update `_dispatch_registry()` to handle both canonical and alias names
            → Agent: argparse-cli-refactorer
            _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 7.11_

        - [x] 2.2.3 Run tests and verify all pass
            → Agent: kiro

    - [x] 2.3 Rename --display to -i/--interactive

        - [x] 2.3.1 Write tests for `-i`/`--interactive` on add and rm commands in `tests/test_cli.py`
            - `--display` hidden from help, deprecation warning on use, `-i` flag parses correctly
            → Agent: general-task-execution
            _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

        - [x] 2.3.2 Refactor `_build_parser()` to add `-i`/`--interactive` and hide `--display` with `argparse.SUPPRESS` on both `add` and `rm` subparsers
            → Agent: argparse-cli-refactorer
            _Requirements: 5.1, 5.2, 5.3, 5.4_

        - [x] 2.3.3 Run tests and verify all pass
            → Agent: kiro

    - [x] 2.4 Add --force, --name, and --only flags

        - [x] 2.4.1 Write tests for `-f`/`--force`, `--name`, and `--only` flag parsing in `tests/test_cli.py`
            - Verify flags parse correctly on `registry add` and legacy `add-registry` subparsers, `--only` on `add`, `--*-only` hidden
            → Agent: general-task-execution
            _Requirements: 6.1, 6.2, 6.3, 11.1, 12.1, 12.2, 12.3_

        - [x] 2.4.2 Refactor `_build_parser()` to add `-f`/`--force` and `--name` on `registry add` and `add-registry`, `--only` on `add`, hide `--*-only` flags with `argparse.SUPPRESS`
            → Agent: argparse-cli-refactorer
            _Requirements: 6.1, 6.2, 6.3, 11.1, 12.1, 12.6_

        - [x] 2.4.3 Run tests and verify all pass
            → Agent: kiro

    - [x] 2.5 Checkpoint — Run full test suite, verify all tests pass
        → Agent: kiro

- [x] 3. Registry add improvements

    - [x] 3.1 Cache conflict handling, --force, and --name

        - [x] 3.1.1 Write unit tests for cache conflict scenarios in `tests/test_registry_commands.py`
            - Same-URL re-add without --force → error with path and --force suggestion
            - Different-URL collision → error with --name suggestion, no --force
            - --force removes cache and re-clones
            - Clone failure after --force → rollback warning
            - No conflict → normal clone and register
            → Agent: general-task-execution
            _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

        - [x] 3.1.2 Write property test for same-URL cache conflict error
            → Agent: hypothesis-test-writer
            **Property 1: Cache conflict same-URL error contains path and --force suggestion**
            _Requirements: 1.1, 1.2, 1.3_

        - [x] 3.1.3 Write property test for different-URL cache conflict error
            → Agent: hypothesis-test-writer
            **Property 2: Cache conflict different-URL error suggests --name and omits --force**
            _Requirements: 1.4_

        - [x] 3.1.4 Write property test for cache namespace
            → Agent: hypothesis-test-writer
            **Property 16: Cache directory uses registry name as namespace**
            _Requirements: 1.8_

        - [x] 3.1.5 Refactor `run_registry_add()` in `src/ksm/commands/registry_add.py`
            - Add `_find_entry_by_cache()`, --force logic, cache conflict detection, --name support per design section 4
            → Agent: general-task-execution
            _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

        - [x] 3.1.6 Run tests and verify all pass
            → Agent: kiro

    - [x] 3.2 Duplicate URL detection and custom name

        - [x] 3.2.1 Write unit tests for duplicate URL detection and --name in `tests/test_registry_commands.py`
            - Duplicate URL → prints existing name, exit 0
            - --name overrides derived name
            - --name collision with existing registry → error exit 1
            → Agent: general-task-execution
            _Requirements: 2.1, 2.2, 11.2, 11.3, 11.4_

        - [x] 3.2.2 Write property test for duplicate URL detection
            → Agent: hypothesis-test-writer
            **Property 3: Duplicate URL detection returns existing name and exit code 0**
            _Requirements: 2.1, 2.2_

        - [x] 3.2.3 Write property test for _derive_name idempotence
            → Agent: hypothesis-test-writer
            **Property 10: _derive_name produces consistent URL-derived names**
            _Requirements: 11.3_

        - [x] 3.2.4 Refactor `run_registry_add()` to use `format_error` for duplicate URL message and support `--name` flag
            → Agent: general-task-execution
            _Requirements: 2.1, 2.2, 11.2, 11.3, 11.4_

        - [x] 3.2.5 Run tests and verify all pass
            → Agent: kiro

    - [x] 3.3 Checkpoint — Run full test suite, verify all tests pass
        → Agent: kiro

- [x] 4. Registry remove improvements

    - [x] 4.1 Improved feedback messages

        - [x] 4.1.1 Write unit tests for registry remove feedback in `tests/test_registry_commands.py`
            - Cache cleaned → message with path
            - Cache absent → "already absent" message
            - Permission error → warning, still removes from index, exit 0
            - Not-found → lists all registered names
            → Agent: general-task-execution
            _Requirements: 3.1, 3.2, 3.3, 3.4_

        - [x] 4.1.2 Write property test for remove feedback matching cache state
            → Agent: hypothesis-test-writer
            **Property 4: Registry remove feedback matches cache state**
            _Requirements: 3.1, 3.2_

        - [x] 4.1.3 Write property test for remove not-found error
            → Agent: hypothesis-test-writer
            **Property 5: Registry remove not-found error lists all registered names**
            _Requirements: 3.4_

        - [x] 4.1.4 Refactor `run_registry_rm()` in `src/ksm/commands/registry_rm.py`
            - Use `format_error`/`format_warning`, add cache state feedback, permission error handling per design section 5
            → Agent: general-task-execution
            _Requirements: 3.1, 3.2, 3.3, 3.4_

        - [x] 4.1.5 Run tests and verify all pass
            → Agent: kiro

    - [x] 4.2 Checkpoint — Run full test suite, verify all tests pass
        → Agent: kiro

- [-] 5. Bundle resolution and qualified names

    - [x] 5.1 Multi-match resolver and qualified name parsing

        - [x] 5.1.1 Write unit tests for `ResolvedBundleResult`, `resolve_bundle` multi-match, and `parse_qualified_name` in `tests/test_resolver.py`
            - Zero matches → empty result
            - Single match → one-element list
            - Multiple matches → all collected
            - Qualified name parsing round-trip
            - `resolve_qualified_bundle` with missing registry → error listing registries
            - `resolve_qualified_bundle` with missing bundle → error
            → Agent: general-task-execution
            _Requirements: 4.6, 10.1, 10.2, 10.3, 10.4_

        - [x] 5.1.2 Write property test for qualified name round-trip
            → Agent: hypothesis-test-writer
            **Property 8: Qualified name round-trip parsing**
            _Requirements: 10.2_

        - [x] 5.1.3 Write property test for ambiguous resolution error
            → Agent: hypothesis-test-writer
            **Property 7: Ambiguous bundle resolution error lists all registries and suggests qualified syntax**
            _Requirements: 4.3, 4.4, 4.6_

        - [x] 5.1.4 Refactor `src/ksm/resolver.py` to add `ResolvedBundleResult`, change `resolve_bundle` to return all matches, add `parse_qualified_name` and `resolve_qualified_bundle`
            → Agent: general-task-execution
            _Requirements: 4.6, 10.1, 10.2, 10.3, 10.4_

        - [x] 5.1.5 Run tests and verify all pass
            → Agent: kiro

    - [x] 5.2 Scanner registry_name population

        - [x] 5.2.1 Write tests verifying `scan_registry` populates `registry_name` on each BundleInfo when called with a registry name parameter in `tests/test_scanner.py`
            → Agent: general-task-execution
            _Requirements: 4.5_

        - [x] 5.2.2 Refactor `scan_registry()` in `src/ksm/scanner.py` to accept an optional `registry_name` parameter and populate it on each BundleInfo
            → Agent: general-task-execution
            _Requirements: 4.5_

        - [x] 5.2.3 Update callers of `scan_registry()` to pass registry name where available (resolver.py, registry_inspect.py, registry_ls.py, add.py)
            → Agent: general-task-execution
            _Requirements: 4.5_

        - [x] 5.2.4 Run tests and verify all pass
            → Agent: kiro

    - [ ] 5.3 Add command qualified name and ambiguity handling

        - [ ] 5.3.1 Write tests for qualified name install and ambiguity error in `tests/test_add.py`
            - `registry/bundle` syntax resolves correctly
            - Ambiguous unqualified name → error listing registries with suggestion
            - `-i` ignored when bundle_spec provided (with stderr message)
            - `--display` prints deprecation warning and behaves as `-i`
            → Agent: general-task-execution
            _Requirements: 4.3, 4.4, 5.5, 5.7, 5.9, 10.1, 10.3, 10.4_

        - [ ] 5.3.2 Refactor `run_add()` in `src/ksm/commands/add.py`
            - Use `parse_qualified_name`, handle multi-match with `format_error`, add `-i`/`--display` deprecation logic
            → Agent: general-task-execution
            _Requirements: 4.3, 4.4, 5.5, 5.7, 5.9, 10.1, 10.3, 10.4_

        - [ ] 5.3.3 Run tests and verify all pass
            → Agent: kiro

    - [ ] 5.4 Selector qualified name display

        - [ ] 5.4.1 Write tests for ambiguous name display in `tests/test_selector.py`
            - Ambiguous bundles show `registry/bundle` format
            - Unique bundles show plain name
            → Agent: general-task-execution
            _Requirements: 4.1, 4.2, 10.5, 10.6_

        - [ ] 5.4.2 Write property test for selector qualification
            → Agent: hypothesis-test-writer
            **Property 6: Selector qualifies ambiguous bundle names and leaves unique names unqualified**
            _Requirements: 4.1, 4.2, 10.5, 10.6_

        - [ ] 5.4.3 Refactor `render_add_selector()` in `src/ksm/selector.py` to detect ambiguous names and display qualified format
            → Agent: general-task-execution
            _Requirements: 4.1, 4.2, 10.5, 10.6_

        - [ ] 5.4.4 Run tests and verify all pass
            → Agent: kiro

    - [ ] 5.5 Checkpoint — Run full test suite, verify all tests pass
        → Agent: kiro

- [ ] 6. --only consolidation and deprecation wiring

    - [ ] 6.1 --only flag parsing and validation

        - [ ] 6.1.1 Write tests for `_build_subdirectory_filter` with --only in `tests/test_add.py`
            - Comma-separated parsing, repeated --only, invalid value → exit 2
            - Deprecated --*-only flags → deprecation warning + equivalent filter
            - Mutual exclusion with dot notation (Req 12.8)
            → Agent: general-task-execution
            _Requirements: 12.2, 12.3, 12.4, 12.5, 12.7, 12.8_

        - [ ] 6.1.2 Write property test for --only comma parsing
            → Agent: hypothesis-test-writer
            **Property 11: --only comma-separated parsing produces correct filter set**
            _Requirements: 12.2_

        - [ ] 6.1.3 Write property test for --only invalid value rejection
            → Agent: hypothesis-test-writer
            **Property 12: --only rejects invalid values with exit code 2**
            _Requirements: 12.5_

        - [ ] 6.1.4 Write property test for deprecated --*-only equivalence
            → Agent: hypothesis-test-writer
            **Property 13: Deprecated --*-only flags produce deprecation warning and equivalent filter**
            _Requirements: 12.7_

        - [ ] 6.1.5 Refactor `_build_subdirectory_filter()` in `src/ksm/commands/add.py`
            - Parse --only with comma splitting, validate values, emit deprecation for old flags, enforce mutual exclusion with dot notation
            → Agent: general-task-execution
            _Requirements: 12.2, 12.3, 12.4, 12.5, 12.7, 12.8_

        - [ ] 6.1.6 Run tests and verify all pass
            → Agent: kiro

    - [ ] 6.2 Checkpoint — Run full test suite, verify all tests pass
        → Agent: kiro

- [ ] 7. Legacy wrapper, rm -i handling, and inspect output

    - [ ] 7.1 Legacy add-registry deprecation wrapper

        - [ ] 7.1.1 Write tests for legacy `add-registry` deprecation in `tests/test_add_registry.py`
            - Prints deprecation warning with version numbers, delegates to `run_registry_add`, retains backward compatibility
            → Agent: general-task-execution
            _Requirements: 8.1, 8.2, 8.3, 8.4_

        - [ ] 7.1.2 Refactor `run_add_registry()` in `src/ksm/commands/add_registry.py` to be a thin wrapper
            - Print `format_deprecation` then delegate to `registry_add.run_registry_add`
            → Agent: general-task-execution
            _Requirements: 8.1, 8.2, 8.3, 8.4_

        - [ ] 7.1.3 Run tests and verify all pass
            → Agent: kiro

    - [ ] 7.2 Remove command -i handling

        - [ ] 7.2.1 Write tests for rm `-i`/`--display` deprecation in `tests/test_rm.py`
            - `--display` prints deprecation, `-i` launches selector, `-i` ignored when bundle_name provided (with stderr message)
            → Agent: general-task-execution
            _Requirements: 5.2, 5.6, 5.8, 5.10_

        - [ ] 7.2.2 Refactor `run_rm()` in `src/ksm/commands/rm.py` to handle `-i`/`--display` deprecation
            - Same pattern as add.py: check --display → deprecation warning, -i ignored when bundle_name provided
            → Agent: general-task-execution
            _Requirements: 5.2, 5.6, 5.8, 5.10_

        - [ ] 7.2.3 Run tests and verify all pass
            → Agent: kiro

    - [ ] 7.3 Registry inspect enhanced output

        - [ ] 7.3.1 Write tests for inspect output fields in `tests/test_registry_commands.py`
            - Output contains name, URL (or "(local)"), path, default status, bundle names with subdirectory types
            - Not-found error lists available registries
            → Agent: general-task-execution
            _Requirements: 14.1, 14.2, 14.3, 14.4_

        - [ ] 7.3.2 Write property test for inspect output completeness
            → Agent: hypothesis-test-writer
            **Property 15: Registry inspect output contains all required fields and bundles**
            _Requirements: 14.1, 14.2, 14.4_

        - [ ] 7.3.3 Refactor `run_registry_inspect()` in `src/ksm/commands/registry_inspect.py`
            - Add URL, default status fields per design section 9
            → Agent: general-task-execution
            _Requirements: 14.1, 14.2, 14.3, 14.4_

        - [ ] 7.3.4 Run tests and verify all pass
            → Agent: kiro

    - [ ] 7.4 Checkpoint — Run full test suite, verify all tests pass
        → Agent: kiro

- [ ] 8. Final integration and cleanup

    - [ ] 8.1 Wire dispatch table and cross-module integration

        - [ ] 8.1.1 Write integration tests verifying end-to-end flows in `tests/test_integration.py`
            - `registry add` with --force, `registry remove` with feedback, `add` with qualified name
            - `_dispatch_registry` handles `remove`/`list` canonical names
            - Legacy `add-registry` delegates correctly with --force and --name
            → Agent: general-task-execution
            _Requirements: 1.5, 3.1, 4.3, 7.6, 8.2, 10.1_

        - [ ] 8.1.2 Update `_dispatch_registry()` and `_dispatch_add_registry()` in `src/ksm/cli.py`
            - Ensure `registry add` dispatches to `registry_add.run_registry_add`
            - Pass `--force` and `--name` args through
            - Ensure `add-registry` dispatches to legacy wrapper
            → Agent: argparse-cli-refactorer
            _Requirements: 7.1, 7.6, 8.1, 8.2_

        - [ ] 8.1.3 Migrate remaining ad-hoc error messages across all commands to use `format_error`/`format_warning`/`format_deprecation` helpers
            → Agent: general-task-execution
            _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

        - [ ] 8.1.4 Run tests and verify all pass
            → Agent: kiro

    - [ ] 8.2 Final checkpoint — Run full test suite, verify all tests pass, lint with black and flake8
        → Agent: kiro

    - [ ] 8.3 Create pull request
        → Skill: github-pr

## Notes

- All refactors target existing files — no new modules except test files
- Property tests use Hypothesis with dev/ci profiles (conftest.py already configured)
- Each property test references its design property number and validated requirements
- Checkpoints ensure incremental validation after each phase
