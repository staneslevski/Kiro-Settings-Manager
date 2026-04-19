---
inclusion: manual
---

# Repository Requirements & Correctness Properties

This document synthesises all correctness properties and requirements from completed specs into a unified reference. It is the canonical source of truth for what the system SHALL and SHALL NOT do.

## 1. Manifest Data Model

- WHEN serializing a `ManifestEntry`, THE SYSTEM SHALL include `workspace_path` only when it is not None, and `has_hooks` only when it is True, to maintain backward compatibility.
- WHEN deserializing a `ManifestEntry` from JSON that lacks `workspace_path` or `has_hooks`, THE SYSTEM SHALL default them to `None` and `False` respectively.
- WHEN `install_bundle()` creates a manifest entry with `scope="local"`, THE SYSTEM SHALL record the resolved workspace path in `ManifestEntry.workspace_path`.
- WHEN `install_bundle()` creates a manifest entry with `scope="global"`, THE SYSTEM SHALL leave `workspace_path` as None.

## 2. Workspace-Scoped Manifest Lookups

- `find_entries(manifest, bundle_name, scope, workspace_path)` SHALL match on `(bundle_name, scope, workspace_path)` when scope is `"local"` and workspace_path is not None.
- `find_entries()` SHALL match on `(bundle_name, scope)` only when scope is `"global"` or workspace_path is None.
- WHEN `_update_manifest()` is called for a local install and `find_entries()` returns no match, THE SYSTEM SHALL fall back to matching a legacy entry with the same `(bundle_name, scope)` and `workspace_path=None`, updating it in place rather than creating a duplicate.

## 3. Bundle Installation — Hooks as Workspace-Only

- WHEN a user runs `ksm add <bundle> -g` AND the bundle contains a `hooks/` subdirectory, THE SYSTEM SHALL install all non-hook subdirectories to `~/.kiro/` but SHALL NOT copy `hooks/` globally.
- WHEN hooks are skipped during a global install, THE SYSTEM SHALL print a warning to stderr advising the user to run `ksm sync`.
- WHEN a bundle is installed globally and contains hooks, THE SYSTEM SHALL record `has_hooks: true` on the manifest entry.
- WHEN a user runs `ksm add <bundle> --only hooks -g`, THE SYSTEM SHALL reject the command with exit code 1.
- WHEN a user runs `ksm add <bundle> --only hooks,steering -g`, THE SYSTEM SHALL install only `steering/` globally, skip `hooks/`, and print the hooks warning.
- WHEN a user runs `ksm add <bundle> -l`, THE SYSTEM SHALL install all subdirectories including hooks with no change in behaviour.
- For any bundle installed globally: the set of installed files SHALL NOT contain any path starting with `hooks/`.
- For any bundle installed locally: the set of installed files SHALL be identical to what would be installed without the hooks-workspace-only feature.

## 4. Bundle Removal — Multi-Workspace Safety

- WHEN `remove_bundle()` is called for a local-scoped entry, THE SYSTEM SHALL remove only the manifest entry whose `bundle_name`, `scope`, AND `workspace_path` all match.
- WHEN `remove_bundle()` is called for a global-scoped entry, THE SYSTEM SHALL match on `bundle_name` and `scope` only.
- WHEN `remove_bundle()` is called for a legacy entry with `workspace_path=None`, THE SYSTEM SHALL fall back to matching on `bundle_name` and `scope` only.
- For any removal: all other bundle entries in the manifest SHALL be preserved.

## 5. Sync Command

### 5.1 Workspace-Path-Aware Targeting

- WHEN `ksm sync --all` is run AND a local manifest entry has a non-null `workspace_path`, THE SYSTEM SHALL sync that entry to `Path(entry.workspace_path) / ".kiro"`, not the current working directory.
- WHEN a local manifest entry has `workspace_path=None` (legacy), THE SYSTEM SHALL fall back to syncing to the current workspace's `.kiro/`.
- WHEN a local entry's `workspace_path` directory does not exist on disk, THE SYSTEM SHALL print a warning to stderr and skip that entry.

### 5.2 Hook Distribution via Sync

- WHEN `ksm sync` is run, THE SYSTEM SHALL identify globally-installed bundles with `has_hooks: true` and copy their `hooks/` subdirectory into the current workspace's `.kiro/hooks/`.
- WHEN `ksm sync --all` is run, THE SYSTEM SHALL copy hooks from global bundles into every workspace tracked in the manifest.
- Hook sync SHALL be idempotent — identical files are skipped.
- WHEN a global bundle with `has_hooks: true` is no longer found in any registry, THE SYSTEM SHALL warn and skip.

### 5.3 Deduplication

- WHEN `ksm sync --all` is run, THE SYSTEM SHALL deduplicate entries by `(bundle_name, scope, workspace_path)` before syncing.
- The confirmation message count SHALL reflect the deduplicated set.
- Named sync (`ksm sync <bundle>`) SHALL NOT deduplicate — all matching entries are synced.

## 6. List Command — Workspace Filtering

- WHEN `ksm list` is run (no `--all`), THE SYSTEM SHALL show only global bundles and local bundles whose `workspace_path` matches the current workspace.
- WHEN `ksm list --scope local` is run, THE SYSTEM SHALL show only local bundles matching the current workspace.
- WHEN `ksm list --all` is run, THE SYSTEM SHALL show all bundles from all workspaces, with workspace path annotations on local entries.
- WHEN `ksm list -v` is run AND a globally-installed bundle has `has_hooks: true`, THE SYSTEM SHALL display `[hooks: workspace-only]` alongside the entry.
- Legacy local entries with `workspace_path=None` SHALL be excluded from default output but included in `--all` output.

## 7. Interactive Mode — Workspace-Aware Installed Badges

- WHEN running `ksm add -i`, `ksm init`, or `ksm rm -i`, THE SYSTEM SHALL only show bundles as installed if they are globally installed or locally installed in the current workspace.
- Local entries from other workspaces SHALL NOT appear as installed in interactive mode.
- THE SYSTEM SHALL display scope-specific badges: `[installed: local]`, `[installed: global]`, or `[installed: local, global]`.
- WHEN running `ksm rm -i`, THE SYSTEM SHALL only list bundles that are globally installed or locally installed in the current workspace as removal candidates.

## 8. Legacy Entry Backfill

- WHEN any `ksm` command runs within a workspace, THE SYSTEM SHALL check for legacy local entries (`workspace_path=None`) whose `installed_files` match files in the current workspace's `.kiro/`, and SHALL backfill `workspace_path` with the resolved workspace path.
- Backfill SHALL NOT modify entries that already have `workspace_path` set.
- Backfill SHALL NOT modify global entries.
- WHEN backfill updates entries, THE SYSTEM SHALL persist the manifest.

## 9. IDE-to-CLI Conversion (`ksm ide2cli`)

### 9.1 Agent Conversion

- WHEN an agent markdown file is found in `agents/`, THE SYSTEM SHALL parse YAML frontmatter to extract `name`, `description`, and `tools`, and produce a CLI JSON file with a `file://` URI prompt referencing the original markdown.
- WHEN frontmatter is missing or invalid, THE SYSTEM SHALL print an error to stderr and skip the file.
- Agent conversion SHALL be idempotent — running twice on unchanged input produces byte-identical output.

### 9.2 Tool Name Mapping

- THE SYSTEM SHALL map IDE tool names to CLI equivalents: `read` → `[fs_read, grep, glob, code]`, `write` → `[fs_write]`, `shell` → `[execute_bash]`, `web` → `[web_search, web_fetch]`.
- `spec` SHALL be omitted with a warning (no CLI equivalent).
- Unknown tool names SHALL pass through unchanged.
- The CLI tools array SHALL be deduplicated.
- Tool map expansion SHALL be deterministic.

### 9.3 Hook Conversion

- WHEN a hook file has `then.type` of `runCommand`, THE SYSTEM SHALL convert it to CLI format.
- WHEN a hook file has `then.type` of `askAgent`, THE SYSTEM SHALL skip it with a warning.
- WHEN a hook file has an unconvertible event type (`fileEdited`, `fileCreated`, `fileDeleted`, `preTaskExecution`, `postTaskExecution`, `userTriggered`), THE SYSTEM SHALL skip it with a warning.
- WHEN a hook file has `enabled: false`, THE SYSTEM SHALL skip it silently.
- Event type mapping: `promptSubmit` → `userPromptSubmit`, `agentStop` → `stop`, `preToolUse` → `preToolUse`, `postToolUse` → `postToolUse`.

### 9.4 Output and Reporting

- All diagnostic output SHALL go to stderr; nothing to stdout.
- THE SYSTEM SHALL print a summary: converted count, skipped count (with reasons), failed count.
- Exit code 0 if at least one file converted or no convertible files found; exit code 1 if all fail or no `.kiro/` directories exist.
- THE SYSTEM SHALL scan both workspace `.kiro/` and global `~/.kiro/`.
