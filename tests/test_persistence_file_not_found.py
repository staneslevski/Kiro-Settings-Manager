"""Bug condition exploration tests for persistence FileNotFoundError.

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7

These tests confirm the bug exists on UNFIXED code and encode
the expected behavior that will pass once the fix is applied.
"""

from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings as h_settings
from hypothesis import strategies as st

from ksm.registry import (
    RegistryEntry,
    RegistryIndex,
    load_registry_index,
    save_registry_index,
)


def test_bug_condition_missing_file_no_default_raises(
    tmp_path: Path,
) -> None:
    """Bug Condition: load_registry_index without
    default_registry_path raises FileNotFoundError when
    registries.json does not exist.

    Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7

    This test CONFIRMS the bug exists on unfixed code.
    It should FAIL (raise FileNotFoundError) before the fix.
    """
    missing = tmp_path / "registries.json"
    assert not missing.exists()

    with pytest.raises(FileNotFoundError):
        load_registry_index(missing)


# Strategy: generate short safe directory names within tmp_path
_safe_dirname = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
        whitelist_characters="-_",
    ),
    min_size=1,
    max_size=20,
)


@h_settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(subdir=_safe_dirname)
def test_expected_behavior_with_default_registry_path(
    tmp_path: Path,
    subdir: str,
) -> None:
    """Expected Behavior: load_registry_index with
    default_registry_path auto-creates a RegistryIndex
    containing a default entry when registries.json is missing.

    Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7

    Property 1: Bug Condition — for any non-existent path,
    calling load_registry_index with a valid
    default_registry_path returns a RegistryIndex with
    exactly one default entry.
    """
    reg_file = tmp_path / subdir / "registries.json"
    default_dir = tmp_path / "config_bundles"
    default_dir.mkdir(exist_ok=True)

    assert not reg_file.exists()

    index = load_registry_index(reg_file, default_registry_path=default_dir)

    assert isinstance(index, RegistryIndex)
    assert len(index.registries) == 1

    entry = index.registries[0]
    assert entry.name == "default"
    assert entry.url is None
    assert entry.local_path == str(default_dir)
    assert entry.is_default is True
    assert reg_file.exists()


# ── Preservation property tests ──────────────────────────────
# Validates: Requirements 3.1, 3.3, 3.4

# Strategies for generating valid RegistryEntry / RegistryIndex

_non_empty_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P"),
        whitelist_characters="-_/ ",
    ),
    min_size=1,
    max_size=40,
)

_optional_url = st.one_of(st.none(), _non_empty_text)


@st.composite
def registry_entry_strategy(
    draw: st.DrawFn,
) -> RegistryEntry:
    """Generate a valid RegistryEntry."""
    return RegistryEntry(
        name=draw(_non_empty_text),
        url=draw(_optional_url),
        local_path=draw(_non_empty_text),
        is_default=draw(st.booleans()),
    )


@st.composite
def registry_index_strategy(
    draw: st.DrawFn,
) -> RegistryIndex:
    """Generate a valid RegistryIndex with 1-5 entries."""
    entries = draw(
        st.lists(
            registry_entry_strategy(),
            min_size=1,
            max_size=5,
        )
    )
    return RegistryIndex(registries=entries)


@h_settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    index=registry_index_strategy(),
    default_dir_name=_safe_dirname,
)
def test_preservation_round_trip(
    tmp_path: Path,
    index: RegistryIndex,
    default_dir_name: str,
) -> None:
    """For all valid RegistryIndex instances, save then load
    returns identical data — with and without
    default_registry_path.

    Validates: Requirements 3.1, 3.3, 3.4
    """
    reg_file = tmp_path / "registries.json"
    default_dir = tmp_path / default_dir_name
    default_dir.mkdir(parents=True, exist_ok=True)

    save_registry_index(index, reg_file)
    assert reg_file.exists()

    # Load without default_registry_path
    loaded = load_registry_index(reg_file)
    assert len(loaded.registries) == len(index.registries)
    for orig, got in zip(index.registries, loaded.registries):
        assert got.name == orig.name
        assert got.url == orig.url
        assert got.local_path == orig.local_path
        assert got.is_default == orig.is_default

    # Load with default_registry_path — same result
    loaded_with_default = load_registry_index(
        reg_file, default_registry_path=default_dir
    )
    assert len(loaded_with_default.registries) == len(index.registries)
    for orig, got in zip(index.registries, loaded_with_default.registries):
        assert got.name == orig.name
        assert got.url == orig.url
        assert got.local_path == orig.local_path
        assert got.is_default == orig.is_default


@h_settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    index=registry_index_strategy(),
    default_dir_name=_safe_dirname,
)
def test_preservation_default_registry_path_ignored_when_file_exists(
    tmp_path: Path,
    index: RegistryIndex,
    default_dir_name: str,
) -> None:
    """For all valid RegistryIndex instances, loading with and
    without default_registry_path returns identical results
    when the file exists.

    Validates: Requirements 3.1, 3.3, 3.4
    """
    reg_file = tmp_path / "registries.json"
    default_dir = tmp_path / default_dir_name
    default_dir.mkdir(parents=True, exist_ok=True)

    save_registry_index(index, reg_file)
    assert reg_file.exists()

    without_default = load_registry_index(reg_file)
    with_default = load_registry_index(reg_file, default_registry_path=default_dir)

    assert len(without_default.registries) == len(with_default.registries)
    for a, b in zip(without_default.registries, with_default.registries):
        assert a.name == b.name
        assert a.url == b.url
        assert a.local_path == b.local_path
        assert a.is_default == b.is_default
