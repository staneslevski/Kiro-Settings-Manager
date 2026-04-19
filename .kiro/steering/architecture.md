---
inclusion: manual
---

# Repository Architecture

This document synthesises all design decisions from completed specs into a unified architecture reference for the `ksm` codebase.

## System Overview

`ksm` is a Python CLI tool for managing Kiro IDE configuration bundles. It installs, removes, syncs, and lists bundles of skills, steering files, hooks, and agents across workspace (`.kiro/`) and global (`~/.kiro/`) scopes. A single global manifest (`~/.kiro/ksm/manifest.json`) tracks all installations.

## Core Data Model

### ManifestEntry

The central data structure tracking installed bundles:

```
ManifestEntry:
  bundle_name: str
  source_registry: str
  scope: str              # "local" | "global"
  installed_files: list[str]
  installed_at: str
  updated_at: str
  version: str | None
  workspace_path: str | None   # Resolved absolute path for local entries
  has_hooks: bool              # True if bundle has hooks skipped during global install
```

Design decisions:
- `workspace_path` is set for local entries, None for global. This enables workspace-scoped filtering across all commands.
- `has_hooks` is serialized only when True, omitted otherwise, for backward compatibility with older manifests.
- Legacy entries (pre-workspace-path) have `workspace_path=None` and are handled via backfill.

### Manifest Lookup: `find_entries()`

Centralised workspace-aware lookup in `src/ksm/manifest.py`:
- Local scope with workspace_path: matches on `(bundle_name, scope, workspace_path)`.
- Global scope or None workspace_path: matches on `(bundle_name, scope)` only.

This function is used by the installer, remover, and command modules to ensure consistent matching semantics.

## Key Architectural Decisions

### Workspace-Only Subdirectories

Certain bundle subdirectory types only function at the workspace level. This is encoded as a data-driven constant:

```python
# src/ksm/scanner.py
WORKSPACE_ONLY_SUBDIRS: frozenset[str] = frozenset({"hooks"})
```

The installer filters these out during global installs. If future subdirectory types become workspace-only, they can be added to this set without changing logic.

### Hook Distribution via Sync

Since hooks cannot be installed globally, they are distributed to workspaces through `ksm sync`:
- `_sync_global_hooks()` in `src/ksm/commands/sync.py` finds global entries with `has_hooks=True`, resolves each bundle from the registry, and copies only the `hooks/` subdirectory to target workspaces.
- `ksm sync` targets the current workspace; `ksm sync --all` targets all tracked workspaces.

### Workspace-Path-Aware Sync Targeting

`_sync_entry()` resolves the target directory per entry:
1. Global entries → `~/.kiro/`
2. Local entries with `workspace_path` → `Path(workspace_path) / ".kiro"`
3. Legacy local entries (`workspace_path=None`) → current workspace `.kiro/` (fallback)
4. Missing workspace directory → warn and skip

### Sync Deduplication

`ksm sync --all` deduplicates entries by `(bundle_name, scope, workspace_path)` before syncing, keeping the first (oldest) entry per key. Named sync (`ksm sync <bundle>`) does not deduplicate.

### Legacy Entry Backfill

A `backfill_workspace_paths()` function in `src/ksm/manifest.py` runs on any manifest-aware command (add, rm, sync, list). It scans for local entries with `workspace_path=None`, checks if their `installed_files` exist under the current workspace's `.kiro/`, and backfills the workspace path if matched. This provides forward compatibility without requiring a manual migration step.

### Interactive Mode Installed Info

Interactive selectors (`ksm add -i`, `ksm init`, `ksm rm -i`) use `build_installed_info(manifest, workspace_path)` which returns `dict[str, set[str]]` mapping bundle names to scope sets (`{"local"}`, `{"global"}`, or both). This replaces the previous flat `set[str]` approach and enables scope-specific badges.

`format_installed_badge(scopes)` renders the badge text: `[installed: local]`, `[installed: global]`, or `[installed: local, global]`.

### Multi-Workspace Removal Safety

`remove_bundle()` in `src/ksm/remover.py` matches on `(bundle_name, scope, workspace_path)` for local entries, ensuring that removing a bundle from one workspace does not affect installations in other workspaces. Global and legacy entries fall back to `(bundle_name, scope)` matching.

## IDE-to-CLI Converter (`ksm ide2cli`)

### Module Structure

```
src/ksm/converters/
├── __init__.py
├── tool_map.py           # IDE → CLI tool name mapping
├── agent_converter.py    # Agent .md → .json conversion
└── hook_converter.py     # Hook .kiro.hook → CLI hook dict
```

### Tool Name Mapping

`TOOL_NAME_MAP` in `tool_map.py` defines one-to-many mappings from IDE simplified names to CLI canonical names. `UNCONVERTIBLE_TOOLS` (e.g. `spec`) are omitted with warnings. Unknown names pass through unchanged. Output is deduplicated.

### Agent Conversion Flow

1. Parse YAML frontmatter from `.md` file (name, description, tools)
2. Map tool names via `map_tools()`
3. Build JSON with `file://` URI prompt referencing the original markdown
4. Write `.json` alongside the source `.md`

### Hook Conversion Flow

1. Parse `.kiro.hook` JSON
2. Skip disabled hooks silently, `askAgent` hooks with warning, unconvertible events with warning
3. Map `when.type` through `EVENT_TYPE_MAP` to CLI event types
4. Map `when.toolTypes` through tool map for pre/postToolUse hooks
5. Produce CLI hook dict with `command` and optional `matcher`

### Scope

The command scans both workspace `.kiro/` and global `~/.kiro/` in a single pass. All output goes to stderr.

## Component Interaction Map

```
CLI (cli.py)
  ├── ksm add    → add.py → installer.py → manifest.py
  ├── ksm rm     → rm.py  → remover.py   → manifest.py
  ├── ksm sync   → sync.py → installer.py → manifest.py
  ├── ksm list   → ls.py  → manifest.py
  ├── ksm init   → init.py → installer.py → manifest.py
  └── ksm ide2cli → ide2cli.py → converters/

Shared:
  manifest.py    — ManifestEntry, find_entries(), build_installed_info(),
                   backfill_workspace_paths(), format_installed_badge()
  installer.py   — install_bundle(), _update_manifest()
  remover.py     — remove_bundle()
  scanner.py     — WORKSPACE_ONLY_SUBDIRS, RECOGNISED_SUBDIRS
  selector.py    — interactive_select(), render_add_selector()
  tui.py         — BundleSelectorApp, RemovalSelectorApp
  copier.py      — copy_tree()
```

## Technology Choices

- Python 3.13, single `pyproject.toml` for all config
- argparse for CLI parsing
- PyYAML for frontmatter parsing (agent converter)
- Hypothesis for property-based testing
- pytest with coverage for test execution
- black, flake8, mypy for code quality
