"""Install manifest management for ksm.

Manages the persistent install manifest (manifest.json) that tracks
which bundles are installed, their source, scope, and file paths.
"""

from dataclasses import dataclass
from pathlib import Path

from ksm.persistence import read_json, write_json


@dataclass
class ManifestEntry:
    """A single installed bundle record."""

    bundle_name: str
    source_registry: str
    scope: str  # "local" | "global"
    installed_files: list[str]
    installed_at: str  # ISO 8601 timestamp
    updated_at: str  # ISO 8601 timestamp


@dataclass
class Manifest:
    """Collection of all installed bundle records."""

    entries: list[ManifestEntry]


def _entry_to_dict(entry: ManifestEntry) -> dict:
    """Serialize a ManifestEntry to a dict."""
    return {
        "bundle_name": entry.bundle_name,
        "source_registry": entry.source_registry,
        "scope": entry.scope,
        "installed_files": entry.installed_files,
        "installed_at": entry.installed_at,
        "updated_at": entry.updated_at,
    }


def _dict_to_entry(data: dict) -> ManifestEntry:
    """Deserialize a dict to a ManifestEntry."""
    return ManifestEntry(
        bundle_name=data["bundle_name"],
        source_registry=data["source_registry"],
        scope=data["scope"],
        installed_files=data["installed_files"],
        installed_at=data["installed_at"],
        updated_at=data["updated_at"],
    )


def load_manifest(path: Path) -> Manifest:
    """Load the install manifest from JSON.

    Returns an empty manifest if the file does not exist.
    """
    try:
        data = read_json(path)
        assert isinstance(data, dict)
        entries = [_dict_to_entry(e) for e in data["entries"]]
        return Manifest(entries=entries)
    except FileNotFoundError:
        return Manifest(entries=[])


def save_manifest(manifest: Manifest, path: Path) -> None:
    """Write the install manifest to JSON."""
    data = {"entries": [_entry_to_dict(e) for e in manifest.entries]}
    write_json(path, data)
