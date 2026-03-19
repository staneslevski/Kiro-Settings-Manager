"""Sync command for ksm.

Handles `ksm sync <bundle_name> [<bundle_name> ...]` and
`ksm sync --all` with optional --yes to skip confirmation.
"""

import argparse
import sys
from pathlib import Path

from ksm.errors import BundleNotFoundError
from ksm.git_ops import pull_repo
from ksm.installer import install_bundle
from ksm.manifest import Manifest, ManifestEntry, save_manifest
from ksm.registry import RegistryIndex
from ksm.resolver import resolve_bundle


def run_sync(
    args: argparse.Namespace,
    *,
    registry_index: RegistryIndex,
    manifest: Manifest,
    manifest_path: Path,
    target_local: Path,
    target_global: Path,
) -> int:
    """Sync specified or all bundles. Returns exit code."""
    bundle_names: list[str] = getattr(args, "bundle_names", [])
    sync_all: bool = getattr(args, "all", False)
    skip_confirm: bool = getattr(args, "yes", False)

    if not bundle_names and not sync_all:
        print(
            "Error: specify bundle name(s) or use --all",
            file=sys.stderr,
        )
        return 1

    # Determine which bundles to sync
    if sync_all:
        entries_to_sync = list(manifest.entries)
    else:
        entries_to_sync = []
        for name in bundle_names:
            matches = [e for e in manifest.entries if e.bundle_name == name]
            if not matches:
                print(
                    f"Error: bundle '{name}' is not installed",
                    file=sys.stderr,
                )
                continue
            entries_to_sync.extend(matches)

    if not entries_to_sync:
        return 0

    # Confirmation prompt
    if not skip_confirm:
        try:
            response = input(
                "This will overwrite current configuration " "files. Continue? [y/n] "
            )
        except EOFError:
            response = "n"
        if response.strip() != "y":
            return 0

    # Pull latest for custom git registries
    _pull_custom_registries(registry_index)

    # Sync each bundle
    for entry in entries_to_sync:
        _sync_entry(
            entry,
            registry_index=registry_index,
            manifest=manifest,
            target_local=target_local,
            target_global=target_global,
        )

    save_manifest(manifest, manifest_path)
    return 0


def _pull_custom_registries(
    registry_index: RegistryIndex,
) -> None:
    """Pull latest changes for non-default git registries."""
    for reg in registry_index.registries:
        if not reg.is_default and reg.url is not None:
            try:
                pull_repo(Path(reg.local_path))
            except Exception as e:
                print(
                    f"Warning: failed to pull {reg.name}: {e}",
                    file=sys.stderr,
                )


def _sync_entry(
    entry: ManifestEntry,
    *,
    registry_index: RegistryIndex,
    manifest: Manifest,
    target_local: Path,
    target_global: Path,
) -> None:
    """Re-install a single bundle from its source registry."""
    target_dir = target_global if entry.scope == "global" else target_local

    try:
        resolved = resolve_bundle(entry.bundle_name, registry_index)
    except BundleNotFoundError as e:
        print(f"Warning: {e}", file=sys.stderr)
        return

    try:
        install_bundle(
            bundle=resolved,
            target_dir=target_dir,
            scope=entry.scope,
            subdirectory_filter=None,
            dot_selection=None,
            manifest=manifest,
            source_label=resolved.registry_name,
        )
    except SystemExit:
        print(
            f"Warning: failed to sync '{entry.bundle_name}'",
            file=sys.stderr,
        )
