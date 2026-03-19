"""Registry index management for ksm.

Manages the persistent registry index (registries.json) that tracks
all registered bundle registries and their locations on disk.
"""

from dataclasses import dataclass
from pathlib import Path

from ksm.persistence import read_json, write_json


@dataclass
class RegistryEntry:
    """A single registry source."""

    name: str
    url: str | None  # None for Default_Registry
    local_path: str
    is_default: bool


@dataclass
class RegistryIndex:
    """Collection of all registered registries."""

    registries: list[RegistryEntry]


def _entry_to_dict(entry: RegistryEntry) -> dict:
    """Serialize a RegistryEntry to a dict."""
    return {
        "name": entry.name,
        "url": entry.url,
        "local_path": entry.local_path,
        "is_default": entry.is_default,
    }


def _dict_to_entry(data: dict) -> RegistryEntry:
    """Deserialize a dict to a RegistryEntry."""
    return RegistryEntry(
        name=data["name"],
        url=data["url"],
        local_path=data["local_path"],
        is_default=data["is_default"],
    )


def load_registry_index(
    path: Path,
    default_registry_path: Path | None = None,
) -> RegistryIndex:
    """Load the registry index from JSON.

    If the file does not exist and default_registry_path is provided,
    creates a new index with the default registry entry and persists it.
    If the file does not exist and no default path is given, raises
    FileNotFoundError.
    """
    try:
        data = read_json(path)
        assert isinstance(data, dict)
        entries = [_dict_to_entry(e) for e in data["registries"]]
        return RegistryIndex(registries=entries)
    except FileNotFoundError:
        if default_registry_path is None:
            raise
        # First run: create default index
        default_entry = RegistryEntry(
            name="default",
            url=None,
            local_path=str(default_registry_path),
            is_default=True,
        )
        index = RegistryIndex(registries=[default_entry])
        save_registry_index(index, path)
        return index


def save_registry_index(index: RegistryIndex, path: Path) -> None:
    """Write the registry index to JSON."""
    data = {"registries": [_entry_to_dict(e) for e in index.registries]}
    write_json(path, data)
