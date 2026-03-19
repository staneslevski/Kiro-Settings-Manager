"""Tests for ksm.persistence module."""

import json
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings as h_settings
from hypothesis import strategies as st

from ksm.persistence import ensure_ksm_dir, read_json, write_json


def test_ensure_ksm_dir_creates_directory(tmp_path: Path) -> None:
    """ensure_ksm_dir creates the ksm directory when it doesn't exist."""
    ksm_dir = tmp_path / ".kiro" / "ksm"
    ensure_ksm_dir(ksm_dir)
    assert ksm_dir.is_dir()


def test_ensure_ksm_dir_idempotent(tmp_path: Path) -> None:
    """ensure_ksm_dir is safe to call when directory already exists."""
    ksm_dir = tmp_path / ".kiro" / "ksm"
    ensure_ksm_dir(ksm_dir)
    ensure_ksm_dir(ksm_dir)
    assert ksm_dir.is_dir()


def test_write_json_read_json_round_trip(tmp_path: Path) -> None:
    """write_json then read_json returns equivalent data."""
    data = {"registries": [{"name": "default", "url": None}]}
    filepath = tmp_path / "test.json"
    write_json(filepath, data)
    assert read_json(filepath) == data


def test_write_json_read_json_list_round_trip(tmp_path: Path) -> None:
    """write_json/read_json works with list data."""
    data = [1, "two", {"three": 3}]
    filepath = tmp_path / "list.json"
    write_json(filepath, data)
    assert read_json(filepath) == data


def test_read_json_missing_file_raises(tmp_path: Path) -> None:
    """read_json raises FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        read_json(tmp_path / "nonexistent.json")


def test_write_json_creates_parent_dirs(tmp_path: Path) -> None:
    """write_json creates parent directories if they don't exist."""
    filepath = tmp_path / "nested" / "dir" / "data.json"
    data = {"key": "value"}
    write_json(filepath, data)
    assert read_json(filepath) == data


def test_write_json_produces_valid_json(tmp_path: Path) -> None:
    """write_json output is valid, human-readable JSON."""
    filepath = tmp_path / "check.json"
    data = {"a": 1, "b": [2, 3]}
    write_json(filepath, data)
    raw = filepath.read_text()
    assert json.loads(raw) == data
    # Should be indented for readability
    assert "\n" in raw


# --- Property-based tests ---

# Strategy for JSON-serialisable values (no NaN/Inf which break JSON)
json_primitives = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(),
)

json_values = st.recursive(
    json_primitives,
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(st.text(max_size=10), children, max_size=5),
    ),
    max_leaves=20,
)


# Feature: kiro-settings-manager, Property 15: Registry index JSON round-trip
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    data=st.fixed_dictionaries(
        {
            "registries": st.lists(
                st.fixed_dictionaries(
                    {
                        "name": st.text(min_size=1, max_size=20),
                        "url": st.one_of(st.none(), st.text(max_size=50)),
                        "local_path": st.text(min_size=1, max_size=50),
                        "is_default": st.booleans(),
                    }
                ),
                max_size=5,
            )
        }
    )
)
def test_property_registry_index_json_round_trip(tmp_path: Path, data: dict) -> None:
    """Property 15: Registry index round-trip through JSON."""
    filepath = tmp_path / "registry_rt.json"
    write_json(filepath, data)
    assert read_json(filepath) == data


# Feature: kiro-settings-manager, Property 16: Manifest JSON round-trip
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    data=st.fixed_dictionaries(
        {
            "entries": st.lists(
                st.fixed_dictionaries(
                    {
                        "bundle_name": st.text(min_size=1, max_size=20),
                        "source_registry": st.text(min_size=1, max_size=30),
                        "scope": st.sampled_from(["local", "global"]),
                        "installed_files": st.lists(
                            st.text(min_size=1, max_size=40),
                            max_size=10,
                        ),
                        "installed_at": st.text(min_size=1, max_size=30),
                        "updated_at": st.text(min_size=1, max_size=30),
                    }
                ),
                max_size=5,
            )
        }
    )
)
def test_property_manifest_json_round_trip(tmp_path: Path, data: dict) -> None:
    """Property 16: Manifest round-trip through JSON."""
    filepath = tmp_path / "manifest_rt.json"
    write_json(filepath, data)
    assert read_json(filepath) == data
