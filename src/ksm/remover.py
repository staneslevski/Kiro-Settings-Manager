"""Bundle remover for ksm.

Deletes installed files based on manifest entries and updates
the manifest accordingly.
"""

from dataclasses import dataclass, field
from pathlib import Path

from ksm.manifest import Manifest, ManifestEntry


@dataclass
class RemovalResult:
    """Summary of a bundle removal operation."""

    removed_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)


def _cleanup_empty_dirs(start_dir: Path, boundary: Path) -> None:
    """Remove empty directories walking up from *start_dir*.

    Stops at (and never removes) *boundary* itself.  If *start_dir*
    does not exist the call is a no-op.
    """
    current = start_dir
    while current != boundary and current.is_dir():
        try:
            current.rmdir()  # only succeeds when empty
        except OSError:
            break
        current = current.parent


def remove_bundle(
    entry: ManifestEntry,
    target_dir: Path,
    manifest: Manifest,
) -> RemovalResult:
    """Delete installed files and remove the manifest entry.

    For each file in entry.installed_files:
      - If the file exists on disk, delete it.
      - If the file does not exist, record it as skipped.
    After all files are processed, empty parent directories are
    cleaned up to the *target_dir* boundary, then the entry is
    removed from the manifest.
    """
    result = RemovalResult()

    for rel_path in entry.installed_files:
        full_path = target_dir / rel_path
        if full_path.exists():
            full_path.unlink()
            result.removed_files.append(rel_path)
            _cleanup_empty_dirs(full_path.parent, target_dir)
        else:
            result.skipped_files.append(rel_path)

    manifest.entries = [
        e
        for e in manifest.entries
        if not (e.bundle_name == entry.bundle_name and e.scope == entry.scope)
    ]

    return result
