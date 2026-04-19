# Design: sync --all wrong workspace fix

## Overview

The fix is a single logic change in `_sync_entry()` in `src/ksm/commands/sync.py`. No new modules, no API changes, no data model changes.

## Change Detail

### `src/ksm/commands/sync.py` — `_sync_entry()`

Replace the current target directory resolution:

```python
target_dir = target_global if entry.scope == "global" else target_local
```

With workspace-path-aware resolution:

```python
if entry.scope == "global":
    target_dir = target_global
elif entry.workspace_path is not None:
    ws = Path(entry.workspace_path)
    if not ws.exists():
        print(
            format_warning(
                f"Workspace '{entry.workspace_path}' no longer exists.",
                f"Skipping sync for '{entry.bundle_name}'.",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        return
    target_dir = ws / ".kiro"
else:
    target_dir = target_local
```

### No changes to `src/ksm/cli.py`

`_dispatch_sync` continues to pass `target_local=cwd / ".kiro"`. This value is now only used as a fallback for legacy entries with `workspace_path=None`. No signature changes needed.

## Correctness Properties

1. **Workspace targeting**: For any local entry with a non-null `workspace_path`, the sync target directory MUST be `Path(entry.workspace_path) / ".kiro"`, never `target_local`.
2. **Legacy fallback**: For any local entry with `workspace_path=None`, the sync target directory MUST be `target_local`.
3. **Global unchanged**: For any global entry, the sync target directory MUST be `target_global`, regardless of `workspace_path`.
4. **Missing workspace safety**: If `entry.workspace_path` points to a non-existent directory, the entry MUST be skipped with a warning and no files written.
5. **Idempotency preserved**: Running sync twice with the same state produces the same result.

## Testing Strategy

Unit tests in `tests/test_sync.py` using the existing patterns (`_make_entry`, `_setup_bundle`, `_make_args`). Property-based tests with Hypothesis to verify correctness properties across varied inputs.
