"""Ls command for ksm.

Handles `ksm ls` — lists all installed bundles from the manifest.
"""

import argparse

from ksm.manifest import Manifest


def run_ls(
    args: argparse.Namespace,
    *,
    manifest: Manifest,
) -> int:
    """Read manifest and print installed bundles. Returns exit code."""
    if not manifest.entries:
        print("No bundles currently installed.")
        return 0

    for entry in manifest.entries:
        print(
            f"{entry.bundle_name}  "
            f"[{entry.scope}]  "
            f"(source: {entry.source_registry})"
        )

    return 0
