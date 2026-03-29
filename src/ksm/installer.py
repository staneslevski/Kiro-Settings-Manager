"""Bundle installer for ksm.

Orchestrates file copying from a resolved bundle into the target
.kiro/ directory and updates the install manifest.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

from ksm.copier import CopyResult, copy_file, copy_tree
from ksm.dot_notation import DotSelection
from ksm.manifest import Manifest, ManifestEntry
from ksm.resolver import ResolvedBundle
from ksm.scanner import RECOGNISED_SUBDIRS


def install_bundle(
    bundle: ResolvedBundle,
    target_dir: Path,
    scope: str,
    subdirectory_filter: set[str] | None,
    dot_selection: DotSelection | None,
    manifest: Manifest,
    source_label: str,
    version: str | None = None,
) -> list[CopyResult]:
    """Install bundle files and update manifest.

    Returns list of CopyResult for all files processed.
    """
    if dot_selection is not None:
        return _install_dot_selection(
            bundle,
            target_dir,
            scope,
            dot_selection,
            manifest,
            source_label,
            version=version,
        )

    subdirs_to_copy = _resolve_subdirs(bundle, subdirectory_filter)
    results: list[CopyResult] = []

    for subdir in subdirs_to_copy:
        src = bundle.path / subdir
        dst = target_dir / subdir
        tree_results = copy_tree(src, dst)
        results.extend(tree_results)

    rel_paths = [str(r.path.relative_to(target_dir)) for r in results]
    workspace_path = str(target_dir.parent.resolve()) if scope == "local" else None
    _update_manifest(
        manifest,
        bundle.name,
        source_label,
        scope,
        rel_paths,
        version=version,
        workspace_path=workspace_path,
    )
    return results


def _install_dot_selection(
    bundle: ResolvedBundle,
    target_dir: Path,
    scope: str,
    dot_selection: DotSelection,
    manifest: Manifest,
    source_label: str,
    version: str | None = None,
) -> list[CopyResult]:
    """Install a single item via dot notation."""
    src_item = bundle.path / dot_selection.subdirectory / dot_selection.item_name
    dst_base = target_dir / dot_selection.subdirectory
    results: list[CopyResult] = []

    if src_item.is_dir():
        tree_results = copy_tree(src_item, dst_base / dot_selection.item_name)
        results.extend(tree_results)
    elif src_item.is_file():
        dst_file = dst_base / dot_selection.item_name
        result = copy_file(src_item, dst_file)
        results.append(result)

    rel_paths = [str(r.path.relative_to(target_dir)) for r in results]
    workspace_path = str(target_dir.parent.resolve()) if scope == "local" else None
    _update_manifest(
        manifest,
        bundle.name,
        source_label,
        scope,
        rel_paths,
        version=version,
        workspace_path=workspace_path,
    )
    return results


def _resolve_subdirs(
    bundle: ResolvedBundle,
    subdirectory_filter: set[str] | None,
) -> list[str]:
    """Determine which subdirectories to copy.

    Emits warnings for missing filtered subdirs.
    Exits if all filters miss.
    """
    available = set(bundle.subdirectories) & RECOGNISED_SUBDIRS

    if subdirectory_filter is None:
        return sorted(available)

    matched: list[str] = []
    for sd in sorted(subdirectory_filter):
        if sd in available:
            matched.append(sd)
        else:
            print(
                f"Warning: subdirectory '{sd}' not found " f"in bundle '{bundle.name}'",
                file=sys.stderr,
            )

    if not matched:
        print(
            f"Error: none of the specified subdirectories "
            f"exist in bundle '{bundle.name}'",
            file=sys.stderr,
        )
        raise SystemExit(1)

    return matched


def _update_manifest(
    manifest: Manifest,
    bundle_name: str,
    source_registry: str,
    scope: str,
    installed_files: list[str],
    version: str | None = None,
    workspace_path: str | None = None,
) -> None:
    """Add or update a manifest entry for the installed bundle."""
    now = datetime.now(timezone.utc).isoformat()

    existing = [
        e for e in manifest.entries if e.bundle_name == bundle_name and e.scope == scope
    ]

    if existing:
        entry = existing[0]
        entry.installed_files = installed_files
        entry.updated_at = now
        entry.source_registry = source_registry
        entry.version = version
        entry.workspace_path = workspace_path
    else:
        manifest.entries.append(
            ManifestEntry(
                bundle_name=bundle_name,
                source_registry=source_registry,
                scope=scope,
                installed_files=installed_files,
                installed_at=now,
                updated_at=now,
                version=version,
                workspace_path=workspace_path,
            )
        )
