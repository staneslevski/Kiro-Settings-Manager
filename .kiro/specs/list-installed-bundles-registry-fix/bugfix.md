# Bugfix Requirements Document

## Introduction

When a local-scoped bundle is installed in two different workspaces and then removed from one workspace, the `remove_bundle()` function in `src/ksm/remover.py` incorrectly removes ALL manifest entries matching the bundle name and scope, rather than only the entry for the target workspace. This causes `ksm list --all` to no longer show the bundle as installed anywhere, even though it remains installed in the other workspace.

The root cause is the manifest entry filter in `remove_bundle()` which matches on `bundle_name` and `scope` only, ignoring `workspace_path`. For local-scoped bundles installed in multiple workspaces, this removes entries for all workspaces instead of just the one being targeted.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a local-scoped bundle is installed in two workspaces and `remove_bundle()` is called for one workspace THEN the system removes ALL manifest entries matching that bundle name and scope, including entries for other workspaces

1.2 WHEN a local-scoped bundle is removed from workspace A and `ksm list --all` is run THEN the system does not show the bundle as installed in workspace B, even though it was never removed from workspace B

### Expected Behavior (Correct)

2.1 WHEN a local-scoped bundle is installed in two workspaces and `remove_bundle()` is called for one workspace THEN the system SHALL remove only the manifest entry whose `bundle_name`, `scope`, AND `workspace_path` all match the entry being removed

2.2 WHEN a local-scoped bundle is removed from workspace A and `ksm list --all` is run THEN the system SHALL continue to show the bundle as installed in workspace B

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a bundle is installed in only one workspace and `remove_bundle()` is called THEN the system SHALL CONTINUE TO remove the manifest entry and delete the installed files

3.2 WHEN a global-scoped bundle is removed THEN the system SHALL CONTINUE TO remove the manifest entry matching `bundle_name` and `scope` (global entries do not use `workspace_path`)

3.3 WHEN `remove_bundle()` is called THEN the system SHALL CONTINUE TO delete installed files from disk and clean up empty subdirectories

3.4 WHEN multiple different bundles are installed and one is removed THEN the system SHALL CONTINUE TO preserve all other bundle entries in the manifest
