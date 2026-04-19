# Bugfix: sync --all syncs same bundle multiple times per workspace

**Issue:** #28

## Current Behavior (Defect)

- WHEN running `ksm sync --all` AND the manifest contains duplicate entries for the same `(bundle_name, scope, workspace_path)` combination THEN the system syncs the same bundle multiple times to the same workspace, producing redundant output and wasted work.

- WHEN running `ksm add <bundle> -l` in a workspace that already has a legacy manifest entry (with `workspace_path=None`) for the same bundle and scope THEN `_update_manifest()` calls `find_entries()` which does not match the legacy entry (because `workspace_path` is now set), so a duplicate entry is appended to the manifest.

## Expected Behavior (Correct)

- WHEN running `ksm sync --all` THEN the system SHALL deduplicate entries by `(bundle_name, scope, workspace_path)` before syncing, so each unique bundle+workspace combination is synced exactly once.

- WHEN running `ksm sync --all` THEN the confirmation message SHALL show the deduplicated count, not the raw manifest entry count.

- WHEN running `ksm add <bundle> -l` in a workspace that already has a legacy manifest entry (with `workspace_path=None`) for the same bundle and scope THEN `_update_manifest()` SHALL match the legacy entry and update it in place (setting `workspace_path`) rather than creating a duplicate.

## Unchanged Behavior (Regression Prevention)

- WHEN running `ksm sync --all` with distinct bundles across different workspaces THEN the system SHALL CONTINUE TO sync each distinct bundle+workspace combination independently.

- WHEN running `ksm sync --all` with a legacy entry (`workspace_path=None`) and a modern entry (`workspace_path="/some/path"`) for the same bundle THEN the system SHALL CONTINUE TO treat them as distinct entries (different dedup keys).

- WHEN running `ksm sync <bundle>` (named sync, not `--all`) THEN the system SHALL CONTINUE TO behave as it does today — syncing all matching manifest entries for the named bundle, including duplicates.

- WHEN running `ksm add <bundle> -l` in a workspace with no existing manifest entry THEN the system SHALL CONTINUE TO create a new entry with `workspace_path` set.

- WHEN running `ksm add <bundle> -g` (global scope) THEN the system SHALL CONTINUE TO match existing global entries by `(bundle_name, scope)` without workspace_path filtering.

## Note: No Retroactive Cleanup

This fix prevents new duplicates and deduplicates at sync time. It does NOT retroactively remove existing duplicate entries from the manifest file on disk. A manifest repair utility is out of scope for this fix.
