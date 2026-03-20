"""Ls command for ksm.

Handles `ksm ls` — lists all installed bundles from the manifest.
"""

import argparse
import sys

from ksm.manifest import Manifest


def run_ls(
    args: argparse.Namespace,
    *,
    manifest: Manifest,
) -> int:
    """Read manifest and print installed bundles. Returns exit code."""
    if not manifest.entries:
        print("No bundles currently installed.", file=sys.stderr)
        return 0

    max_name = max(len(e.bundle_name) for e in manifest.entries)
    max_scope = max(len(e.scope) for e in manifest.entries)

    for entry in manifest.entries:
        name = entry.bundle_name.ljust(max_name)
        scope = entry.scope.ljust(max_scope)
        print(f"{name}  [{scope}]  " f"(source: {entry.source_registry})")

    return 0
