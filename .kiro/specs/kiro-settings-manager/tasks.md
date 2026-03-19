# Implementation Plan: Kiro Settings Manager (`ksm`)

## Overview

Incremental, TDD-driven implementation of the `ksm` CLI tool. Each group writes tests first, then implementation, building from infrastructure up through domain logic to CLI wiring. Property-based tests (Hypothesis) validate correctness properties from the design; unit tests cover concrete scenarios and edge cases.

## Tasks

- [x] 1. Project Scaffolding and Infrastructure Layer

    - [x] 1.1 Project skeleton and packaging

        - [x] 1.1.1 Create `pyproject.toml` with project metadata, `[project.scripts]` entry point, and `[project.optional-dependencies] dev` list
            - Include pytest, pytest-cov, hypothesis, black, flake8, flake8-pyproject, mypy
            - Register `ksm = "ksm.cli:main"`
            - _Requirements: 8.1, 8.2_

        - [x] 1.1.2 Create `src/ksm/__init__.py` with `__version__ = "0.1.0"`
            - _Requirements: 8.4_

        - [x] 1.1.3 Create `src/ksm/errors.py` with custom exception classes
            - `BundleNotFoundError`, `GitError`, `InvalidSubdirectoryError`, `MutualExclusionError`
            - _Requirements: 1.5, 5.5, 11.3, 11.9_

        - [x] 1.1.4 Create `src/ksm/commands/__init__.py` (empty)

        - [x] 1.1.5 Create `tests/conftest.py` with Hypothesis dev/ci profiles and shared fixtures
            - dev: `max_examples=15, deadline=None`; ci: `max_examples=100, deadline=None`
            - Load profile from `HYPOTHESIS_PROFILE` env var, default `dev`

        - [x] 1.1.6 Set up virtual environment and install project in editable mode
            - `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`

    - [x] 1.2 Persistence module (JSON I/O)

        - [x] 1.2.1 Write tests for `persistence.py` in `tests/test_persistence.py`
            - Test `ensure_ksm_dir` creates `~/.kiro/ksm/` (use `tmp_path`)
            - Test `read_json` / `write_json` round-trip
            - Test `read_json` on missing file raises `FileNotFoundError`
            - _Requirements: 6.1, 6.2, 6.3_

        - [x] 1.2.2 Write property test for JSON round-trip in `tests/test_persistence.py`
            - **Property 15: Registry index JSON round-trip**
            - **Property 16: Manifest JSON round-trip**
            - **Validates: Requirements 6.5, 6.6**

        - [x] 1.2.3 Implement `src/ksm/persistence.py`
            - `KSM_DIR`, `REGISTRIES_FILE`, `MANIFEST_FILE` constants
            - `ensure_ksm_dir()`, `read_json()`, `write_json()`
            - _Requirements: 6.1, 6.2, 6.3_

    - [x] 1.3 Checkpoint — Verify infrastructure layer
        - Ensure all tests pass, ask the user if questions arise.


- [x] 2. Domain Layer — Data Models and Pure Logic

    - [x] 2.1 Registry index module

        - [x] 2.1.1 Write tests for `registry.py` in `tests/test_registry.py`
            - Test `load_registry_index` creates default entry on first run
            - Test `save_registry_index` / `load_registry_index` round-trip
            - Test duplicate registry detection
            - _Requirements: 6.1, 6.4, 5.4_

        - [x] 2.1.2 Write property test for registry round-trip
            - **Property 15: Registry index JSON round-trip**
            - **Validates: Requirements 6.5**

        - [x] 2.1.3 Write property test for duplicate registry no-op
            - **Property 14: Duplicate registry is a no-op**
            - **Validates: Requirements 5.4**

        - [x] 2.1.4 Implement `src/ksm/registry.py`
            - `RegistryEntry`, `RegistryIndex` dataclasses
            - `load_registry_index()`, `save_registry_index()`
            - _Requirements: 6.1, 6.4, 6.5_

    - [x] 2.2 Manifest module

        - [x] 2.2.1 Write tests for `manifest.py` in `tests/test_manifest.py`
            - Test `load_manifest` returns empty manifest when file missing
            - Test `save_manifest` / `load_manifest` round-trip
            - Test manifest entry lookup by name and scope
            - _Requirements: 6.2, 6.6_

        - [x] 2.2.2 Write property test for manifest round-trip
            - **Property 16: Manifest JSON round-trip**
            - **Validates: Requirements 6.6**

        - [x] 2.2.3 Implement `src/ksm/manifest.py`
            - `ManifestEntry`, `Manifest` dataclasses
            - `load_manifest()`, `save_manifest()`
            - _Requirements: 6.2, 6.6_

    - [x] 2.3 Scanner module

        - [x] 2.3.1 Write tests for `scanner.py` in `tests/test_scanner.py`
            - Test scanning a directory with valid bundles
            - Test scanning ignores directories without recognised subdirs
            - Test scanning empty directory returns empty list
            - _Requirements: 5.2, 7.1_

        - [x] 2.3.2 Write property test for scanner identification
            - **Property 13: Scanner identifies valid bundles**
            - **Validates: Requirements 5.2**

        - [x] 2.3.3 Implement `src/ksm/scanner.py`
            - `RECOGNISED_SUBDIRS`, `BundleInfo` dataclass, `scan_registry()`
            - _Requirements: 5.2, 7.1_

    - [x] 2.4 Dot notation module

        - [x] 2.4.1 Write tests for `dot_notation.py` in `tests/test_dot_notation.py`
            - Test parsing plain name returns `None`
            - Test parsing valid dot notation returns `DotSelection`
            - Test invalid subdirectory type raises `InvalidSubdirectoryError`
            - Test malformed strings (too few/many dots)
            - _Requirements: 11.1, 11.2, 11.3_

        - [x] 2.4.2 Write property test for dot notation validation
            - **Property 28: Dot notation validates subdirectory type**
            - **Validates: Requirements 11.2, 11.3**

        - [x] 2.4.3 Implement `src/ksm/dot_notation.py`
            - `DotSelection` dataclass, `parse_dot_notation()`, `validate_dot_selection()`
            - _Requirements: 11.1, 11.2, 11.3_

    - [x] 2.5 Copier module

        - [x] 2.5.1 Write tests for `copier.py` in `tests/test_copier.py`
            - Test `copy_file` copies content byte-for-byte
            - Test `copy_file` skips identical files
            - Test `copy_tree` preserves directory structure
            - Test `files_identical` returns correct results
            - _Requirements: 7.2, 7.3, 7.4, 7.5_

        - [x] 2.5.2 Write property tests for copier
            - **Property 18: File copy preserves structure and content**
            - **Property 19: Identical files are skipped**
            - **Validates: Requirements 7.2, 7.3, 7.4, 7.5**

        - [x] 2.5.3 Implement `src/ksm/copier.py`
            - `copy_tree()`, `copy_file()`, `files_identical()`
            - _Requirements: 7.2, 7.3, 7.4, 7.5_

    - [x] 2.6 Checkpoint — Verify data models and pure logic
        - Ensure all tests pass, ask the user if questions arise.


- [x] 3. Domain Layer — Orchestration Modules

    - [x] 3.1 Resolver module

        - [x] 3.1.1 Write tests for `resolver.py` in `tests/test_resolver.py`
            - Test resolving a bundle found in default registry
            - Test resolving a bundle found in custom registry
            - Test `BundleNotFoundError` for unknown bundle
            - _Requirements: 1.1, 1.5_

        - [x] 3.1.2 Write property test for unknown bundle error
            - **Property 2: Unknown bundle produces error**
            - **Validates: Requirements 1.5**

        - [x] 3.1.3 Implement `src/ksm/resolver.py`
            - `ResolvedBundle` dataclass, `resolve_bundle()`
            - _Requirements: 1.1, 1.5_

    - [x] 3.2 Installer module

        - [x] 3.2.1 Write tests for `installer.py` in `tests/test_installer.py`
            - Test full bundle installation copies all recognised subdirs
            - Test filtered installation copies only specified subdirs
            - Test dot-notation installation copies only target item
            - Test manifest is updated with installed file paths
            - Test target subdirectory creation when missing
            - Test warning for missing filtered subdirectory
            - Test error when all filters miss
            - _Requirements: 1.1, 1.6, 1.7, 7.1, 10.1–10.9, 11.1, 11.5, 11.6_

        - [x] 3.2.2 Write property tests for installer
            - **Property 3: Manifest records exactly the installed files**
            - **Property 4: Reinstallation is idempotent**
            - **Property 17: Only recognised subdirectories are copied**
            - **Property 24: Subdirectory filter restricts copied directories**
            - **Property 25: Warning for missing filtered subdirectory**
            - **Property 26: Error when all filters miss**
            - **Property 27: Dot notation installs only the target item**
            - **Validates: Requirements 1.7, 1.8, 7.1, 10.1–10.9, 11.1, 11.7**

        - [x] 3.2.3 Implement `src/ksm/installer.py`
            - `install_bundle()` with scope, filter, and dot-selection support
            - _Requirements: 1.1, 1.6, 1.7, 1.8, 7.1, 10.1–10.9, 11.1, 11.5, 11.6, 11.7_

    - [x] 3.3 Remover module

        - [x] 3.3.1 Write tests for `remover.py` in `tests/test_remover.py`
            - Test removal deletes all manifest-listed files
            - Test removal skips files that no longer exist on disk
            - Test manifest entry is removed after deletion
            - Test empty subdirectories are preserved
            - _Requirements: 12.1, 12.2, 12.7, 12.8_

        - [x] 3.3.2 Write property tests for remover
            - **Property 32: Removal deletes exactly the manifest-listed files**
            - **Property 33: Removal removes the manifest entry**
            - **Property 36: Missing files on disk are skipped gracefully**
            - **Property 37: Empty subdirectories are preserved after removal**
            - **Validates: Requirements 12.1, 12.2, 12.7, 12.8**

        - [x] 3.3.3 Implement `src/ksm/remover.py`
            - `RemovalResult` dataclass, `remove_bundle()`
            - _Requirements: 12.1, 12.2, 12.7, 12.8_

    - [x] 3.4 Git operations module

        - [x] 3.4.1 Write tests for `git_ops.py` in `tests/test_git_ops.py`
            - Test `clone_repo` calls subprocess with correct args (mocked)
            - Test `pull_repo` calls subprocess with correct args (mocked)
            - Test `clone_ephemeral` returns temp path and clones (mocked)
            - Test `GitError` raised on subprocess failure
            - _Requirements: 5.1, 5.5, 9.1, 9.4_

        - [x] 3.4.2 Write property test for ephemeral cleanup
            - **Property 22: Ephemeral clone is cleaned up**
            - **Validates: Requirements 9.4**

        - [x] 3.4.3 Implement `src/ksm/git_ops.py`
            - `clone_repo()`, `pull_repo()`, `clone_ephemeral()`
            - _Requirements: 5.1, 5.5, 9.1, 9.4_

    - [x] 3.5 Selector module

        - [x] 3.5.1 Write tests for `selector.py` in `tests/test_selector.py`
            - Test render output shows bundles alphabetically with `>` prefix
            - Test `[installed]` label appears for installed bundles
            - Test arrow key navigation clamps at boundaries
            - Test Enter returns selected bundle name
            - Test `q`/Escape returns `None`
            - Test removal selector shows scope labels
            - _Requirements: 2.1–2.8, 12.9–12.17_

        - [x] 3.5.2 Write property tests for selector
            - **Property 5: Selector presents all bundles sorted alphabetically**
            - **Property 6: Installed label accuracy**
            - **Property 7: Arrow key navigation wraps correctly**
            - **Property 38: Removal selector shows installed bundles with scope labels sorted alphabetically**
            - **Validates: Requirements 2.1, 2.2, 2.5, 2.6, 12.9, 12.10, 12.13**

        - [x] 3.5.3 Implement `src/ksm/selector.py`
            - `interactive_select()`, `interactive_removal_select()`
            - Raw terminal mode via `tty`/`termios`, `>` prefix, `[installed]`/`[local]`/`[global]` labels
            - _Requirements: 2.1–2.8, 12.9–12.17_

    - [x] 3.6 Checkpoint — Verify orchestration modules
        - Ensure all tests pass, ask the user if questions arise.


- [x] 4. Command Layer

    - [x] 4.1 `commands/add.py`

        - [x] 4.1.1 Write tests for `commands/add.py` in `tests/test_add.py`
            - Test `run_add` with plain bundle name installs to local `.kiro/`
            - Test `-g` flag installs to global `~/.kiro/`
            - Test `--display` launches interactive selector
            - Test `--from` clones ephemeral registry and cleans up
            - Test subdirectory filter flags restrict installation
            - Test dot notation + subdirectory filter raises mutual exclusion error
            - Test ephemeral registry is not persisted in registry index
            - Test ephemeral source recorded as git URL in manifest
            - _Requirements: 1.1–1.8, 9.1–9.8, 10.1–10.10, 11.1–11.9_

        - [x] 4.1.2 Write property tests for add command
            - **Property 1: Scope flag determines target directory**
            - **Property 21: Ephemeral registry is not persisted**
            - **Property 23: Ephemeral source recorded as git URL**
            - **Property 29: Dot notation missing item produces error**
            - **Property 30: Dot notation copies correct item type**
            - **Property 31: Dot notation and subdirectory filter are mutually exclusive**
            - **Validates: Requirements 1.2, 1.3, 1.4, 9.3, 9.7, 11.4, 11.5, 11.6, 11.9**

        - [x] 4.1.3 Implement `src/ksm/commands/add.py`
            - `run_add()` orchestrating resolver, installer, selector, dot_notation, git_ops
            - _Requirements: 1.1–1.8, 9.1–9.8, 10.1–10.10, 11.1–11.9_

    - [x] 4.2 `commands/ls.py`

        - [x] 4.2.1 Write tests for `commands/ls.py` in `tests/test_ls.py`
            - Test output contains bundle name, scope, and source registry for each entry
            - Test empty manifest prints "no bundles installed" message
            - _Requirements: 3.1, 3.2, 3.3_

        - [x] 4.2.2 Write property test for ls output
            - **Property 8: ls displays all manifest entries with required fields**
            - **Validates: Requirements 3.1, 3.2**

        - [x] 4.2.3 Implement `src/ksm/commands/ls.py`
            - `run_ls()` reading manifest and formatting output
            - _Requirements: 3.1, 3.2, 3.3_

    - [x] 4.3 `commands/sync.py`

        - [x] 4.3.1 Write tests for `commands/sync.py` in `tests/test_sync.py`
            - Test confirmation prompt aborts on non-`y` input
            - Test `--yes` skips confirmation
            - Test sync re-copies files from source registry
            - Test sync with `--all` syncs all installed bundles
            - Test unknown bundle name prints error and continues
            - Test manifest `updated_at` timestamp is updated after sync
            - Test no args and no `--all` prints usage message
            - Test git pull called for custom registries before sync
            - _Requirements: 4.1–4.11_

        - [x] 4.3.2 Write property tests for sync command
            - **Property 9: Sync aborts on non-y confirmation**
            - **Property 10: Sync re-copies bundle files from source**
            - **Property 11: Sync continues past unknown bundles**
            - **Property 12: Sync updates manifest timestamp**
            - **Validates: Requirements 4.4, 4.6, 4.7, 4.8, 4.10**

        - [x] 4.3.3 Implement `src/ksm/commands/sync.py`
            - `run_sync()` with confirmation prompt, `--yes`, `--all`, git pull
            - _Requirements: 4.1–4.11_

    - [x] 4.4 `commands/add_registry.py`

        - [x] 4.4.1 Write tests for `commands/add_registry.py` in `tests/test_add_registry.py`
            - Test cloning a new git repo and registering it
            - Test duplicate URL prints message and exits 0
            - Test git clone failure prints error and exits 1
            - Test scanned bundles are registered from cloned repo
            - _Requirements: 5.1–5.5_

        - [x] 4.4.2 Implement `src/ksm/commands/add_registry.py`
            - `run_add_registry()` orchestrating git_ops, scanner, registry
            - _Requirements: 5.1–5.5_

    - [x] 4.5 `commands/rm.py`

        - [x] 4.5.1 Write tests for `commands/rm.py` in `tests/test_rm.py`
            - Test `run_rm` removes files and updates manifest
            - Test `-l`/`-g` scope flags resolve correct target directory
            - Test `--display` launches removal selector
            - Test unknown bundle prints error and exits 1
            - Test no bundles installed with `--display` prints message and exits 0
            - _Requirements: 12.1–12.17_

        - [x] 4.5.2 Write property tests for rm command
            - **Property 34: Unknown bundle in rm produces error**
            - **Property 35: Rm scope flag determines target directory**
            - **Validates: Requirements 12.3, 12.4, 12.5, 12.6**

        - [x] 4.5.3 Implement `src/ksm/commands/rm.py`
            - `run_rm()` orchestrating remover, manifest, selector
            - _Requirements: 12.1–12.17_

    - [x] 4.6 Checkpoint — Verify command layer
        - Ensure all tests pass, ask the user if questions arise.


- [x] 5. CLI Entry Point and Integration

    - [x] 5.1 CLI module

        - [x] 5.1.1 Write tests for `cli.py` in `tests/test_cli.py`
            - Test `--help` displays help with all commands listed
            - Test `--version` displays version string
            - Test unknown command exits with non-zero status and lists valid commands
            - Test each subcommand dispatches to correct handler
            - _Requirements: 8.2, 8.3, 8.4, 8.5_

        - [x] 5.1.2 Write property test for unknown command error
            - **Property 20: Unknown CLI command produces error**
            - **Validates: Requirements 8.5**

        - [x] 5.1.3 Implement `src/ksm/cli.py`
            - `main()` with argparse, subparsers for `add`, `ls`, `sync`, `add-registry`, `rm`
            - Global `--version` flag
            - _Requirements: 8.1–8.5_

    - [x] 5.2 Integration wiring and end-to-end tests

        - [x] 5.2.1 Write integration tests in `tests/test_integration.py`
            - Test full `add` → `ls` → `sync` → `rm` workflow using tmp_path fixtures
            - Test `add` with `--from` ephemeral registry end-to-end
            - Test `add` with dot notation end-to-end
            - Test `add` with subdirectory filters end-to-end
            - Test `add-registry` with mocked git clone end-to-end
            - _Requirements: 1.1–1.8, 3.1–3.3, 4.1–4.11, 9.1–9.8, 12.1–12.8_

        - [x] 5.2.2 Verify all modules are wired together correctly
            - Ensure CLI dispatches to commands, commands use domain modules, domain modules use infrastructure
            - Run full test suite and confirm no import errors or missing dependencies

    - [x] 5.3 Coverage and linting verification

        - [x] 5.3.1 Run `pytest --cov=ksm --cov-report=term-missing` and verify ≥95% coverage
            - Identify and fill any coverage gaps with additional tests

        - [x] 5.3.2 Run `black src/ tests/` and `flake8 src/ tests/` and `mypy src/`
            - Fix any formatting, style, or type errors

    - [x] 5.4 Final checkpoint — All tests pass with ≥95% coverage
        - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks are required
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each layer
- Property tests validate the 38 correctness properties from the design document
- Unit tests validate specific examples, edge cases, and error conditions
- TDD: write tests before implementation in every group
- All code must pass black, flake8, and mypy before task completion
