# Bugfix Requirements Document

## Introduction

When the same bundle is installed locally in two different workspaces, the manifest entry for the first workspace is overwritten by the second. This causes `ksm list --all` to show only the last workspace where the bundle was installed, and `ksm rm` to potentially target the wrong entry. The root cause is that `_update_manifest()` in `installer.py` and the lookup in `rm.py` use only `(bundle_name, scope)` as the key for local entries, ignoring `workspace_path`.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a bundle is installed locally in workspace A and then the same bundle is installed locally in workspace B THEN the system overwrites the manifest entry for workspace A with the workspace B entry, losing the workspace A record

1.2 WHEN `ksm list --all` is run after installing the same bundle locally in two workspaces THEN the system displays only the last workspace installation instead of both

1.3 WHEN `ksm rm <bundle> -l` is run from workspace A after the manifest entry was overwritten by a workspace B install THEN the system fails to find the entry for workspace A because it was replaced

### Expected Behavior (Correct)

2.1 WHEN a bundle is installed locally in workspace A and then the same bundle is installed locally in workspace B THEN the system SHALL create and maintain separate manifest entries for each workspace

2.2 WHEN `ksm list --all` is run after installing the same bundle locally in two workspaces THEN the system SHALL display both workspace entries

2.3 WHEN `ksm rm <bundle> -l` is run from a specific workspace THEN the system SHALL match the entry using both `bundle_name` and `workspace_path` for local-scoped entries, removing only the entry for the current workspace

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a bundle is installed at global scope THEN the system SHALL CONTINUE TO use `(bundle_name, scope)` as the lookup key since global entries have no workspace_path

3.2 WHEN the same bundle is re-installed locally in the same workspace THEN the system SHALL CONTINUE TO update the existing entry in place rather than creating a duplicate

3.3 WHEN `ksm list` is run without `--all` THEN the system SHALL CONTINUE TO filter local entries to only the current workspace

3.4 WHEN a global bundle is removed via `ksm rm <bundle> -g` THEN the system SHALL CONTINUE TO match by `(bundle_name, scope)` without considering workspace_path
