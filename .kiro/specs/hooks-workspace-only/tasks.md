# Tasks: Handle hooks as workspace-only during global install and sync

GitHub Issue: #29
Requirements: #[[file:.kiro/specs/hooks-workspace-only/requirements.md]]
Design: #[[file:.kiro/specs/hooks-workspace-only/design.md]]

## Task List

- [x] 1. Foundation: Manifest and scanner changes

    - [x] 1.1 Add `has_hooks` field to ManifestEntry and update serialization

        - [x] 1.1.1 Write tests for `has_hooks` on ManifestEntry: serialization includes `has_hooks` only when True, deserialization defaults to False when absent, round-trip preserves the field. Add to `tests/test_manifest.py`. (FR-6.1, FR-6.2, FR-6.3)

        - [x] 1.1.2 Add `has_hooks: bool = False` field to `ManifestEntry` in `src/ksm/manifest.py`. Update `_entry_to_dict` to include `"has_hooks"` only when True. Update `_dict_to_entry` to read `data.get("has_hooks", False)`. (FR-6.1, FR-6.2, FR-6.3)

        - [x] 1.1.3 Run tests and verify all existing tests still pass alongside the new manifest tests.

    - [x] 1.2 Add `WORKSPACE_ONLY_SUBDIRS` constant to scanner

        - [x] 1.2.1 Write a test in `tests/test_scanner.py` that imports `WORKSPACE_ONLY_SUBDIRS` and asserts it contains `"hooks"` and is a subset of `RECOGNISED_SUBDIRS`.

        - [x] 1.2.2 Add `WORKSPACE_ONLY_SUBDIRS: frozenset[str] = frozenset({"hooks"})` to `src/ksm/scanner.py`.

        - [x] 1.2.3 Run tests and verify all pass.

- [x] 2. Installer: Filter hooks from global installs

    - [x] 2.1 Update `install_bundle` and `_update_manifest` to handle hooks filtering

        - [x] 2.1.1 Write tests in `tests/test_installer.py` for: (a) global install of bundle with hooks skips `hooks/` subdir and sets `has_hooks=True` on manifest entry, (b) global install of bundle without hooks sets `has_hooks=False`, (c) local install of bundle with hooks copies all subdirs including hooks and sets `has_hooks=False`, (d) property test (CP-1): for any global install, no installed file path starts with `hooks/`. (FR-1.1, FR-1.3, FR-1.4, FR-3.1)

        - [x] 2.1.2 Modify `install_bundle()` in `src/ksm/installer.py`: after `_resolve_subdirs()`, when `scope == "global"`, filter out subdirs in `WORKSPACE_ONLY_SUBDIRS`, track `hooks_skipped`. Import `WORKSPACE_ONLY_SUBDIRS` from `ksm.scanner`.

        - [x] 2.1.3 Add `has_hooks: bool = False` parameter to `_update_manifest()`. Set `entry.has_hooks = has_hooks` on both update and create paths. Pass `has_hooks=hooks_skipped` from `install_bundle()`.

        - [x] 2.1.4 Run tests and verify all pass including new and existing installer tests.

- [x] 3. Add command: Reject and warn for hooks + global scope

    - [x] 3.1 Reject `--only hooks -g` and strip hooks from mixed filters

        - [x] 3.1.1 Write tests in `tests/test_add.py` for: (a) `--only hooks -g` exits with code 1 and prints error to stderr, (b) `--only hooks -l` succeeds normally, (c) `--only hooks,steering -g` installs only steering and prints hooks warning, (d) dot notation `bundle.hooks.item -g` exits with code 1. (FR-2.1, FR-2.2, FR-2.3)

        - [x] 3.1.2 In `run_add()` in `src/ksm/commands/add.py`, after scope is determined and before dry-run check: add guard that rejects `subdirectory_filter == {"hooks"}` when `scope == "global"` (exit 1 with `format_error`). When `"hooks" in subdirectory_filter` with other values and `scope == "global"`, strip `"hooks"` from the filter.

        - [x] 3.1.3 In `run_add()`, after dot notation validation, add guard that rejects `dot_selection.subdirectory == "hooks"` when `scope == "global"` (exit 1 with `format_error`).

        - [x] 3.1.4 Run tests and verify all pass.

    - [x] 3.2 Print hooks warning after global install

        - [x] 3.2.1 Write tests in `tests/test_add.py` for: (a) global install of bundle with hooks prints warning to stderr containing "workspace" and "ksm sync", (b) global install of bundle without hooks prints no warning, (c) local install of bundle with hooks prints no warning. (FR-1.2)

        - [x] 3.2.2 In `run_add()`, after the install success output block, when `scope == "global"`: look up the manifest entry via `find_entries` and check `has_hooks`. If True, print `format_warning` to stderr advising the user to run `ksm sync`.

        - [x] 3.2.3 Apply the same `has_hooks` warning check in `_handle_ephemeral()` after its install success output block.

        - [x] 3.2.4 Run tests and verify all pass.

- [x] 4. Sync command: Distribute hooks from global bundles to workspaces

    - [x] 4.1 Implement `_sync_global_hooks` function

        - [x] 4.1.1 Write tests in `tests/test_sync.py` for: (a) `_sync_global_hooks` copies hooks from a global bundle with `has_hooks=True` to a workspace, (b) skips bundles not found in registry with warning, (c) skips workspaces that no longer exist with warning, (d) idempotent — second call produces all UNCHANGED results, (e) does nothing when no global entries have `has_hooks=True`. (FR-4.1, FR-4.2, FR-4.4, FR-4.5, FR-4.6)

        - [x] 4.1.2 Implement `_sync_global_hooks()` in `src/ksm/commands/sync.py` per the design: find global entries with `has_hooks`, resolve each from registry, copy only `hooks/` to each target workspace, print summary. Import `copy_tree` from `ksm.copier`.

        - [x] 4.1.3 Run tests and verify all pass.

    - [x] 4.2 Integrate `_sync_global_hooks` into `run_sync`

        - [x] 4.2.1 Write tests in `tests/test_sync.py` for: (a) `run_sync` with `--all` distributes hooks to all tracked workspaces, (b) `run_sync` without `--all` distributes hooks to current workspace only, (c) global entry sync via `_sync_entry` does not copy hooks (installer filtering). (FR-4.2, FR-4.3)

        - [x] 4.2.2 In `run_sync()`, after the regular sync loop and before `save_manifest`, collect target workspaces: if `sync_all`, gather all unique workspace paths from local entries plus current workspace; otherwise use current workspace only. Call `_sync_global_hooks()`.

        - [x] 4.2.3 Run tests and verify all pass.

- [x] 5. List command: Show hooks indicator

    - [x] 5.1 Update verbose list output and JSON serialization

        - [x] 5.1.1 Write tests in `tests/test_ls.py` for: (a) verbose output for a global entry with `has_hooks=True` contains `[hooks: workspace-only]`, (b) verbose output for a global entry with `has_hooks=False` does not contain the indicator, (c) verbose output for a local entry with `has_hooks=True` does not show the indicator, (d) JSON output includes `has_hooks` when True. (FR-5.1)

        - [x] 5.1.2 In `_format_grouped()` in `src/ksm/commands/ls.py`, after the verbose file listing loop, append `[hooks: workspace-only]` line when `row_entries[i].scope == "global"` and `row_entries[i].has_hooks`.

        - [x] 5.1.3 In `_entry_to_dict()` in `src/ksm/commands/ls.py`, add `has_hooks` to the JSON dict when `entry.has_hooks` is True.

        - [x] 5.1.4 Run tests and verify all pass.

- [x] 6. Final verification

    - [x] 6.1 Full test suite and linting

        - [x] 6.1.1 Run the full test suite with coverage: `source .venv/bin/activate && pytest --cov=src/ksm tests/ -v`. Verify all tests pass and coverage is ≥95% for changed files.

        - [x] 6.1.2 Run linting: `source .venv/bin/activate && black src/ tests/` then `source .venv/bin/activate && flake8 src/ tests/` then `source .venv/bin/activate && mypy src/`.

        - [x] 6.1.3 Fix any linting or coverage issues found.
