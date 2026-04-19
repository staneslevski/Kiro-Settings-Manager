# Tasks: sync --all duplicate bundle fix

**Issue:** #28

- [x] 1. Deduplicate entries in sync --all

    - [x] 1.1 Add deduplication logic to run_sync

        - [x] 1.1.1 Write tests for sync --all deduplication in `tests/test_sync.py`
            - Test: duplicate manifest entries for same (bundle_name, scope, workspace_path) result in single sync
            - Test: distinct bundles across different workspaces are all synced
            - Test: entries with workspace_path=None are deduplicated separately from those with a path set (distinct keys, not collapsed)
            - Test: confirmation message count reflects deduplicated set, not raw entry count

        - [x] 1.1.2 Implement deduplication in `run_sync()` in `src/ksm/commands/sync.py`
            - When `sync_all` is True, deduplicate `entries_to_sync` by `(bundle_name, scope, workspace_path)` keeping first entry per key

        - [x] 1.1.3 Run tests and verify all pass

    - [x] 1.2 Regression guard for named sync

        - [x] 1.2.1 Write test: named sync (`ksm sync <bundle>`) with duplicate entries still syncs all of them (no dedup applied)

- [x] 2. Prevent duplicate manifest entries for legacy bundles

    - [x] 2.1 Add legacy entry matching to _update_manifest

        - [x] 2.1.1 Write tests for legacy entry matching in `tests/test_installer.py`
            - Test: _update_manifest with existing legacy entry (workspace_path=None) updates it in place when workspace_path is now provided
            - Test: _update_manifest with multiple legacy entries (workspace_path=None) upgrades only the first, leaves rest alone
            - Test: _update_manifest with no legacy entry and no matching entry creates a new entry (existing behavior preserved)
            - Test: _update_manifest with matching entry (workspace_path set) updates it (existing behavior preserved)

        - [x] 2.1.2 Implement legacy fallback in `_update_manifest()` in `src/ksm/installer.py`
            - After `find_entries()` returns empty, directly scan manifest.entries for legacy entries with same (bundle_name, scope) and workspace_path is None
            - If found, treat the first legacy entry as the existing entry to update
            - Add code comment explaining why first match is taken

        - [x] 2.1.3 Run tests and verify all pass

- [x] 3. Final verification

    - [x] 3.1 Full test suite and coverage

        - [x] 3.1.1 Run full test suite with coverage — 1147 passed, 98% coverage
        - [x] 3.1.2 Run linting (black, flake8, mypy) — all clean
        - [x] 3.1.3 Verify ≥95% coverage on modified files — sync.py 96%, installer.py 100%, manifest.py 100%
