"""Tests for registry-aware interactive add selector.

Property-based and unit tests for the registry-aware two-column
layout in render_add_selector and qualified name returns from
interactive_select.
"""

import re
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ksm.resolver import parse_qualified_name
from ksm.scanner import BundleInfo

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return _ANSI_RE.sub("", text)


# Hypothesis strategy: BundleInfo with non-empty registry_name
_bundle_info_st = st.builds(
    BundleInfo,
    name=st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True),
    path=st.builds(Path, st.just("/fake")),
    subdirectories=st.just(["skills"]),
    registry_name=st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True),
)


# Feature: registry-aware-interactive-add, Property 1:
# Display contains bundle name and registry name
@given(
    bundles=st.lists(
        _bundle_info_st,
        min_size=1,
        max_size=8,
    ),
)
def test_property_display_contains_bundle_and_registry_name(
    bundles: list[BundleInfo],
) -> None:
    """Property 1: Display contains bundle name and registry name.

    For any list of BundleInfo with non-empty registry_name,
    the rendered output contains both bundle.name and
    bundle.registry_name for each bundle.
    Validates: Requirements 1.1, 1.3
    """
    from ksm.selector import render_add_selector

    lines = render_add_selector(bundles, installed_names=set(), selected=0)
    full_output = _strip_ansi("\n".join(lines))

    for bundle in bundles:
        assert (
            bundle.name in full_output
        ), f"bundle name {bundle.name!r} missing from output"
        assert bundle.registry_name in full_output, (
            f"registry name {bundle.registry_name!r} missing "
            f"from output for bundle {bundle.name!r}"
        )


# Feature: registry-aware-interactive-add, Property 2:
# Installed detection uses bare name
@given(
    bundles=st.lists(
        _bundle_info_st,
        min_size=1,
        max_size=8,
        unique_by=lambda b: (b.name, b.registry_name),
    ),
    data=st.data(),
)
def test_property_installed_detection_uses_bare_name(
    bundles: list[BundleInfo],
    data: st.DataObject,
) -> None:
    """Property 2: Installed detection uses bare name.

    [installed] appears iff bundle.name is in installed_names,
    regardless of registry_name or display format.
    Validates: Requirements 1.4
    """
    from ksm.selector import render_add_selector

    all_names = list({b.name for b in bundles})
    installed = set(
        data.draw(
            st.lists(
                st.sampled_from(all_names),
                unique=True,
                max_size=len(all_names),
            ),
            label="installed",
        )
    )

    lines = render_add_selector(bundles, installed_names=installed, selected=0)
    bundle_lines = lines[3:]

    # Sort bundles the same way the selector does
    sorted_bundles = sorted(
        bundles, key=lambda b: (b.name.lower(), b.registry_name.lower())
    )

    for i, bundle in enumerate(sorted_bundles):
        line = bundle_lines[i]
        if bundle.name in installed:
            assert "[installed]" in line, (
                f"Expected [installed] for {bundle.name!r} "
                f"(registry={bundle.registry_name!r})"
            )
        else:
            assert "[installed]" not in line, (
                f"Unexpected [installed] for {bundle.name!r} "
                f"(registry={bundle.registry_name!r})"
            )


# Feature: registry-aware-interactive-add, Property 4:
# Duplicate bundle names produce separate items
@given(
    name=st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True),
    registries=st.lists(
        st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True),
        min_size=2,
        max_size=5,
        unique=True,
    ),
)
def test_property_duplicate_names_produce_separate_items(
    name: str,
    registries: list[str],
) -> None:
    """Property 4: Duplicate bundle names produce separate items.

    When the same bundle name appears with different registry_name
    values, the rendered output has one selectable line per
    BundleInfo (no deduplication).
    Validates: Requirements 4.1
    """
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(
            name=name,
            path=Path(f"/{reg}/{name}"),
            subdirectories=["skills"],
            registry_name=reg,
        )
        for reg in registries
    ]
    lines = render_add_selector(bundles, installed_names=set(), selected=0)
    bundle_lines = lines[3:]

    assert len(bundle_lines) == len(registries), (
        f"Expected {len(registries)} lines for {len(registries)} "
        f"registries, got {len(bundle_lines)}"
    )

    # Each registry name should appear in the output
    full_output = _strip_ansi("\n".join(bundle_lines))
    for reg in registries:
        assert reg in full_output, f"Registry {reg!r} missing from output"


# Strategy: BundleInfo with empty registry_name
_bundle_info_no_registry_st = st.builds(
    BundleInfo,
    name=st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True),
    path=st.builds(Path, st.just("/fake")),
    subdirectories=st.just(["skills"]),
    registry_name=st.just(""),
)


# Feature: registry-aware-interactive-add, Property 3:
# Qualified name round-trip
@given(
    registry_name=st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True),
    bundle_name=st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True),
)
def test_property_qualified_name_round_trip(
    registry_name: str,
    bundle_name: str,
) -> None:
    """Property 3: Qualified name round-trip.

    Building a qualified name as registry/bundle and parsing
    it with parse_qualified_name() returns the original pair.
    Validates: Requirements 2.1, 2.2, 2.4, 2.5, 1.5
    """
    qualified = f"{registry_name}/{bundle_name}"
    parsed_reg, parsed_name = parse_qualified_name(qualified)
    assert parsed_reg == registry_name, (
        f"Registry mismatch: expected {registry_name!r}, " f"got {parsed_reg!r}"
    )
    assert parsed_name == bundle_name, (
        f"Bundle name mismatch: expected {bundle_name!r}, " f"got {parsed_name!r}"
    )


@given(
    bundle_name=st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True),
)
def test_property_empty_registry_produces_bare_name(
    bundle_name: str,
) -> None:
    """Property 3 (empty case): Empty registry produces bare name.

    When registry_name is empty, the qualified name is the bare
    bundle_name with no leading '/'.
    Validates: Requirements 2.5, 1.5
    """
    # Build qualified name the way the selector should
    registry_name = ""
    if registry_name:
        qualified = f"{registry_name}/{bundle_name}"
    else:
        qualified = bundle_name

    assert "/" not in qualified, f"Bare name should not contain '/': {qualified!r}"
    parsed_reg, parsed_name = parse_qualified_name(qualified)
    assert parsed_reg is None, (
        f"Expected None registry for bare name, " f"got {parsed_reg!r}"
    )
    assert parsed_name == bundle_name, (
        f"Bundle name mismatch: expected {bundle_name!r}, " f"got {parsed_name!r}"
    )


# Feature: registry-aware-interactive-add, Property 5:
# Filter matches both bundle name and registry name
@given(
    bundles=st.lists(
        _bundle_info_st,
        min_size=1,
        max_size=8,
    ),
    filter_str=st.from_regex(r"[a-z0-9\-]{1,3}", fullmatch=True),
)
def test_property_filter_matches_both_fields(
    bundles: list[BundleInfo],
    filter_str: str,
) -> None:
    """Property 5: Filter matches both bundle name and registry name.

    For any filter string and list of BundleInfo objects, the
    filtered result set includes a bundle iff the filter string
    is a case-insensitive substring of either bundle.name or
    bundle.registry_name.
    **Validates: Requirements 5.1**
    """
    from ksm.selector import render_add_selector

    lines = render_add_selector(
        bundles,
        installed_names=set(),
        selected=0,
        filter_text=filter_str,
    )

    # First 3 lines are header, instructions, filter indicator
    bundle_lines = lines[3:]

    # Compute expected matches
    ft = filter_str.lower()
    expected = [
        b
        for b in sorted(
            bundles,
            key=lambda b: (b.name.lower(), b.registry_name.lower()),
        )
        if ft in b.name.lower() or ft in b.registry_name.lower()
    ]

    assert len(bundle_lines) == len(expected), (
        f"Expected {len(expected)} bundle lines for "
        f"filter {filter_str!r}, got {len(bundle_lines)}"
    )

    for i, bundle in enumerate(expected):
        stripped = _strip_ansi(bundle_lines[i])
        assert bundle.name in stripped, (
            f"Expected bundle name {bundle.name!r} in line " f"{i}: {stripped!r}"
        )


# Feature: registry-aware-interactive-add, Property 6:
# Qualified name resolves to correct registry
@given(
    bundle_name=st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True),
    registries=st.lists(
        st.from_regex(r"[a-z][a-z0-9\-]{0,9}", fullmatch=True),
        min_size=2,
        max_size=5,
        unique=True,
    ),
)
def test_property_qualified_name_resolves_to_correct_registry(
    bundle_name: str,
    registries: list[str],
) -> None:
    """Property 6: Qualified name resolves to correct registry.

    Build a RegistryIndex with duplicate bundles across registries.
    Call resolve_qualified_bundle(), assert returned registry_name
    matches input.
    Validates: Requirements 3.3, 4.2
    """
    import tempfile

    from ksm.registry import RegistryEntry, RegistryIndex
    from ksm.resolver import resolve_qualified_bundle

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        entries: list[RegistryEntry] = []
        for reg in registries:
            reg_dir = tmp_path / reg
            bundle_dir = reg_dir / bundle_name
            skills_dir = bundle_dir / "skills"
            skills_dir.mkdir(parents=True)
            entries.append(
                RegistryEntry(
                    name=reg,
                    url=None,
                    local_path=str(reg_dir),
                    is_default=False,
                )
            )

        index = RegistryIndex(registries=entries)

        for reg in registries:
            qualified = f"{reg}/{bundle_name}"
            resolved = resolve_qualified_bundle(qualified, index)
            assert resolved.registry_name == reg, (
                f"Expected registry {reg!r}, " f"got {resolved.registry_name!r}"
            )
            assert resolved.name == bundle_name, (
                f"Expected bundle {bundle_name!r}, " f"got {resolved.name!r}"
            )


# ------------------------------------------------------------------
# Unit tests for _handle_display pass-through (Task 4.1.2)
# ------------------------------------------------------------------


def test_handle_display_returns_qualified_name_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_handle_display returns the qualified name from
    interactive_select unchanged.
    Validates: Requirement 3.1
    """
    from ksm.commands.add import _handle_display
    from ksm.manifest import Manifest
    from ksm.registry import RegistryEntry, RegistryIndex

    qualified = "my-registry/my-bundle"

    monkeypatch.setattr(
        "ksm.commands.add.scan_registry",
        lambda path, registry_name="": [
            BundleInfo(
                name="my-bundle",
                path=Path("/fake/my-bundle"),
                subdirectories=["skills"],
                registry_name="my-registry",
            )
        ],
    )
    monkeypatch.setattr(
        "ksm.commands.add.interactive_select",
        lambda bundles, installed: [qualified],
    )

    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="my-registry",
                url=None,
                local_path="/fake",
                is_default=False,
            )
        ]
    )
    manifest = Manifest(entries=[])

    result = _handle_display(index, manifest)
    assert result == qualified, f"Expected {qualified!r}, got {result!r}"


def test_handle_display_cancellation_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_handle_display returns None when interactive_select
    returns None (user cancellation).
    Validates: Requirement 3.1
    """
    from ksm.commands.add import _handle_display
    from ksm.manifest import Manifest
    from ksm.registry import RegistryEntry, RegistryIndex

    monkeypatch.setattr(
        "ksm.commands.add.scan_registry",
        lambda path, registry_name="": [
            BundleInfo(
                name="b",
                path=Path("/fake/b"),
                subdirectories=["skills"],
                registry_name="r",
            )
        ],
    )
    monkeypatch.setattr(
        "ksm.commands.add.interactive_select",
        lambda bundles, installed: None,
    )

    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="r",
                url=None,
                local_path="/fake",
                is_default=False,
            )
        ]
    )
    manifest = Manifest(entries=[])

    result = _handle_display(index, manifest)
    assert result is None


# ------------------------------------------------------------------
# Unit tests for empty registry_name edge case (Task 4.1.3)
# ------------------------------------------------------------------


def test_empty_registry_display_shows_bare_name() -> None:
    """Display shows bare name when registry_name is empty.

    No registry column should appear, and no leading '/' in
    the output.
    Validates: Requirement 1.5
    """
    from ksm.selector import render_add_selector

    bundle = BundleInfo(
        name="my-bundle",
        path=Path("/fake/my-bundle"),
        subdirectories=["skills"],
        registry_name="",
    )
    lines = render_add_selector([bundle], installed_names=set(), selected=0)
    bundle_lines = lines[3:]
    assert len(bundle_lines) == 1
    stripped = _strip_ansi(bundle_lines[0])
    assert "my-bundle" in stripped
    # No leading '/' and no registry column
    assert "/" not in stripped


def test_empty_registry_return_is_bare_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """interactive_select returns bare name when registry_name
    is empty, with no leading '/'.
    Validates: Requirement 1.5
    """
    from ksm.selector import interactive_select

    bundle = BundleInfo(
        name="my-bundle",
        path=Path("/fake/my-bundle"),
        subdirectories=["skills"],
        registry_name="",
    )

    # Force fallback path (no Textual)
    monkeypatch.setattr("ksm.selector._can_run_textual", lambda: False)
    # Simulate user picking item 0
    monkeypatch.setattr(
        "ksm.selector._numbered_list_select",
        lambda items, header: 0,
    )

    result = interactive_select([bundle], installed_names=set())
    assert result is not None
    assert len(result) == 1
    assert result[0] == "my-bundle"
    assert "/" not in result[0]


def test_empty_registry_handle_display_returns_bare_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_handle_display returns bare name when registry_name
    is empty, with no leading '/'.
    Validates: Requirement 1.5
    """
    from ksm.commands.add import _handle_display
    from ksm.manifest import Manifest
    from ksm.registry import RegistryEntry, RegistryIndex

    monkeypatch.setattr(
        "ksm.commands.add.scan_registry",
        lambda path, registry_name="": [
            BundleInfo(
                name="my-bundle",
                path=Path("/fake/my-bundle"),
                subdirectories=["skills"],
                registry_name="",
            )
        ],
    )
    monkeypatch.setattr(
        "ksm.commands.add.interactive_select",
        lambda bundles, installed: ["my-bundle"],
    )

    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path="/fake",
                is_default=True,
            )
        ]
    )
    manifest = Manifest(entries=[])

    result = _handle_display(index, manifest)
    assert result == "my-bundle"
    assert "/" not in result


# ------------------------------------------------------------------
# Unit tests for backward compatibility (Task 5.1.1)
# ------------------------------------------------------------------


def test_run_add_bare_name_calls_resolve_bundle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """run_add() with a bare name (no '/') calls resolve_bundle().

    Validates: Requirement 6.1
    """
    import argparse
    from unittest.mock import MagicMock

    from ksm.commands.add import run_add
    from ksm.manifest import Manifest
    from ksm.registry import RegistryEntry, RegistryIndex
    from ksm.resolver import ResolvedBundle, ResolvedBundleResult

    resolved = ResolvedBundle(
        name="my-bundle",
        path=tmp_path / "reg" / "my-bundle",
        registry_name="default",
        subdirectories=["skills"],
    )
    result = ResolvedBundleResult(
        matches=[resolved],
        searched=["default"],
    )

    mock_resolve = MagicMock(return_value=result)
    mock_resolve_qualified = MagicMock()

    monkeypatch.setattr("ksm.commands.add.resolve_bundle", mock_resolve)
    monkeypatch.setattr(
        "ksm.commands.add.resolve_qualified_bundle",
        mock_resolve_qualified,
    )
    monkeypatch.setattr(
        "ksm.commands.add.install_bundle",
        MagicMock(return_value=[]),
    )
    monkeypatch.setattr("ksm.commands.add.save_manifest", MagicMock())

    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(tmp_path / "reg"),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(entries=[])
    manifest_path = tmp_path / "manifest.json"

    args = argparse.Namespace()
    args.bundle_spec = "my-bundle"
    args.display = False
    args.interactive = False
    setattr(args, "global_", False)
    args.local = True
    args.skills_only = False
    args.steering_only = False
    args.hooks_only = False
    args.agents_only = False
    args.from_url = None
    args.dry_run = False
    args.yes = False

    code = run_add(
        args,
        registry_index=index,
        manifest=manifest,
        manifest_path=manifest_path,
        target_local=tmp_path / ".kiro",
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    mock_resolve.assert_called_once_with("my-bundle", index)
    mock_resolve_qualified.assert_not_called()


def test_run_add_qualified_name_calls_resolve_qualified_bundle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """run_add() with registry/bundle calls resolve_qualified_bundle().

    Validates: Requirement 6.2
    """
    import argparse
    from unittest.mock import MagicMock

    from ksm.commands.add import run_add
    from ksm.manifest import Manifest
    from ksm.registry import RegistryEntry, RegistryIndex
    from ksm.resolver import ResolvedBundle

    resolved = ResolvedBundle(
        name="my-bundle",
        path=tmp_path / "reg" / "my-bundle",
        registry_name="my-registry",
        subdirectories=["skills"],
    )

    mock_resolve = MagicMock()
    mock_resolve_qualified = MagicMock(return_value=resolved)

    monkeypatch.setattr("ksm.commands.add.resolve_bundle", mock_resolve)
    monkeypatch.setattr(
        "ksm.commands.add.resolve_qualified_bundle",
        mock_resolve_qualified,
    )
    monkeypatch.setattr(
        "ksm.commands.add.install_bundle",
        MagicMock(return_value=[]),
    )
    monkeypatch.setattr("ksm.commands.add.save_manifest", MagicMock())

    index = RegistryIndex(
        registries=[
            RegistryEntry(
                name="my-registry",
                url=None,
                local_path=str(tmp_path / "reg"),
                is_default=False,
            )
        ]
    )
    manifest = Manifest(entries=[])
    manifest_path = tmp_path / "manifest.json"

    args = argparse.Namespace()
    args.bundle_spec = "my-registry/my-bundle"
    args.display = False
    args.interactive = False
    setattr(args, "global_", False)
    args.local = True
    args.skills_only = False
    args.steering_only = False
    args.hooks_only = False
    args.agents_only = False
    args.from_url = None
    args.dry_run = False
    args.yes = False

    code = run_add(
        args,
        registry_index=index,
        manifest=manifest,
        manifest_path=manifest_path,
        target_local=tmp_path / ".kiro",
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    mock_resolve_qualified.assert_called_once_with("my-registry/my-bundle", index)
    mock_resolve.assert_not_called()
