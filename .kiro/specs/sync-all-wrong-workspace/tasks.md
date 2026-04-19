# Tasks: sync --all wrong workspace fix

GitHub Issue: #30

- [x] 1. Fix workspace-path-aware sync targeting

    - [x] 1.1 Write tests for the fix

        - [x] 1.1.1 Write unit test: `_sync_entry` with a local entry whose `workspace_path` differs from `target_local` syncs files to the correct workspace directory

        - [x] 1.1.2 Write unit test: `_sync_entry` with a local entry whose `workspace_path` is `None` falls back to `target_local`

        - [x] 1.1.3 Write unit test: `_sync_entry` with a local entry whose `workspace_path` does not exist on disk emits a warning to stderr and skips without writing files

        - [x] 1.1.4 Write property test: for any local entry with non-null `workspace_path`, the install target is always `Path(workspace_path) / ".kiro"` and never `target_local`

    - [x] 1.2 Implement the fix

        - [x] 1.2.1 Update `_sync_entry` in `src/ksm/commands/sync.py` to use `Path(entry.workspace_path) / ".kiro"` when `workspace_path` is set, validate the path exists, warn and skip if missing, fall back to `target_local` for legacy entries

    - [x] 1.3 Verify

        - [x] 1.3.1 Run all tests and confirm they pass with ≥95% coverage on the changed module

        - [x] 1.3.2 Run linting (black, flake8, mypy) on `src/ksm/commands/sync.py` and `tests/test_sync.py`
