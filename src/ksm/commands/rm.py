"""Rm command for ksm.

Handles `ksm rm <bundle_name>` with flags -l, -g, --display.
"""

import argparse
import sys
from pathlib import Path

from ksm.manifest import Manifest, save_manifest
from ksm.remover import remove_bundle
from ksm.selector import interactive_removal_select


def run_rm(
    args: argparse.Namespace,
    *,
    manifest: Manifest,
    manifest_path: Path,
    target_local: Path,
    target_global: Path,
) -> int:
    """Execute the rm command. Returns exit code."""
    # Handle --display mode
    if getattr(args, "display", False):
        if not manifest.entries:
            print("No bundles currently installed.")
            return 0

        selected = interactive_removal_select(manifest.entries)
        if selected is None:
            return 0

        target_dir = target_global if selected.scope == "global" else target_local
        remove_bundle(selected, target_dir, manifest)
        save_manifest(manifest, manifest_path)
        return 0

    # Determine scope and target
    bundle_name: str | None = getattr(args, "bundle_name", None)
    if bundle_name is None:
        print("Error: no bundle specified", file=sys.stderr)
        return 1

    scope = "global" if getattr(args, "global_", False) else "local"
    target_dir = target_global if scope == "global" else target_local

    # Find matching manifest entry
    matches = [
        e for e in manifest.entries if e.bundle_name == bundle_name and e.scope == scope
    ]

    if not matches:
        print(
            f"Error: bundle '{bundle_name}' is not installed " f"at {scope} scope",
            file=sys.stderr,
        )
        return 1

    entry = matches[0]
    remove_bundle(entry, target_dir, manifest)
    save_manifest(manifest, manifest_path)
    return 0
