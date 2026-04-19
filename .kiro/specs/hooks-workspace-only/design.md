# Design: Handle hooks as workspace-only during global install and sync

GitHub Issue: #29
Requirements: #[[file:.kiro/specs/hooks-workspace-only/requirements.md]]

## Overview

Hooks are a Kiro IDE feature that only works from the workspace-level `.kiro/hooks/` directory. This design adds scope-aware handling so that hooks are excluded from global installs, recorded as metadata in the manifest, and distributed to workspaces during sync.

## High-Level Design

### Constant: `WORKSPACE_ONLY_SUBDIRS`

A new module-level constant in `src/ksm/scanner.py`:

```python
WORKSPACE_ONLY_SUBDIRS: frozenset[str] = frozenset({"hooks"})
```

This makes the constraint data-driven. If future subdirectory types also become workspace-only, they can be added here without changing logic.

### Data Flow

```
ksm add <bundle> -g
  │
  ├─ run_add() detects scope == "global"
  │   ├─ Checks: --only hooks -g → reject (FR-2.1)
  │   ├─ Checks: --only hooks,steering -g → strip hooks, warn (FR-2.3)
  │   └─ Passes to install_bundle()
  │
  ├─ install_bundle() receives scope == "global"
  │   ├─ _resolve_subdirs() returns all matched subdirs
  │   ├─ Filters out WORKSPACE_ONLY_SUBDIRS from subdirs_to_copy
  │   ├─ Sets hooks_skipped = True if any were removed
  │   ├─ Copies remaining subdirs normally
  │   └─ Calls _update_manifest() with has_hooks=hooks_skipped
  │
  └─ run_add() prints hooks warning if install_bundle signals it

ksm sync / ksm sync --all
  │
  ├─ run_sync() iterates entries_to_sync
  │   ├─ For each entry: calls _sync_entry() (existing behaviour)
  │   └─ After regular sync: calls _sync_global_hooks()
  │
  └─ _sync_global_hooks()
      ├─ Finds global entries with has_hooks == True
      ├─ Resolves each bundle from registry
      ├─ Copies only hooks/ to target workspace(s)
      └─ Prints summary
```

## Detailed Design

### 1. Manifest Changes (`src/ksm/manifest.py`)

**FR-6.1, FR-6.2, FR-6.3**

Add `has_hooks: bool = False` to `ManifestEntry`:

```python
@dataclass
class ManifestEntry:
    bundle_name: str
    source_registry: str
    scope: str
    installed_files: list[str]
    installed_at: str
    updated_at: str
    version: str | None = None
    workspace_path: str | None = None
    has_hooks: bool = False  # NEW
```

Serialization (`_entry_to_dict`): include `"has_hooks": True` only when `entry.has_hooks is True`. This keeps existing manifests unchanged.

Deserialization (`_dict_to_entry`): read `data.get("has_hooks", False)`. Old manifests without the field default to `False`.

### 2. Scanner Changes (`src/ksm/scanner.py`)

Add the constant:

```python
WORKSPACE_ONLY_SUBDIRS: frozenset[str] = frozenset({"hooks"})
```

No other changes to scanner. The constant is imported by `installer.py`.

### 3. Installer Changes (`src/ksm/installer.py`)

**FR-1.1, FR-1.3**

Modify `install_bundle()` to filter workspace-only subdirs when `scope == "global"`:

```python
def install_bundle(
    bundle: ResolvedBundle,
    target_dir: Path,
    scope: str,
    subdirectory_filter: set[str] | None,
    dot_selection: DotSelection | None,
    manifest: Manifest,
    source_label: str,
    version: str | None = None,
) -> list[CopyResult]:
    if dot_selection is not None:
        return _install_dot_selection(...)

    subdirs_to_copy = _resolve_subdirs(bundle, subdirectory_filter)

    # Filter workspace-only subdirs for global scope
    hooks_skipped = False
    if scope == "global":
        filtered = [
            sd for sd in subdirs_to_copy
            if sd not in WORKSPACE_ONLY_SUBDIRS
        ]
        hooks_skipped = len(filtered) < len(subdirs_to_copy)
        subdirs_to_copy = filtered

    results: list[CopyResult] = []
    for subdir in subdirs_to_copy:
        src = bundle.path / subdir
        dst = target_dir / subdir
        tree_results = copy_tree(src, dst)
        results.extend(tree_results)

    rel_paths = [str(r.path.relative_to(target_dir)) for r in results]
    workspace_path = (
        str(target_dir.parent.resolve()) if scope == "local" else None
    )
    _update_manifest(
        manifest,
        bundle.name,
        source_label,
        scope,
        rel_paths,
        version=version,
        workspace_path=workspace_path,
        has_hooks=hooks_skipped,  # NEW parameter
    )
    return results
```

The return type stays `list[CopyResult]`. The caller (`run_add`) needs to know whether hooks were skipped to print the warning. Two options:

**Option A**: Return a richer type (e.g. `InstallResult` dataclass with `results` and `hooks_skipped`).
**Option B**: The caller checks the manifest entry's `has_hooks` field after `install_bundle` returns.

**Decision**: Option B. It avoids changing the return type and keeps the interface simple. After `install_bundle()` returns, `run_add()` reads the manifest entry to check `has_hooks`.

Modify `_update_manifest()` to accept and store `has_hooks`:

```python
def _update_manifest(
    manifest: Manifest,
    bundle_name: str,
    source_registry: str,
    scope: str,
    installed_files: list[str],
    version: str | None = None,
    workspace_path: str | None = None,
    has_hooks: bool = False,  # NEW
) -> None:
    ...
    if existing:
        entry = existing[0]
        entry.installed_files = installed_files
        entry.updated_at = now
        entry.source_registry = source_registry
        entry.version = version
        entry.workspace_path = workspace_path
        entry.has_hooks = has_hooks  # NEW
    else:
        manifest.entries.append(
            ManifestEntry(
                ...,
                has_hooks=has_hooks,  # NEW
            )
        )
```

**Dot notation + global scope (FR-2.1 edge case)**: `_install_dot_selection()` does not need changes because the rejection of `ksm add bundle.hooks.item -g` is handled upstream in `run_add()` before `install_bundle()` is called.

### 4. Add Command Changes (`src/ksm/commands/add.py`)

**FR-1.2, FR-2.1, FR-2.3**

#### 4a. Reject `--only hooks -g` (FR-2.1)

After scope is determined and before calling `install_bundle()`, add a check:

```python
# Reject hooks-only global install
if scope == "global" and subdirectory_filter is not None:
    if subdirectory_filter == {"hooks"}:
        print(
            format_error(
                "Hooks can only be installed at"
                " the workspace level.",
                "Hooks are loaded from .kiro/hooks/"
                " which is workspace-only.",
                "Use -l to install locally, or run"
                " `ksm sync` in a workspace.",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        return 1
```

#### 4b. Strip hooks from mixed `--only` filter (FR-2.3)

When `scope == "global"` and `subdirectory_filter` contains `"hooks"` along with other values, remove `"hooks"` from the filter and print the warning. This happens in the same block:

```python
if scope == "global" and subdirectory_filter is not None:
    if subdirectory_filter == {"hooks"}:
        # ... reject as above
    elif "hooks" in subdirectory_filter:
        subdirectory_filter = subdirectory_filter - {"hooks"}
        # Warning printed after install (see 4c)
```

#### 4c. Print hooks warning after install (FR-1.2)

After `install_bundle()` returns, check the manifest entry for `has_hooks`:

```python
if results:
    # ... existing success output ...

    # Check if hooks were skipped during global install
    if scope == "global":
        ws_path = None
        entries = find_entries(
            manifest, resolved.name, scope, ws_path
        )
        if entries and entries[0].has_hooks:
            print(
                format_warning(
                    f"{bundle_spec} contains hooks, but"
                    " hooks only work at the"
                    " workspace level.",
                    "Hooks were not installed"
                    " globally. Run `ksm sync`"
                    " in a workspace to install"
                    " hooks locally.",
                    stream=sys.stderr,
                ),
                file=sys.stderr,
            )
```

#### 4d. Dot notation hooks + global scope

When `dot_selection` is not None and `dot_selection.subdirectory == "hooks"` and `scope == "global"`, reject with the same error as FR-2.1. This check goes alongside the existing dot notation validation:

```python
if (
    dot_selection is not None
    and dot_selection.subdirectory == "hooks"
    and scope == "global"
):
    print(
        format_error(
            "Hooks can only be installed at"
            " the workspace level.",
            ...
        ),
        file=sys.stderr,
    )
    return 1
```

#### 4e. Ephemeral flow (`_handle_ephemeral`)

The same hooks-skipping logic applies. Since `install_bundle()` handles the filtering internally, `_handle_ephemeral` gets the behaviour for free. The warning message after install needs the same `has_hooks` check added.

### 5. Sync Command Changes (`src/ksm/commands/sync.py`)

**FR-4.1 through FR-4.6**

#### 5a. New function: `_sync_global_hooks()`

After the regular sync loop in `run_sync()`, call a new function that handles hook distribution:

```python
def _sync_global_hooks(
    *,
    registry_index: RegistryIndex,
    manifest: Manifest,
    target_workspaces: list[Path],
) -> list[CopyResult]:
    """Copy hooks from global bundles to workspace(s)."""
    global_with_hooks = [
        e for e in manifest.entries
        if e.scope == "global" and e.has_hooks
    ]

    all_results: list[CopyResult] = []
    for entry in global_with_hooks:
        result = resolve_bundle(entry.bundle_name, registry_index)
        if not result.matches:
            # Warn and skip (FR-4.6)
            print(format_warning(...), file=sys.stderr)
            continue
        resolved = result.matches[0]

        # Check bundle actually has hooks/ subdir
        hooks_src = resolved.path / "hooks"
        if not hooks_src.is_dir():
            continue

        for ws_dir in target_workspaces:
            if not ws_dir.exists():
                print(format_warning(...), file=sys.stderr)
                continue
            hooks_dst = ws_dir / ".kiro" / "hooks"
            results = copy_tree(hooks_src, hooks_dst)
            all_results.extend(results)

            if results:
                # Print summary per workspace
                check = success(SYM_CHECK, stream=sys.stderr)
                name = accent(
                    entry.bundle_name, stream=sys.stderr
                )
                print(
                    f"{check} Synced hooks from {name}"
                    f" → {ws_dir}/.kiro/hooks/",
                    file=sys.stderr,
                )
                print(
                    format_diff_summary(
                        results, stream=sys.stderr
                    ),
                    file=sys.stderr,
                )

    return all_results
```

#### 5b. Determine target workspaces

In `run_sync()`, after the regular sync loop:

- **`ksm sync` (no `--all`)**: target is `[target_local.parent]` (current workspace only).
- **`ksm sync --all`**: target is all unique workspace paths from local manifest entries, plus the current workspace.

```python
# Collect target workspaces for hook distribution
if sync_all:
    ws_paths: set[str] = set()
    for e in manifest.entries:
        if e.scope == "local" and e.workspace_path:
            ws_paths.add(e.workspace_path)
    # Also include current workspace
    ws_paths.add(str(target_local.parent.resolve()))
    target_workspaces = [Path(p) for p in sorted(ws_paths)]
else:
    target_workspaces = [target_local.parent]

_sync_global_hooks(
    registry_index=registry_index,
    manifest=manifest,
    target_workspaces=target_workspaces,
)
```

#### 5c. Global entry sync skips hooks

When `_sync_entry()` syncs a global entry, `install_bundle()` already filters out hooks for `scope == "global"` (from the installer changes in section 3). No additional change needed in `_sync_entry()`.

### 6. List Command Changes (`src/ksm/commands/ls.py`)

**FR-5.1**

In `_format_grouped()`, when `verbose` is True and the entry is global with `has_hooks`, append an indicator after the file list:

```python
if verbose:
    for f in sorted(row_entries[i].installed_files):
        lines.append(f"    {muted(f)}")
    if (
        row_entries[i].scope == "global"
        and row_entries[i].has_hooks
    ):
        lines.append(
            f"    {muted('[hooks: workspace-only]')}"
        )
```

Also update `_entry_to_dict()` in ls.py to include `has_hooks` in JSON output when True:

```python
def _entry_to_dict(entry: ManifestEntry) -> dict[str, object]:
    d: dict[str, object] = { ... }
    if entry.workspace_path is not None:
        d["workspace_path"] = entry.workspace_path
    if entry.has_hooks:
        d["has_hooks"] = True  # NEW
    return d
```

## Files Changed

| File | Change |
|------|--------|
| `src/ksm/scanner.py` | Add `WORKSPACE_ONLY_SUBDIRS` constant |
| `src/ksm/manifest.py` | Add `has_hooks` field to `ManifestEntry`, update serialization/deserialization |
| `src/ksm/installer.py` | Filter workspace-only subdirs for global scope, pass `has_hooks` to manifest |
| `src/ksm/commands/add.py` | Reject `--only hooks -g`, strip hooks from mixed filters, print warning, handle dot notation + hooks + global |
| `src/ksm/commands/sync.py` | Add `_sync_global_hooks()`, call it after regular sync loop |
| `src/ksm/commands/ls.py` | Show `[hooks: workspace-only]` indicator in verbose mode, include `has_hooks` in JSON |

## Correctness Properties

### CP-1: Hook exclusion from global installs

For any bundle B with hooks and scope "global": the set of installed files SHALL NOT contain any path starting with `hooks/`.

### CP-2: Non-hook subdirectories unaffected

For any bundle B installed globally: the set of installed files for non-hook subdirectories SHALL be identical to what would be installed without this feature.

### CP-3: Local install unchanged

For any bundle B installed locally (scope "local"): the set of installed files SHALL be identical to what would be installed without this feature, including hooks.

### CP-4: Manifest has_hooks accuracy

For any global manifest entry: `has_hooks` is True if and only if the bundle contained a `hooks/` subdirectory at install time.

### CP-5: Sync hook distribution idempotency

Running `ksm sync` twice in succession with no upstream changes SHALL produce identical workspace hook files (no duplicates, no changes on second run).

### CP-6: Backward compatibility

Manifests without `has_hooks` fields SHALL deserialize with `has_hooks = False` and function identically to pre-feature behaviour.

## Testing Strategy

Tests will be added to the existing test files following the project's test structure:

- `tests/test_installer.py` — test hook filtering in `install_bundle()` for global scope, verify local scope unchanged
- `tests/test_manifest.py` — test `has_hooks` serialization/deserialization, backward compatibility
- `tests/test_sync.py` — test `_sync_global_hooks()`, verify hooks distributed to correct workspaces
- `tests/test_add.py` — test `--only hooks -g` rejection, mixed filter stripping, warning output
- `tests/test_ls.py` — test `[hooks: workspace-only]` indicator in verbose output

Property-based tests using Hypothesis will validate CP-1 through CP-6.
