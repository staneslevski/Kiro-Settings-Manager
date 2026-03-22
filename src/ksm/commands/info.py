"""Info command for ksm.

Handles `ksm info <bundle_name>` — displays bundle metadata,
subdirectory breakdown, and installed status.

Requirements: 18.1, 18.2, 18.3
"""

import argparse
import sys

from ksm.color import SYM_DOT, accent, muted, success
from ksm.errors import format_error
from ksm.manifest import Manifest
from ksm.registry import RegistryIndex
from ksm.resolver import resolve_bundle


def run_info(
    args: argparse.Namespace,
    *,
    registry_index: RegistryIndex,
    manifest: Manifest,
) -> int:
    """Display bundle metadata. Returns exit code."""
    bundle_name: str = args.bundle_name

    result = resolve_bundle(bundle_name, registry_index)
    if not result.matches:
        searched = ", ".join(result.searched) if result.searched else "none"
        print(
            format_error(
                f"Bundle '{bundle_name}' not found.",
                f"Searched: {searched}",
                "Run `ksm search <query>` to find" " available bundles.",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        return 1
    resolved = result.matches[0]

    # Check installed status
    installed_scopes = [
        e.scope for e in manifest.entries if e.bundle_name == bundle_name
    ]

    lines: list[str] = []
    lines.append(accent(resolved.name))
    lines.append(f"  Registry   {muted(resolved.registry_name)}")

    # Flattened contents
    content_parts: list[str] = []
    for subdir in resolved.subdirectories:
        subdir_path = resolved.path / subdir
        items = (
            sorted(p.name for p in subdir_path.iterdir())
            if subdir_path.is_dir()
            else []
        )
        content_parts.append(f"{subdir}/ {len(items)} items")
    contents_str = muted(f" {SYM_DOT} ".join(content_parts))
    lines.append(f"  Contents   {contents_str}")

    # Installed status
    if installed_scopes:
        scopes_str = ", ".join(installed_scopes)
        lines.append(f"  Installed  {success(scopes_str)}")
    else:
        lines.append(f"  Installed  {muted('no')}")

    print("\n".join(lines))
    return 0
