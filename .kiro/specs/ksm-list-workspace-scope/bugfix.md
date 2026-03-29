# Bugfix Requirements Document

## Introduction

`ksm list` displays locally installed bundles from all workspaces instead of only the current workspace. The root cause is that `ManifestEntry` records `scope="local"` but does not record which workspace the bundle was installed in. Since the manifest is global (`~/.kiro/ksm/manifest.json`), `run_ls()` has no way to distinguish local bundles belonging to the current workspace from those belonging to other workspaces. This causes confusion when working across multiple projects.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user runs `ksm list` (no flags) in workspace A THEN the system shows local bundles installed in workspace B alongside workspace A's local bundles, because the manifest has no workspace association for local entries.

1.2 WHEN a user runs `ksm list --scope local` in workspace A THEN the system shows all local bundles from every workspace, not just those installed in workspace A.

1.3 WHEN `install_bundle()` creates a manifest entry with `scope="local"` THEN the system does not record the workspace path in the `ManifestEntry`, making it impossible to filter by workspace later.

1.4 WHEN a user wants to see local bundles from all workspaces THEN the system provides no `--all` flag to explicitly request cross-workspace listing.

### Expected Behavior (Correct)

2.1 WHEN a user runs `ksm list` (no flags) in workspace A THEN the system SHALL show only global bundles and local bundles whose `workspace_path` matches the resolved path of workspace A.

2.2 WHEN a user runs `ksm list --scope local` in workspace A THEN the system SHALL show only local bundles whose `workspace_path` matches the resolved path of workspace A.

2.3 WHEN `install_bundle()` creates a manifest entry with `scope="local"` THEN the system SHALL record the resolved workspace path in the `ManifestEntry.workspace_path` field.

2.4 WHEN a user runs `ksm list --all` THEN the system SHALL show global bundles and local bundles from all workspaces, with workspace path information visible for local entries.

2.5 WHEN any `ksm` command runs within a workspace THEN the system SHALL check the manifest for legacy local entries (those with `scope="local"` but no `workspace_path` field) whose `installed_files` match files present in the current workspace's `.kiro/` directory, and SHALL automatically backfill the `workspace_path` field with the resolved path of the current workspace, persisting the updated manifest so that those entries become forward-compatible with workspace-filtered listing.

2.6 WHEN the manifest contains legacy local entries that cannot be matched to the current workspace (files not present in `.kiro/`) THEN the system SHALL leave them unchanged, include them in `--all` output, but exclude them from workspace-filtered output (default `ksm list`).

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user runs `ksm list` and only global bundles exist THEN the system SHALL CONTINUE TO display all global bundles exactly as before.

3.2 WHEN a user runs `ksm list --scope global` THEN the system SHALL CONTINUE TO show only global bundles, unaffected by the workspace filtering change.

3.3 WHEN a user runs `ksm list --format json` THEN the system SHALL CONTINUE TO output valid JSON with all required fields (`bundle_name`, `scope`, `source_registry`, `installed_files`, `installed_at`, `updated_at`), now additionally including `workspace_path` for local entries.

3.4 WHEN a user runs `ksm list -v` (verbose) THEN the system SHALL CONTINUE TO show installed file paths under each bundle entry.

3.5 WHEN a user installs a bundle with `scope="global"` THEN the system SHALL CONTINUE TO create a manifest entry without a `workspace_path` field.

3.6 WHEN a user runs `ksm list` with text output THEN the system SHALL CONTINUE TO group bundles by scope with bold headers, column alignment, and relative timestamps.
