"""Search command for ksm.

Handles `ksm search <query>` — case-insensitive name search
across all registered registries.

Requirements: 19.1, 19.2, 19.3
"""

import argparse
import sys
from pathlib import Path

from ksm.color import _align_columns, accent, muted, subtle
from ksm.registry import RegistryIndex
from ksm.scanner import BundleInfo, scan_registry


def _matches(query: str, bundle: BundleInfo) -> bool:
    """Case-insensitive substring match on bundle name."""
    return query.lower() in bundle.name.lower()


def run_search(
    args: argparse.Namespace,
    *,
    registry_index: RegistryIndex,
) -> int:
    """Search for bundles by name. Returns exit code."""
    query: str = args.query

    results: list[tuple[str, BundleInfo]] = []
    for entry in registry_index.registries:
        registry_path = Path(entry.local_path)
        bundles = scan_registry(registry_path, registry_name=entry.name)
        for bundle in bundles:
            if _matches(query, bundle):
                results.append((entry.name, bundle))

    if not results:
        print(
            f"No bundles matching {accent(query)}.",
            file=sys.stderr,
        )
        print(
            subtle("Try a different search term or run"
                   " `ksm registry ls` to check registries."),
            file=sys.stderr,
        )
        return 0

    rows: list[tuple[str, ...]] = []
    for reg_name, bundle in results:
        subdirs = ", ".join(bundle.subdirectories)
        rows.append((accent(bundle.name), muted(reg_name), muted(subdirs)))

    aligned = _align_columns(rows)
    for line in aligned:
        print(f"  {line}")
    return 0
