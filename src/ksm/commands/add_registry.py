"""Add-registry command for ksm.

Handles `ksm add-registry <git_url>` — clones a git repository
and registers it as a bundle source.
"""

import argparse
import sys
from pathlib import Path
from posixpath import basename

from ksm.errors import GitError
from ksm.git_ops import clone_repo
from ksm.registry import (
    RegistryEntry,
    RegistryIndex,
    save_registry_index,
)
from ksm.scanner import scan_registry


def _derive_name(url: str) -> str:
    """Derive a registry name from a git URL."""
    name = basename(url.rstrip("/"))
    if name.endswith(".git"):
        name = name[:-4]
    return name


def run_add_registry(
    args: argparse.Namespace,
    *,
    registry_index: RegistryIndex,
    registry_index_path: Path,
    cache_dir: Path,
) -> int:
    """Clone a git repo and register it. Returns exit code."""
    git_url: str = args.git_url

    # Check for duplicate
    for entry in registry_index.registries:
        if entry.url == git_url:
            print(f"Registry already registered: {git_url}")
            return 0

    name = _derive_name(git_url)
    target = cache_dir / name

    try:
        clone_repo(git_url, target)
    except GitError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Scan for bundles (validates the repo has bundles)
    scan_registry(target)

    # Register
    registry_index.registries.append(
        RegistryEntry(
            name=name,
            url=git_url,
            local_path=str(target),
            is_default=False,
        )
    )
    save_registry_index(registry_index, registry_index_path)

    print(f"Registered registry '{name}' from {git_url}")
    return 0
