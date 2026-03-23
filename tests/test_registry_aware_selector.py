"""Tests for registry-aware interactive add selector.

Property-based and unit tests for the registry-aware two-column
layout in render_add_selector and qualified name returns from
interactive_select.
"""

import re
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

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
