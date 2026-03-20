"""Init command for ksm.

Handles `ksm init` — creates the `.kiro/` directory in the
current working directory, prints a success message, and
optionally offers the interactive bundle selector on TTY.

Requirements: 17.1, 17.2, 17.3, 17.4
"""

import argparse
import sys
from pathlib import Path

from ksm.registry import RegistryIndex
from ksm.manifest import Manifest
from ksm.scanner import scan_registry
from ksm.selector import interactive_select


def run_init(
    args: argparse.Namespace,
    *,
    target_dir: Path,
    registry_index: RegistryIndex | None = None,
    manifest: Manifest | None = None,
) -> int:
    """Create .kiro/ directory and offer selector. Returns exit code."""
    kiro_dir = target_dir / ".kiro"

    if kiro_dir.exists():
        print(
            "Already initialised — .kiro/ exists.",
            file=sys.stderr,
        )
    else:
        kiro_dir.mkdir(parents=True)
        print(
            "Initialised .kiro/ directory.",
            file=sys.stderr,
        )

    # Offer interactive selector if TTY and registries available
    if sys.stdin.isatty() and registry_index is not None and manifest is not None:
        all_bundles = []
        for entry in registry_index.registries:
            registry_path = Path(entry.local_path)
            all_bundles.extend(scan_registry(registry_path))

        if all_bundles:
            installed = {e.bundle_name for e in manifest.entries}
            interactive_select(all_bundles, installed)

    return 0
