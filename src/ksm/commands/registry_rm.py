"""Registry rm command for ksm.

Handles `ksm registry rm <name>` — removes a named registry,
blocks removal of the default registry, and cleans its cache.

Requirements: 8.2, 8.3
"""

import argparse
import shutil
import sys
from pathlib import Path

from ksm.registry import RegistryIndex, save_registry_index


def run_registry_rm(
    args: argparse.Namespace,
    *,
    registry_index: RegistryIndex,
    registry_index_path: Path,
) -> int:
    """Remove a named registry. Returns exit code."""
    name: str = args.registry_name

    # Find the registry entry
    match = None
    for entry in registry_index.registries:
        if entry.name == name:
            match = entry
            break

    if match is None:
        registered = [e.name for e in registry_index.registries]
        print(
            f"Error: registry '{name}' not found. "
            f"Registered: {', '.join(registered)}",
            file=sys.stderr,
        )
        return 1

    # Block removal of default registry
    if match.is_default:
        print(
            "Error: cannot remove the default registry.",
            file=sys.stderr,
        )
        return 1

    # Clean cache directory
    cache_path = Path(match.local_path)
    if cache_path.exists():
        shutil.rmtree(cache_path, ignore_errors=True)

    # Remove from index and save
    registry_index.registries = [
        e for e in registry_index.registries if e.name != name
    ]
    save_registry_index(registry_index, registry_index_path)

    print(
        f"Removed registry '{name}'.",
        file=sys.stderr,
    )
    return 0
