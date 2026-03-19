"""Tests for ksm.resolver module."""

from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings as h_settings
from hypothesis import strategies as st

from ksm.errors import BundleNotFoundError
from ksm.registry import RegistryEntry, RegistryIndex
from ksm.resolver import resolve_bundle


def _make_bundle(registry: Path, name: str, subdirs: list[str]) -> Path:
    """Helper to create a bundle directory with given subdirs."""
    bundle_dir = registry / name
    bundle_dir.mkdir(parents=True)
    for subdir in subdirs:
        (bundle_dir / subdir).mkdir()
        (bundle_dir / subdir / "placeholder.md").write_text("x")
    return bundle_dir


def test_resolve_bundle_found_in_default_registry(
    tmp_path: Path,
) -> None:
    """resolve_bundle finds a bundle in the default registry."""
    registry_path = tmp_path / "default_reg"
    _make_bundle(registry_path, "aws", ["skills", "steering"])

    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(registry_path),
                is_default=True,
            ),
        ]
    )

    result = resolve_bundle("aws", index)

    assert result.name == "aws"
    assert result.path == registry_path / "aws"
    assert result.registry_name == "default"
    assert "skills" in result.subdirectories
    assert "steering" in result.subdirectories


def test_resolve_bundle_found_in_custom_registry(
    tmp_path: Path,
) -> None:
    """resolve_bundle finds a bundle in a custom (non-default) registry."""
    default_path = tmp_path / "default_reg"
    default_path.mkdir()
    custom_path = tmp_path / "custom_reg"
    _make_bundle(custom_path, "team-tools", ["hooks", "agents"])

    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(default_path),
                is_default=True,
            ),
            RegistryEntry(
                name="team",
                url="https://github.com/org/repo.git",
                local_path=str(custom_path),
                is_default=False,
            ),
        ]
    )

    result = resolve_bundle("team-tools", index)

    assert result.name == "team-tools"
    assert result.path == custom_path / "team-tools"
    assert result.registry_name == "team"
    assert "hooks" in result.subdirectories
    assert "agents" in result.subdirectories


def test_resolve_bundle_not_found_raises(tmp_path: Path) -> None:
    """resolve_bundle raises BundleNotFoundError for unknown bundle."""
    registry_path = tmp_path / "default_reg"
    _make_bundle(registry_path, "aws", ["skills"])

    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(registry_path),
                is_default=True,
            ),
        ]
    )

    with pytest.raises(BundleNotFoundError) as exc_info:
        resolve_bundle("nonexistent", index)
    assert "nonexistent" in str(exc_info.value)


def test_resolve_bundle_prefers_first_registry(tmp_path: Path) -> None:
    """resolve_bundle returns the first match when multiple registries have it."""
    reg1 = tmp_path / "reg1"
    reg2 = tmp_path / "reg2"
    _make_bundle(reg1, "shared", ["skills"])
    _make_bundle(reg2, "shared", ["hooks"])

    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="first",
                url=None,
                local_path=str(reg1),
                is_default=True,
            ),
            RegistryEntry(
                name="second",
                url="https://example.com/repo.git",
                local_path=str(reg2),
                is_default=False,
            ),
        ]
    )

    result = resolve_bundle("shared", index)

    assert result.registry_name == "first"
    assert "skills" in result.subdirectories


def test_resolve_bundle_empty_registries() -> None:
    """resolve_bundle raises BundleNotFoundError with empty registry index."""
    index = RegistryIndex(registries=[])

    with pytest.raises(BundleNotFoundError):
        resolve_bundle("anything", index)


# --- Property-based tests ---


# Feature: kiro-settings-manager, Property 2: Unknown bundle produces error
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    bundle_name=st.from_regex(r"[a-zA-Z][a-zA-Z0-9_-]{0,19}", fullmatch=True),
)
def test_property_unknown_bundle_produces_error(
    tmp_path: Path,
    bundle_name: str,
) -> None:
    """Property 2: Unknown bundle name produces BundleNotFoundError."""
    # Create a registry with no bundles
    empty_reg = tmp_path / "empty_reg"
    empty_reg.mkdir(exist_ok=True)

    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(empty_reg),
                is_default=True,
            ),
        ]
    )

    with pytest.raises(BundleNotFoundError) as exc_info:
        resolve_bundle(bundle_name, index)
    assert bundle_name in str(exc_info.value)


def test_resolve_bundle_not_found_includes_searched_registries(
    tmp_path: Path,
) -> None:
    """resolve_bundle passes searched registry names to BundleNotFoundError."""
    reg1 = tmp_path / "reg1"
    reg1.mkdir()
    reg2 = tmp_path / "reg2"
    reg2.mkdir()

    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg1),
                is_default=True,
            ),
            RegistryEntry(
                name="my-custom",
                url="https://example.com/repo.git",
                local_path=str(reg2),
                is_default=False,
            ),
        ]
    )

    with pytest.raises(BundleNotFoundError) as exc_info:
        resolve_bundle("missing-bundle", index)

    err = exc_info.value
    assert err.searched_registries == ["default", "my-custom"]
    msg = str(err)
    assert "default" in msg
    assert "my-custom" in msg
    assert "missing-bundle" in msg
