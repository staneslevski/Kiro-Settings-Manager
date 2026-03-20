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
    bundle_dir.mkdir(parents=True, exist_ok=True)
    for subdir in subdirs:
        (bundle_dir / subdir).mkdir(exist_ok=True)
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

    assert len(result.matches) == 1
    match = result.matches[0]
    assert match.name == "aws"
    assert match.path == registry_path / "aws"
    assert match.registry_name == "default"
    assert "skills" in match.subdirectories
    assert "steering" in match.subdirectories


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

    assert len(result.matches) == 1
    match = result.matches[0]
    assert match.name == "team-tools"
    assert match.path == custom_path / "team-tools"
    assert match.registry_name == "team"
    assert "hooks" in match.subdirectories
    assert "agents" in match.subdirectories


def test_resolve_bundle_not_found_returns_empty(
    tmp_path: Path,
) -> None:
    """resolve_bundle returns empty matches for unknown bundle."""
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

    result = resolve_bundle("nonexistent", index)
    assert result.matches == []
    assert "default" in result.searched


def test_resolve_bundle_collects_all_registries(
    tmp_path: Path,
) -> None:
    """resolve_bundle returns matches from all registries."""
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

    assert len(result.matches) == 2
    assert result.matches[0].registry_name == "first"
    assert result.matches[1].registry_name == "second"


def test_resolve_bundle_empty_registries() -> None:
    """resolve_bundle returns empty result with empty registry index."""
    index = RegistryIndex(registries=[])

    result = resolve_bundle("anything", index)
    assert result.matches == []
    assert result.searched == []


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

    result = resolve_bundle(bundle_name, index)
    assert result.matches == []
    assert "default" in result.searched


def test_resolve_bundle_not_found_includes_searched_registries(
    tmp_path: Path,
) -> None:
    """resolve_bundle populates searched with all registry names."""
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

    result = resolve_bundle("missing-bundle", index)

    assert result.matches == []
    assert result.searched == ["default", "my-custom"]


# --- Phase 5: Multi-match resolver and qualified name parsing ---


def test_resolve_bundle_zero_matches_empty_result(
    tmp_path: Path,
) -> None:
    """resolve_bundle returns empty matches for unknown bundle."""
    reg = tmp_path / "reg"
    _make_bundle(reg, "other", ["skills"])

    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            ),
        ]
    )

    result = resolve_bundle("nonexistent", index)

    assert result.matches == []
    assert "default" in result.searched


def test_resolve_bundle_single_match_one_element(
    tmp_path: Path,
) -> None:
    """resolve_bundle returns one-element list for unique bundle."""
    reg = tmp_path / "reg"
    _make_bundle(reg, "aws", ["skills", "steering"])

    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            ),
        ]
    )

    result = resolve_bundle("aws", index)

    assert len(result.matches) == 1
    assert result.matches[0].name == "aws"
    assert result.matches[0].registry_name == "default"
    assert "skills" in result.matches[0].subdirectories


def test_resolve_bundle_multiple_matches_all_collected(
    tmp_path: Path,
) -> None:
    """resolve_bundle collects matches from all registries."""
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

    assert len(result.matches) == 2
    names = {m.registry_name for m in result.matches}
    assert names == {"first", "second"}
    assert result.searched == ["first", "second"]


def test_parse_qualified_name_with_slash() -> None:
    """parse_qualified_name splits registry/bundle correctly."""
    from ksm.resolver import parse_qualified_name

    reg, bundle = parse_qualified_name("my-reg/my-bundle")
    assert reg == "my-reg"
    assert bundle == "my-bundle"


def test_parse_qualified_name_plain() -> None:
    """parse_qualified_name returns None registry for plain name."""
    from ksm.resolver import parse_qualified_name

    reg, bundle = parse_qualified_name("my-bundle")
    assert reg is None
    assert bundle == "my-bundle"


def test_parse_qualified_name_leading_slash() -> None:
    """parse_qualified_name treats leading slash as plain name."""
    from ksm.resolver import parse_qualified_name

    reg, bundle = parse_qualified_name("/my-bundle")
    assert reg is None
    assert bundle == "/my-bundle"


def test_resolve_qualified_bundle_success(
    tmp_path: Path,
) -> None:
    """resolve_qualified_bundle finds bundle in named registry."""
    from ksm.resolver import resolve_qualified_bundle

    reg = tmp_path / "reg"
    _make_bundle(reg, "aws", ["skills"])

    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="my-reg",
                url="https://example.com/repo.git",
                local_path=str(reg),
                is_default=False,
            ),
        ]
    )

    result = resolve_qualified_bundle("my-reg/aws", index)
    assert result.name == "aws"
    assert result.registry_name == "my-reg"


def test_resolve_qualified_bundle_missing_registry(
    tmp_path: Path,
) -> None:
    """resolve_qualified_bundle errors when registry not found."""
    from ksm.resolver import resolve_qualified_bundle

    reg = tmp_path / "reg"
    reg.mkdir()

    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            ),
            RegistryEntry(
                name="team",
                url="https://example.com/repo.git",
                local_path=str(reg),
                is_default=False,
            ),
        ]
    )

    with pytest.raises(BundleNotFoundError) as exc_info:
        resolve_qualified_bundle("nonexistent/aws", index)

    msg = str(exc_info.value)
    assert "nonexistent" in msg
    # Should list available registries
    assert "default" in msg
    assert "team" in msg


def test_resolve_qualified_bundle_missing_bundle(
    tmp_path: Path,
) -> None:
    """resolve_qualified_bundle errors when bundle not in registry."""
    from ksm.resolver import resolve_qualified_bundle

    reg = tmp_path / "reg"
    _make_bundle(reg, "other", ["skills"])

    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="my-reg",
                url="https://example.com/repo.git",
                local_path=str(reg),
                is_default=False,
            ),
        ]
    )

    with pytest.raises(BundleNotFoundError) as exc_info:
        resolve_qualified_bundle("my-reg/missing", index)

    msg = str(exc_info.value)
    assert "missing" in msg


# Feature: ksm-enhancements, Property 8: Qualified name round-trip parsing
@given(
    registry_name=st.from_regex(r"[a-zA-Z][a-zA-Z0-9_-]{0,14}", fullmatch=True),
    bundle_name=st.from_regex(r"[a-zA-Z][a-zA-Z0-9_-]{0,14}", fullmatch=True),
)
def test_property_qualified_name_round_trip(
    registry_name: str,
    bundle_name: str,
) -> None:
    """Property 8: Qualified name round-trip parsing.

    For any valid registry name and bundle name (both non-empty,
    no '/'), parse_qualified_name(f"{reg}/{bundle}") returns
    (reg, bundle). For plain names, returns (None, name).
    """
    from ksm.resolver import parse_qualified_name

    # Qualified form round-trips correctly
    qualified = f"{registry_name}/{bundle_name}"
    reg, bun = parse_qualified_name(qualified)
    assert reg == registry_name
    assert bun == bundle_name

    # Plain form returns None registry
    plain_reg, plain_bun = parse_qualified_name(bundle_name)
    assert plain_reg is None
    assert plain_bun == bundle_name


# Feature: ksm-enhancements, Property 7: Ambiguous bundle resolution
# error lists all registries and suggests qualified syntax
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    data=st.data(),
    bundle_name=st.from_regex(r"[a-zA-Z][a-zA-Z0-9_-]{0,14}", fullmatch=True),
    reg_names=st.lists(
        st.from_regex(r"[a-zA-Z][a-zA-Z0-9_-]{0,9}", fullmatch=True),
        min_size=2,
        max_size=4,
        unique=True,
    ),
)
def test_property_ambiguous_resolution_lists_all(
    tmp_path: Path,
    data: st.DataObject,
    bundle_name: str,
    reg_names: list[str],
) -> None:
    """Property 7: Ambiguous bundle resolution returns all matches.

    For any bundle name present in 2+ registries, resolve_bundle
    returns a ResolvedBundleResult with len(matches) == number of
    registries containing that bundle, and searched contains all
    registry names.
    """
    iso = tmp_path / data.draw(st.uuids().map(str), label="isolation_id")
    iso.mkdir(parents=True, exist_ok=True)

    entries: list[RegistryEntry] = []
    for i, rname in enumerate(reg_names):
        reg_path = iso / f"reg_{i}"
        _make_bundle(reg_path, bundle_name, ["skills"])
        entries.append(
            RegistryEntry(
                name=rname,
                url=f"https://example.com/{rname}.git",
                local_path=str(reg_path),
                is_default=(i == 0),
            )
        )

    index = RegistryIndex(registries=entries)
    result = resolve_bundle(bundle_name, index)

    assert len(result.matches) == len(reg_names)
    match_regs = {m.registry_name for m in result.matches}
    assert match_regs == set(reg_names)
    assert set(result.searched) == set(reg_names)
