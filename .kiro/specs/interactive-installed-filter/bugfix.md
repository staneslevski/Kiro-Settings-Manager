# Bugfix Requirements Document

## Introduction

When running `ksm add -i`, `ksm rm -i`, or any interactive mode command, the "installed" badge is shown for bundles that are installed locally in a different workspace. Notably, `ksm list` already correctly filters by workspace — running `ksm list` from Workspace-B does not show bundles installed locally in Workspace-A. The bug is isolated to the interactive mode paths: `_handle_display()` in `add.py`, `run_init()` in `init.py`, and the interactive path in `rm.py` build the `installed_names` set from all manifest entries without filtering by workspace context. A bundle installed locally in Workspace-A appears as "installed" when browsing interactively from Workspace-B, which is incorrect. Additionally, the installed badge does not distinguish between local and global installations.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a bundle is installed locally in Workspace-A and the user runs `ksm add -i` from Workspace-B THEN the system shows the bundle as "[installed]" even though it is not installed in Workspace-B

1.2 WHEN a bundle is installed locally in Workspace-A and the user runs `ksm rm -i` from Workspace-B THEN the system shows the bundle as "[installed]" even though it is not installed in Workspace-B

1.3 WHEN a bundle is installed locally in Workspace-A and the user runs `ksm init` from Workspace-B (triggering the interactive selector) THEN the system shows the bundle as "[installed]" even though it is not installed in Workspace-B

1.4 WHEN a bundle is installed locally in Workspace-A and the user runs `ksm rm -i` from Workspace-B THEN the system lists the bundle as available for removal even though it is not installed in Workspace-B

1.5 WHEN a bundle is installed both locally and globally, and the user runs any interactive mode command THEN the system shows only a single "[installed]" badge with no indication of whether the installation is local, global, or both

### Expected Behavior (Correct)

2.1 WHEN a bundle is installed locally in Workspace-A and the user runs `ksm add -i` from Workspace-B THEN the system SHALL NOT show the bundle as installed, because the local installation in Workspace-A has no effect on Workspace-B

2.2 WHEN a bundle is installed locally in Workspace-A and the user runs `ksm rm -i` from Workspace-B THEN the system SHALL NOT show the bundle as installed, because the local installation in Workspace-A has no effect on Workspace-B

2.3 WHEN a bundle is installed locally in Workspace-A and the user runs `ksm init` from Workspace-B THEN the system SHALL NOT show the bundle as installed, because the local installation in Workspace-A has no effect on Workspace-B

2.4 WHEN a bundle is installed locally in the current workspace THEN the system SHALL show the bundle with an "[installed: local]" badge in interactive mode

2.5 WHEN a bundle is installed globally THEN the system SHALL show the bundle with an "[installed: global]" badge in interactive mode

2.6 WHEN a bundle is installed both locally in the current workspace and globally THEN the system SHALL show the bundle with an "[installed: local, global]" badge in interactive mode

2.7 WHEN the user runs `ksm rm -i` from Workspace-B THEN the system SHALL only list bundles that are either installed globally or installed locally in Workspace-B — bundles installed locally in other workspaces SHALL NOT appear as removal candidates

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a bundle is installed globally and the user runs `ksm add -i` from any workspace THEN the system SHALL CONTINUE TO show the bundle as installed (now with "[installed: global]" badge)

3.2 WHEN a bundle is installed locally in the current workspace and the user runs `ksm add -i` from that same workspace THEN the system SHALL CONTINUE TO show the bundle as installed (now with "[installed: local]" badge)

3.3 WHEN no bundles are installed and the user runs `ksm add -i` THEN the system SHALL CONTINUE TO show no installed badges on any bundle

3.4 WHEN the user runs non-interactive commands (`ksm add <bundle>`, `ksm rm <bundle>`) THEN the system SHALL CONTINUE TO behave identically to current behavior

3.5a WHEN the user runs `ksm list` THEN the system SHALL CONTINUE TO show global bundles and locally installed bundles for the current workspace only (this already works correctly and must not regress)

3.5b WHEN the user runs `ksm list --all` THEN the system SHALL CONTINUE TO show global bundles and all locally installed bundles across all workspaces, including a path to describe where each local bundle is installed (this already works correctly and must not regress)

3.6 WHEN the user runs `ksm rm -i` from a workspace THEN the system SHALL only show globally installed bundles and bundles installed locally in that specific workspace as removal candidates
