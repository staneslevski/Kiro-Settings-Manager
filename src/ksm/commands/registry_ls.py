"""Registry ls command for ksm.

Handles `ksm registry ls` — lists all registered registries
with name, URL, path, and bundle count.

Requirements: 8.1
"""

import argparse
import sys
from pathlib import Path

from ksm.color import _align_columns, accent, muted
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

    rows: list[tuple[str, ...]] = []
    for entry in registry_index.registries:
        registry_path = Path(entry.local_path)
        bundles = scan_registry(registry_path, registry_name=entry.name)
        bundle_count = len(bundles)

        name_str = accent(entry.name)
        url_str = muted(entry.url if entry.url else "(local)")
        count_str = muted(f"{bundle_count} bundle{'s' if bundle_count != 1 else ''}")
        rows.append((name_str, url_str, count_str))

    aligned = _align_columns(rows)
    for line in aligned:
        print(f"  {line}")
    return 0
