"""Registry add command for ksm.

Handles ``ksm registry add <git_url>`` — clones a git repository
and registers it as a bundle source.

Refactored from ``add_registry.py`` for the ``registry`` subcommand
group (Req 7).  Includes cache conflict handling (Req 1), duplicate
URL detection (Req 2), --force (Req 6), and --name (Req 11).
"""

import argparse
import shutil
import sys
from pathlib import Path
from posixpath import basename

from ksm.errors import (
    GitError,
    format_error,
)
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


def _find_entry_by_cache(
    cache_path: Path,
    registry_index: RegistryIndex,
) -> RegistryEntry | None:
    """Find a registry entry whose local_path matches."""
    for entry in registry_index.registries:
        if Path(entry.local_path) == cache_path:
            return entry
    return None


def run_registry_add(
    args: argparse.Namespace,
    *,
    registry_index: RegistryIndex,
    registry_index_path: Path,
    cache_dir: Path,
) -> int:
    """Clone a git repo and register it. Returns exit code."""
    git_url: str = args.git_url
    force: bool = getattr(args, "force", False)
    custom_name: str | None = getattr(args, "custom_name", None)

    # 1. Determine name (Req 11)
    name = custom_name if custom_name else _derive_name(git_url)

    # 2. Cache directory conflict detection (Req 1)
    #    Must happen before duplicate URL check so --force
    #    can handle same-URL re-add with existing cache.
    target = cache_dir / name
    if target.exists():
        existing = _find_entry_by_cache(target, registry_index)
        if existing and existing.url == git_url:
            # Same URL re-add (Req 1.1–1.3)
            if not force:
                print(
                    format_error(
                        f"Cache directory already exists:" f" {target}",
                        f"Registry '{name}' was previously" " cloned here.",
                        "Use `--force` to replace the" " existing cache.",
                    ),
                    file=sys.stderr,
                )
                return 1
        elif existing:
            # Different URL owns this cache dir (Req 1.4)
            print(
                format_error(
                    f"Cache directory name collision:" f" {target}",
                    f"Directory belongs to registry"
                    f" '{existing.name}'"
                    f" ({existing.url}).",
                    "Use `--name <custom-name>` to specify"
                    " a different cache directory name.",
                ),
                file=sys.stderr,
            )
            return 1

        # --force: remove existing cache (Req 1.5)
        if force:
            shutil.rmtree(target)

    # 3. Duplicate URL check (Req 2) — print existing name
    #    Only reached when cache conflict didn't trigger above.
    if not force:
        for entry in registry_index.registries:
            if entry.url == git_url:
                print(
                    format_error(
                        "Registry already registered as" f" '{entry.name}'.",
                        f"URL: {git_url}",
                        "Use `ksm registry list` to see" " registered registries.",
                    ),
                    file=sys.stderr,
                )
                return 0

    # 4. Name collision with existing registry (Req 11.4)
    if not force:
        for entry in registry_index.registries:
            if entry.name == name:
                print(
                    format_error(
                        f"Registry name '{name}' is" " already in use.",
                        f"Existing registry '{name}' has" f" URL: {entry.url}",
                        "Use `--name <custom-name>` to" " specify a different name.",
                    ),
                    file=sys.stderr,
                )
                return 1

    # 5. Clone (Req 1.7)
    try:
        clone_repo(git_url, target)
    except GitError as e:
        if force:
            # Rollback warning (Req 1.6)
            print(
                format_error(
                    f"Clone failed: {e}",
                    "The previous cache directory" " was removed.",
                    "Re-add the registry to restore:" " `ksm registry add <url>`",
                ),
                file=sys.stderr,
            )
        else:
            print(
                format_error(
                    "Clone failed",
                    str(e),
                    "Check the URL and try again.",
                ),
                file=sys.stderr,
            )
        return 1

    # 6. Scan for bundles
    scan_registry(target)

    # 7. Register — remove old entry if --force re-add
    if force:
        registry_index.registries = [
            e for e in registry_index.registries if e.name != name
        ]

    registry_index.registries.append(
        RegistryEntry(
            name=name,
            url=git_url,
            local_path=str(target),
            is_default=False,
        )
    )
    save_registry_index(registry_index, registry_index_path)

    print(
        f"Registered registry '{name}' from {git_url}",
        file=sys.stderr,
    )
    return 0
