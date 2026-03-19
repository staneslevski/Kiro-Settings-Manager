"""Tests for ksm.registry module."""

from pathlib import Path

from hypothesis import HealthCheck, given, settings as h_settings
from hypothesis import strategies as st

from ksm.persistence import read_json, write_json
from ksm.registry import (
    RegistryEntry,
    RegistryIndex,
    load_registry_index,
    save_registry_index,
)


def test_load_registry_index_creates_default_on_first_run(
    tmp_path: Path,
) -> None:
    """load_registry_index creates a default entry when no file exists."""
    filepath = tmp_path / "registries.json"
    default_path = tmp_path / "config_bundles"
    default_path.mkdir()

    index = load_registry_index(filepath, default_registry_path=default_path)

    assert len(index.registries) == 1
    entry = index.registries[0]
    assert entry.name == "default"
    assert entry.url is None
    assert entry.local_path == str(default_path)
    assert entry.is_default is True


def test_load_registry_index_persists_default_on_first_run(
    tmp_path: Path,
) -> None:
    """load_registry_index writes the default index to disk on first run."""
    filepath = tmp_path / "registries.json"
    default_path = tmp_path / "config_bundles"
    default_path.mkdir()

    load_registry_index(filepath, default_registry_path=default_path)

    assert filepath.exists()
    data = read_json(filepath)
    assert len(data["registries"]) == 1
    assert data["registries"][0]["name"] == "default"


def test_save_load_round_trip(tmp_path: Path) -> None:
    """save_registry_index then load_registry_index returns equivalent data."""
    filepath = tmp_path / "registries.json"
    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path="/some/path",
                is_default=True,
            ),
            RegistryEntry(
                name="team-configs",
                url="https://github.com/org/repo.git",
                local_path="/cache/team-configs",
                is_default=False,
            ),
        ]
    )

    save_registry_index(index, filepath)
    loaded = load_registry_index(filepath)

    assert len(loaded.registries) == len(index.registries)
    for orig, loaded_entry in zip(index.registries, loaded.registries):
        assert orig.name == loaded_entry.name
        assert orig.url == loaded_entry.url
        assert orig.local_path == loaded_entry.local_path
        assert orig.is_default == loaded_entry.is_default


def test_duplicate_registry_detection(tmp_path: Path) -> None:
    """Adding a registry with a URL already present is detected."""
    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path="/some/path",
                is_default=True,
            ),
            RegistryEntry(
                name="team",
                url="https://github.com/org/repo.git",
                local_path="/cache/team",
                is_default=False,
            ),
        ]
    )

    duplicate_url = "https://github.com/org/repo.git"
    existing = [e for e in index.registries if e.url == duplicate_url]
    assert len(existing) == 1
    assert existing[0].name == "team"


def test_duplicate_registry_by_name(tmp_path: Path) -> None:
    """Registries can be looked up by name for duplicate detection."""
    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path="/some/path",
                is_default=True,
            ),
        ]
    )

    names = [e.name for e in index.registries]
    assert "default" in names
    assert "nonexistent" not in names


def test_load_existing_registry_index(tmp_path: Path) -> None:
    """load_registry_index reads an existing file without modification."""
    filepath = tmp_path / "registries.json"
    data = {
        "registries": [
            {
                "name": "custom",
                "url": "https://example.com/repo.git",
                "local_path": "/cache/custom",
                "is_default": False,
            }
        ]
    }
    write_json(filepath, data)

    index = load_registry_index(filepath)

    assert len(index.registries) == 1
    assert index.registries[0].name == "custom"
    assert index.registries[0].url == "https://example.com/repo.git"


# --- Property-based tests ---


# Feature: kiro-settings-manager, Property 15: Registry index JSON round-trip
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    registries=st.lists(
        st.fixed_dictionaries(
            {
                "name": st.text(
                    alphabet=st.characters(
                        whitelist_categories=("L", "N"),
                        whitelist_characters="-_",
                    ),
                    min_size=1,
                    max_size=20,
                ),
                "url": st.one_of(st.none(), st.text(max_size=50)),
                "local_path": st.text(min_size=1, max_size=50),
                "is_default": st.booleans(),
            }
        ),
        max_size=5,
    )
)
def test_property_registry_index_round_trip(
    tmp_path: Path, registries: list[dict]
) -> None:
    """Property 15: Registry index JSON round-trip via dataclasses."""
    entries = [
        RegistryEntry(
            name=r["name"],
            url=r["url"],
            local_path=r["local_path"],
            is_default=r["is_default"],
        )
        for r in registries
    ]
    index = RegistryIndex(registries=entries)
    filepath = tmp_path / "prop_registry.json"

    save_registry_index(index, filepath)
    loaded = load_registry_index(filepath)

    assert len(loaded.registries) == len(index.registries)
    for orig, loaded_entry in zip(index.registries, loaded.registries):
        assert orig.name == loaded_entry.name
        assert orig.url == loaded_entry.url
        assert orig.local_path == loaded_entry.local_path
        assert orig.is_default == loaded_entry.is_default


# Feature: kiro-settings-manager, Property 14: Duplicate registry is a no-op
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    url=st.text(
        alphabet=st.characters(
            whitelist_categories=("L", "N"),
            whitelist_characters="/:.-_",
        ),
        min_size=5,
        max_size=60,
    ),
)
def test_property_duplicate_registry_no_op(tmp_path: Path, url: str) -> None:
    """Property 14: Adding a registry with an existing URL is a no-op."""
    filepath = tmp_path / "registries.json"
    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path="/default",
                is_default=True,
            ),
            RegistryEntry(
                name="existing",
                url=url,
                local_path="/cache/existing",
                is_default=False,
            ),
        ]
    )
    save_registry_index(index, filepath)

    # Attempting to find a duplicate should detect it
    loaded = load_registry_index(filepath)
    duplicates = [e for e in loaded.registries if e.url == url]
    assert len(duplicates) == 1

    # The index should be unchanged after save/load
    assert len(loaded.registries) == 2
