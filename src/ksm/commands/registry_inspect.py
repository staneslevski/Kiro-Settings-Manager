"""Registry inspect command for ksm.

Handles `ksm registry inspect <name>` — lists all bundles in
a registry with their subdirectory contents.

Requirements: 8.4, 8.5
"""

import argparse
import sys
from pathlib import Path

from ksm.color import bold, dim
from ksm.errors import format_error
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
            format_error(
                f"Registry '{name}' not found.",
                f"Registered: {', '.join(registered)}",
                "Run `ksm registry list` to see" " all registries.",
            ),
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
    lines.append(f"  URL:     {match.url or '(local)'}")
    lines.append(dim(f"  Path:    {match.local_path}"))
    lines.append(f"  Default: {'yes' if match.is_default else 'no'}")
    lines.append(f"  Bundles: {len(bundles)}")
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
