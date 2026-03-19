"""Tests for ksm.selector module."""

from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from ksm.manifest import ManifestEntry
from ksm.scanner import BundleInfo


def test_render_add_selector_alphabetical_with_prefix() -> None:
    """Render output shows bundles alphabetically with > prefix."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(name="zebra", path=Path("/z"), subdirectories=["skills"]),
        BundleInfo(name="alpha", path=Path("/a"), subdirectories=["hooks"]),
        BundleInfo(name="mid", path=Path("/m"), subdirectories=["steering"]),
    ]
    lines = render_add_selector(bundles, installed_names=set(), selected=0)

    # Should be sorted alphabetically
    assert "alpha" in lines[0]
    assert "mid" in lines[1]
    assert "zebra" in lines[2]
    # First item has > prefix
    assert lines[0].startswith(">")
    assert not lines[1].startswith(">")


def test_render_add_selector_installed_label() -> None:
    """[installed] label appears for installed bundles."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(name="aws", path=Path("/a"), subdirectories=["skills"]),
        BundleInfo(name="git", path=Path("/g"), subdirectories=["hooks"]),
    ]
    lines = render_add_selector(bundles, installed_names={"aws"}, selected=0)

    aws_line = [ln for ln in lines if "aws" in ln][0]
    git_line = [ln for ln in lines if "git" in ln][0]
    assert "[installed]" in aws_line
    assert "[installed]" not in git_line


def test_navigation_clamps_at_boundaries() -> None:
    """Arrow key navigation clamps at list boundaries."""
    from ksm.selector import clamp_index

    assert clamp_index(-1, 5) == 0
    assert clamp_index(5, 5) == 4
    assert clamp_index(0, 5) == 0
    assert clamp_index(4, 5) == 4
    assert clamp_index(2, 5) == 2


def test_process_key_enter_returns_selected() -> None:
    """Enter key returns the selected bundle name."""
    from ksm.selector import process_key

    bundles_sorted = ["alpha", "beta", "gamma"]
    action, idx = process_key(b"\r", 1, len(bundles_sorted))
    assert action == "select"
    assert idx == 1


def test_process_key_q_returns_none() -> None:
    """q key returns quit action."""
    from ksm.selector import process_key

    action, idx = process_key(b"q", 0, 3)
    assert action == "quit"


def test_process_key_escape_returns_none() -> None:
    """Escape key returns quit action."""
    from ksm.selector import process_key

    action, idx = process_key(b"\x1b", 0, 3)
    assert action == "quit"


def test_process_key_down_arrow() -> None:
    """Down arrow moves selection down."""
    from ksm.selector import process_key

    action, idx = process_key(b"\x1b[B", 0, 3)
    assert action == "navigate"
    assert idx == 1


def test_process_key_up_arrow() -> None:
    """Up arrow moves selection up."""
    from ksm.selector import process_key

    action, idx = process_key(b"\x1b[A", 1, 3)
    assert action == "navigate"
    assert idx == 0


def test_process_key_up_clamps_at_zero() -> None:
    """Up arrow at index 0 stays at 0."""
    from ksm.selector import process_key

    action, idx = process_key(b"\x1b[A", 0, 3)
    assert action == "navigate"
    assert idx == 0


def test_process_key_down_clamps_at_max() -> None:
    """Down arrow at last index stays at last."""
    from ksm.selector import process_key

    action, idx = process_key(b"\x1b[B", 2, 3)
    assert action == "navigate"
    assert idx == 2


def test_render_removal_selector_shows_scope_labels() -> None:
    """Removal selector shows scope labels next to bundles."""
    from ksm.selector import render_removal_selector

    entries = [
        ManifestEntry(
            bundle_name="aws",
            source_registry="default",
            scope="global",
            installed_files=[],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        ),
        ManifestEntry(
            bundle_name="git",
            source_registry="default",
            scope="local",
            installed_files=[],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        ),
    ]
    lines = render_removal_selector(entries, selected=0)

    aws_line = [ln for ln in lines if "aws" in ln][0]
    git_line = [ln for ln in lines if "git" in ln][0]
    assert "[global]" in aws_line
    assert "[local]" in git_line
    # Alphabetical order
    assert lines[0].startswith(">")
    assert "aws" in lines[0]


# --- Property-based tests ---


# Property 5: Selector presents all bundles sorted
@given(
    names=st.lists(
        st.from_regex(r"[a-z]{1,10}", fullmatch=True),
        min_size=1,
        max_size=10,
        unique=True,
    ),
)
def test_property_selector_sorted_alphabetically(
    names: list[str],
) -> None:
    """Property 5: Selector presents all bundles sorted alphabetically."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(name=n, path=Path(f"/{n}"), subdirectories=["skills"]) for n in names
    ]
    lines = render_add_selector(bundles, installed_names=set(), selected=0)

    # Extract names from lines (strip > prefix and whitespace)
    rendered_names = []
    for line in lines:
        stripped = line.lstrip("> ").strip()
        # Name is the first word
        rendered_names.append(stripped.split()[0])

    assert rendered_names == sorted(names, key=str.lower)


# Feature: kiro-settings-manager, Property 6: Installed label accuracy
@given(
    names=st.lists(
        st.from_regex(r"[a-z]{1,10}", fullmatch=True),
        min_size=1,
        max_size=8,
        unique=True,
    ),
    data=st.data(),
)
def test_property_installed_label_accuracy(
    names: list[str],
    data: st.DataObject,
) -> None:
    """Property 6: [installed] label iff bundle is in installed set."""
    from ksm.selector import render_add_selector

    installed = set(
        data.draw(
            st.lists(st.sampled_from(names), unique=True, max_size=len(names)),
            label="installed",
        )
    )
    bundles = [
        BundleInfo(name=n, path=Path(f"/{n}"), subdirectories=["skills"]) for n in names
    ]
    lines = render_add_selector(bundles, installed_names=installed, selected=0)

    sorted_names = sorted(names, key=str.lower)
    for i, line in enumerate(lines):
        name = sorted_names[i]
        if name in installed:
            assert "[installed]" in line
        else:
            assert "[installed]" not in line


# Feature: kiro-settings-manager, Property 7: Arrow key navigation wraps correctly
@given(
    n=st.integers(min_value=1, max_value=50),
    current=st.integers(min_value=0, max_value=49),
)
def test_property_arrow_navigation_clamps(
    n: int,
    current: int,
) -> None:
    """Property 7: Arrow key navigation clamps at boundaries."""
    from ksm.selector import clamp_index

    current = min(current, n - 1)

    # Down: clamp at n-1
    down_result = clamp_index(current + 1, n)
    assert 0 <= down_result < n

    # Up: clamp at 0
    up_result = clamp_index(current - 1, n)
    assert 0 <= up_result < n


# Property 38: Removal selector — scope labels sorted alphabetically
@given(
    entries_data=st.lists(
        st.tuples(
            st.from_regex(r"[a-z]{1,10}", fullmatch=True),
            st.sampled_from(["local", "global"]),
        ),
        min_size=1,
        max_size=8,
        unique_by=lambda x: x[0],
    ),
)
def test_property_removal_selector_sorted_with_scope(
    entries_data: list[tuple[str, str]],
) -> None:
    """Property 38: Removal selector sorted alphabetically with scope."""
    from ksm.selector import render_removal_selector

    entries = [
        ManifestEntry(
            bundle_name=name,
            source_registry="default",
            scope=scope,
            installed_files=[],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        for name, scope in entries_data
    ]
    lines = render_removal_selector(entries, selected=0)

    expected_sorted = sorted(entries_data, key=lambda x: x[0].lower())
    for i, (name, scope) in enumerate(expected_sorted):
        assert name in lines[i]
        assert f"[{scope}]" in lines[i]
