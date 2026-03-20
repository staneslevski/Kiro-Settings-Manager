"""Registry inspect command for ksm.

Handles `ksm registry inspect <name>` — lists all bundles in
a registry with their subdirectory contents.

Requirements: 8.4, 8.5
"""

import argparse
import sys
from pathlib import Path

from ksm.color import bold, dim
from ksm.registry import RegistryIndex
from ksm.scanner import scan_registry


def run_registry_inspect(
    args: argparse.Namespace,
    *,
    registry_index: RegistryIndex,
) -> int:
    """Inspect a named registry. Returns exit code."""
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

    registry_path = Path(match.local_path)
    bundles = scan_registry(registry_path, registry_name=match.name)

    if not bundles:
        print(
            f"Registry '{name}' contains no bundles.",
            file=sys.stderr,
        )
        return 0

    lines: list[str] = []
    lines.append(bold(f"Registry: {name}"))
    lines.append(dim(f"  Path: {match.local_path}"))
    lines.append(f"  {len(bundles)} bundle" f"{'s' if len(bundles) != 1 else ''}:")
    lines.append("")

    for bundle in bundles:
        lines.append(f"  {bold(bundle.name)}")
        for subdir in bundle.subdirectories:
            # List items in each subdirectory
            subdir_path = bundle.path / subdir
            items = sorted(
                p.name for p in subdir_path.iterdir() if p.is_dir() or p.is_file()
            )
            lines.append(f"    {subdir}/ " f"{dim(f'({len(items)} items)')}")
            for item in items:
                lines.append(f"      {dim(item)}")
        lines.append("")

    # Remove trailing blank line
    if lines and lines[-1] == "":
        lines.pop()

    print("\n".join(lines))
    return 0
