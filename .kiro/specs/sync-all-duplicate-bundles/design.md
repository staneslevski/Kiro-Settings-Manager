# Design: sync --all duplicate bundle fix

**Issue:** #28

## Overview

Two targeted changes to fix duplicate syncing. No new files, no new commands — pure refactoring of existing logic.

## Change 1: Deduplicate entries in `sync --all` (src/ksm/commands/sync.py)

In `run_sync()`, when `sync_all` is True, deduplicate `entries_to_sync` by `(bundle_name, scope, workspace_path)` before iterating. Keep the first entry encountered for each unique key. The first entry is the oldest (entries are appended chronologically), so this preserves the original `installed_at` timestamp.

```python
if sync_all:
    seen: set[tuple[str, str, str | None]] = set()
    entries_to_sync = []
    for e in manifest.entries:
        key = (e.bundle_name, e.scope, e.workspace_path)
        if key not in seen:
            seen.add(key)
            entries_to_sync.append(e)
```

This deduplication happens before the confirmation prompt, so the confirmation message count reflects the actual number of syncs.

## Change 2: Match legacy entries in `_update_manifest()` (src/ksm/installer.py)

In `_update_manifest()`, after the initial `find_entries()` call returns no matches, perform a direct scan of manifest entries for legacy entries with the same `(bundle_name, scope)` where `workspace_path is None`. If found, update the first legacy entry in place rather than appending a duplicate.

```python
existing = find_entries(manifest, bundle_name, scope, workspace_path)

if not existing and scope == "local" and workspace_path is not None:
    # Fallback: match legacy entry with workspace_path=None.
    # This handles entries created before workspace_path tracking
    # was introduced. We take the first match because entries are
    # appended chronologically — the first is the original install.
    legacy_none = [
        e for e in manifest.entries
        if e.bundle_name == bundle_name
        and e.scope == scope
        and e.workspace_path is None
    ]
    if legacy_none:
        existing = [legacy_none[0]]
```

This is a single-pass filter over `manifest.entries`, avoiding the confusing indirection of calling `find_entries` with `None` (which returns ALL local entries, not just `None` ones).

## What is NOT changed

- `find_entries()` in `manifest.py` — its current behavior is correct for its general-purpose contract. The fallback logic belongs in the caller (`_update_manifest`), not in the shared lookup function.
- Named sync (`ksm sync <bundle>`) — no deduplication applied here; the user explicitly named the bundle and may intentionally have multiple entries.
- No new CLI commands or manifest repair utilities (out of scope for this fix).
- Existing duplicate entries on disk are not cleaned up. They are deduplicated at sync runtime only.

## Testing strategy

- Test `sync --all` with duplicate manifest entries → verify single sync per unique key
- Test `sync --all` confirmation message count reflects deduplicated set
- Test legacy entry (`workspace_path=None`) and modern entry for same bundle are NOT deduplicated (distinct keys)
- Test `_update_manifest` with a legacy entry (`workspace_path=None`) → verify it updates in place
- Test `_update_manifest` with multiple legacy entries → verify first is upgraded, rest left alone
- Test named sync (`ksm sync <bundle>`) with duplicates still syncs all (regression guard)
- All existing tests must continue to pass
