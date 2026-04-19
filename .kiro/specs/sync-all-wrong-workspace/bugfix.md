# Bugfix: sync --all syncs local bundles to wrong workspace

GitHub Issue: #30

## Current Behavior (Defect)

- WHEN `ksm sync --all` is run AND the manifest contains local bundle entries with `workspace_path` values pointing to different workspaces THEN the system syncs ALL local entries to the current working directory's `.kiro/` instead of each entry's recorded `workspace_path`.

## Expected Behavior (Correct)

- WHEN `ksm sync --all` is run AND a local manifest entry has a non-null `workspace_path` THEN the system SHALL sync that entry to `Path(entry.workspace_path) / ".kiro"`.
- WHEN `ksm sync --all` is run AND a local manifest entry has `workspace_path = None` (legacy) THEN the system SHALL fall back to syncing to the current workspace's `.kiro/` directory.
- WHEN `ksm sync --all` is run AND a local manifest entry's `workspace_path` directory does not exist on disk THEN the system SHALL print a warning to stderr and skip that entry without error.
- WHEN `ksm sync` is run with named bundles THEN the same workspace-path-aware target resolution SHALL apply.

## Unchanged Behavior (Regression Prevention)

- WHEN a manifest entry has `scope == "global"` THEN the system SHALL CONTINUE TO sync to `~/.kiro/` regardless of `workspace_path`.
- WHEN `ksm sync` is run with `--yes` THEN the system SHALL CONTINUE TO skip the confirmation prompt.
- WHEN `ksm sync --all` is run THEN deduplication by `(bundle_name, scope, workspace_path)` SHALL CONTINUE TO work as implemented for issue #28.
- WHEN a bundle is not found in any registry during sync THEN the system SHALL CONTINUE TO print a warning and skip that entry.

## Root Cause

In `src/ksm/commands/sync.py`, `_sync_entry()` determines the target directory as:

```python
target_dir = target_global if entry.scope == "global" else target_local
```

The `target_local` parameter is always `Path.cwd() / ".kiro"` (set by `_dispatch_sync` in `cli.py`). For local entries belonging to other workspaces, the function should use `Path(entry.workspace_path) / ".kiro"` instead.

## Fix

In `_sync_entry`, replace the target directory logic with:

```python
if entry.scope == "global":
    target_dir = target_global
elif entry.workspace_path is not None:
    ws = Path(entry.workspace_path)
    if not ws.exists():
        # warn and skip
        return
    target_dir = ws / ".kiro"
else:
    target_dir = target_local
```
