# Requirements: Handle hooks as workspace-only during global install and sync

GitHub Issue: #29

## Context

Kiro IDE only loads hooks from the workspace-level `.kiro/hooks/` directory. Hooks placed in the global `~/.kiro/hooks/` directory have no effect. Currently `ksm` treats all subdirectory types (agents, skills, steering, hooks) identically during install — it copies them to whichever target directory the scope dictates, with no awareness that hooks are workspace-only.

## Functional Requirements

### FR-1: Skip hooks during global install

- FR-1.1: WHEN a user runs `ksm add <bundle> -g` AND the bundle contains a `hooks/` subdirectory, THE SYSTEM SHALL install all non-hook subdirectories (agents, skills, steering) to `~/.kiro/` as normal BUT SHALL NOT copy the `hooks/` subdirectory to `~/.kiro/hooks/`.
- FR-1.2: WHEN hooks are skipped during a global install, THE SYSTEM SHALL print a warning to stderr explaining that hooks are workspace-only and were not installed, and advise the user to run `ksm sync` in a workspace.
- FR-1.3: WHEN a bundle is installed globally and contains hooks, THE SYSTEM SHALL record in the manifest entry that the bundle has hooks that were skipped (`has_hooks: true`).
- FR-1.4: WHEN a user runs `ksm add <bundle> -g` AND the bundle does NOT contain a `hooks/` subdirectory, THE SYSTEM SHALL CONTINUE TO install all subdirectories globally with no change in behaviour.

### FR-2: Reject `--only hooks -g`

- FR-2.1: WHEN a user runs `ksm add <bundle> --only hooks -g`, THE SYSTEM SHALL reject the command with exit code 1 and print an error to stderr explaining that hooks can only be installed at the workspace level.
- FR-2.2: WHEN a user runs `ksm add <bundle> --only hooks -l`, THE SYSTEM SHALL CONTINUE TO install hooks locally as normal (no change in behaviour).
- FR-2.3: WHEN a user runs `ksm add <bundle> --only hooks,steering -g`, THE SYSTEM SHALL install only `steering/` globally, skip `hooks/`, and print the hooks warning from FR-1.2.

### FR-3: Local install unchanged

- FR-3.1: WHEN a user runs `ksm add <bundle> -l` AND the bundle contains hooks, THE SYSTEM SHALL CONTINUE TO install all subdirectories including hooks to `<workspace>/.kiro/` with no change in behaviour.

### FR-4: Sync distributes hooks from global bundles to workspaces

- FR-4.1: WHEN a user runs `ksm sync` (no arguments, in a workspace) or `ksm sync --all`, THE SYSTEM SHALL identify all globally-installed bundles that have `has_hooks: true` in the manifest.
- FR-4.2: FOR EACH such global bundle with hooks, THE SYSTEM SHALL resolve the bundle from its source registry and copy only the `hooks/` subdirectory into the current workspace's `.kiro/hooks/` directory.
- FR-4.3: WHEN `ksm sync --all` is run, THE SYSTEM SHALL copy hooks from global bundles into every workspace tracked in the manifest (i.e. all workspaces that have local entries).
- FR-4.4: The hook sync SHALL be idempotent — if a hook file already exists and is identical, it SHALL be skipped (using existing skip-if-identical logic).
- FR-4.5: THE SYSTEM SHALL print a summary of which hooks were synced to which workspaces.
- FR-4.6: WHEN a global bundle with `has_hooks: true` is no longer found in any registry, THE SYSTEM SHALL print a warning and skip the hook sync for that bundle (same as existing sync behaviour for missing bundles).

### FR-5: List command indicates hook metadata

- FR-5.1: WHEN a user runs `ksm list -v` AND a globally-installed bundle has `has_hooks: true`, THE SYSTEM SHALL display an indicator (e.g. `[hooks: workspace-only]`) alongside the bundle entry to inform the user that hooks require workspace-level sync.

### FR-6: Manifest metadata

- FR-6.1: THE SYSTEM SHALL add an optional `has_hooks` boolean field to `ManifestEntry`.
- FR-6.2: WHEN serializing a manifest entry, THE SYSTEM SHALL include `has_hooks` in the JSON only when it is `True` (to maintain backward compatibility with existing manifests).
- FR-6.3: WHEN deserializing a manifest entry, THE SYSTEM SHALL default `has_hooks` to `False` if the field is absent (backward compatibility).

## Non-Functional Requirements

- NFR-1: All existing tests MUST continue to pass after the changes.
- NFR-2: New behaviour MUST have ≥95% test coverage.
- NFR-3: All code MUST pass black, flake8, and mypy linting.
- NFR-4: The warning and error messages MUST use the existing `format_warning` and `format_error` helpers for consistent formatting.
