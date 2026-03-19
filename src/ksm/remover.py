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


def remove_bundle(
    entry: ManifestEntry,
    target_dir: Path,
    manifest: Manifest,
) -> RemovalResult:
    """Delete installed files and remove the manifest entry.

    For each file in entry.installed_files:
      - If the file exists on disk, delete it.
      - If the file does not exist, record it as skipped.
    After all files are processed, remove the entry from the manifest.
    Empty subdirectories are left in place.
    """
    result = RemovalResult()

    for rel_path in entry.installed_files:
        full_path = target_dir / rel_path
        if full_path.exists():
            full_path.unlink()
            result.removed_files.append(rel_path)
        else:
            result.skipped_files.append(rel_path)

    manifest.entries = [
        e
        for e in manifest.entries
        if not (e.bundle_name == entry.bundle_name and e.scope == entry.scope)
    ]

    return result
