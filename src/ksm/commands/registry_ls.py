"""Registry ls command for ksm.

Handles `ksm registry ls` — lists all registered registries
with name, URL, path, and bundle count.

Requirements: 8.1
"""

import argparse
import sys
from pathlib import Path

from ksm.color import bold, dim
from ksm.registry import RegistryIndex
from ksm.scanner import scan_registry


def run_registry_ls(
    args: argparse.Namespace,
    *,
    registry_index: RegistryIndex,
) -> int:
    """List all registered registries. Returns exit code."""
    if not registry_index.registries:
        print("No registries configured.", file=sys.stderr)
        return 0

    lines: list[str] = []
    for entry in registry_index.registries:
        registry_path = Path(entry.local_path)
        bundles = scan_registry(
            registry_path, registry_name=entry.name
        )
        bundle_count = len(bundles)

        name_str = bold(entry.name)
        url_str = entry.url if entry.url else dim("(local)")
        count_str = dim(f"{bundle_count} bundle{'s' if bundle_count != 1 else ''}")

        lines.append(f"  {name_str}")
        lines.append(f"    URL:     {url_str}")
        lines.append(f"    Path:    {entry.local_path}")
        lines.append(f"    Bundles: {count_str}")
        lines.append("")

    # Remove trailing blank line
    if lines and lines[-1] == "":
        lines.pop()

    print("\n".join(lines))
    return 0
