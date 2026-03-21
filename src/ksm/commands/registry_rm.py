"""Registry rm command for ksm.

Handles `ksm registry remove <name>` — removes a named registry,
blocks removal of the default registry, and cleans its cache.

Requirements: 3.1, 3.2, 3.3, 3.4, 8.2, 8.3
"""

import argparse
import shutil
import sys
from pathlib import Path

from ksm.errors import format_error, format_warning
from ksm.registry import (
    RegistryEntry,
    RegistryIndex,
    save_registry_index,
)


def _find_registry(
    name: str,
    registry_index: RegistryIndex,
) -> RegistryEntry | None:
    """Find a registry entry by name."""
    for entry in registry_index.registries:
        if entry.name == name:
            return entry
    return None


def run_registry_rm(
    args: argparse.Namespace,
    *,
    registry_index: RegistryIndex,
    registry_index_path: Path,
) -> int:
    """Remove a named registry. Returns exit code."""
    name: str = args.registry_name

    match = _find_registry(name, registry_index)

    if match is None:
        registered = [e.name for e in registry_index.registries]
        print(
            format_error(
                f"Registry '{name}' not found.",
                f"Registered registries:"
                f" {', '.join(registered)}",
                "Run `ksm registry list`"
                " to see all registries.",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        return 1

    if match.is_default:
        print(
            format_error(
                "Cannot remove the default registry.",
                f"'{name}' is the built-in"
                " default registry.",
                "Only user-added registries"
                " can be removed.",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        return 1

    # Remove from index first
    registry_index.registries = [e for e in registry_index.registries if e.name != name]
    save_registry_index(registry_index, registry_index_path)

    # Clean cache directory (Req 3.1–3.3)
    cache_path = Path(match.local_path)
    if cache_path.exists():
        try:
            shutil.rmtree(cache_path)
            print(
                f"Removed registry '{name}'."
                f" Cache directory cleaned:"
                f" {cache_path}",
                file=sys.stderr,
            )
        except PermissionError:
            print(
                format_warning(
                    f"Could not remove cache"
                    f" directory: {cache_path}",
                    "Permission denied."
                    " The registry was removed"
                    " but the cache remains.",
                    stream=sys.stderr,
                ),
                file=sys.stderr,
            )
    else:
        print(
            f"Removed registry '{name}'." " Cache directory was already absent.",
            file=sys.stderr,
        )

    return 0
