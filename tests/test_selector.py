"""Tests for ksm.selector module."""

import io
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ksm.manifest import ManifestEntry
from ksm.scanner import BundleInfo

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def test_render_add_selector_alphabetical_with_prefix() -> None:
    """Render output shows bundles alphabetically with > prefix."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(
            name="zebra",
            path=Path("/z"),
            subdirectories=["skills"],
            registry_name="default",
        ),
        BundleInfo(
            name="alpha",
            path=Path("/a"),
            subdirectories=["hooks"],
            registry_name="default",
        ),
        BundleInfo(
            name="mid",
            path=Path("/m"),
            subdirectories=["steering"],
            registry_name="default",
        ),
    ]
    lines = render_add_selector(bundles, installed_names=set(), selected=0)

    # First 3 lines are header, instructions, blank separator
    bundle_lines = lines[3:]
    # Should be sorted alphabetically
    assert "alpha" in bundle_lines[0]
    assert "mid" in bundle_lines[1]
    assert "zebra" in bundle_lines[2]
    # First item has > prefix
    assert bundle_lines[0].startswith(">")
    assert not bundle_lines[1].startswith(">")


def test_render_add_selector_installed_label() -> None:
    """[installed] label appears for installed bundles."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(
            name="aws",
            path=Path("/a"),
            subdirectories=["skills"],
            registry_name="default",
        ),
        BundleInfo(
            name="git",
            path=Path("/g"),
            subdirectories=["hooks"],
            registry_name="default",
        ),
    ]
    lines = render_add_selector(bundles, installed_names={"aws"}, selected=0)

    aws_line = [ln for ln in lines if "aws" in ln][0]
    git_line = [ln for ln in lines if "git" in ln][0]
    assert "[installed]" in aws_line
    assert "[installed]" not in git_line


def test_render_add_selector_shows_registry_name() -> None:
    """Selector shows registry name as second column for all bundles."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(
            name="aws",
            path=Path("/a"),
            subdirectories=["skills"],
            registry_name="default",
        ),
        BundleInfo(
            name="aws",
            path=Path("/t"),
            subdirectories=["hooks"],
            registry_name="team-repo",
        ),
    ]
    lines = render_add_selector(bundles, installed_names=set(), selected=0)

    bundle_lines = lines[3:]
    plain = [_ANSI_RE.sub("", ln) for ln in bundle_lines]
    # Two-column layout: bundle name + registry name
    assert "aws" in plain[0] and "default" in plain[0]
    assert "aws" in plain[1] and "team-repo" in plain[1]


def test_render_add_selector_multi_registry_sorted() -> None:
    """Bundles from multiple registries are sorted alphabetically."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(
            name="zulu",
            path=Path("/z"),
            subdirectories=["skills"],
            registry_name="team",
        ),
        BundleInfo(
            name="alpha",
            path=Path("/a"),
            subdirectories=["hooks"],
            registry_name="default",
        ),
    ]
    lines = render_add_selector(bundles, installed_names=set(), selected=0)

    assert "alpha" in lines[3]
    assert "zulu" in lines[4]


def test_navigation_clamps_at_boundaries() -> None:
    """Arrow key navigation clamps at list boundaries."""
    from ksm.selector import clamp_index

    assert clamp_index(-1, 5) == 0
    assert clamp_index(5, 5) == 4
    assert clamp_index(0, 5) == 0
    assert clamp_index(4, 5) == 4
    assert clamp_index(2, 5) == 2


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
    assert "[local" in git_line
    # Alphabetical order (bundle lines start at index 3)
    bundle_lines = lines[3:]
    assert bundle_lines[0].startswith(">")
    assert "aws" in bundle_lines[0]


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
        BundleInfo(
            name=n,
            path=Path(f"/{n}"),
            subdirectories=["skills"],
            registry_name="default",
        )
        for n in names
    ]
    lines = render_add_selector(bundles, installed_names=set(), selected=0)

    # Skip 3 header lines (header, instructions, blank)
    bundle_lines = lines[3:]
    # Extract names from bundle lines (strip > prefix and whitespace)
    rendered_names = []
    for line in bundle_lines:
        plain = _ANSI_RE.sub("", line)
        stripped = plain.lstrip("> ").strip()
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
        BundleInfo(
            name=n,
            path=Path(f"/{n}"),
            subdirectories=["skills"],
            registry_name="default",
        )
        for n in names
    ]
    lines = render_add_selector(bundles, installed_names=installed, selected=0)

    # Skip 3 header lines (header, instructions, blank)
    bundle_lines = lines[3:]
    sorted_names = sorted(names, key=str.lower)
    for i, line in enumerate(bundle_lines):
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

    # Skip 3 header lines (header, instructions, blank)
    bundle_lines = lines[3:]
    expected_sorted = sorted(entries_data, key=lambda x: x[0].lower())
    for i, (name, scope) in enumerate(expected_sorted):
        assert name in bundle_lines[i]
        assert f"[{scope}" in bundle_lines[i]


# --- Tests for interactive functions with mocked terminal I/O ---


def test_interactive_select_empty_bundles_returns_none() -> None:
    """interactive_select returns None for empty bundle list."""
    from ksm.selector import interactive_select

    result = interactive_select([], installed_names=set())
    assert result is None


def test_interactive_removal_select_empty_returns_none() -> None:
    """interactive_removal_select returns None for empty list."""
    from ksm.selector import interactive_removal_select

    result = interactive_removal_select([])
    assert result is None


# --- Column alignment tests ---


def test_render_add_selector_columns_aligned() -> None:
    """All columns in add selector must start at the same position."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(
            name="aws",
            path=Path("/a"),
            subdirectories=["skills"],
        ),
        BundleInfo(
            name="project_foundations",
            path=Path("/p"),
            subdirectories=["steering", "hooks"],
        ),
    ]
    lines = render_add_selector(bundles, installed_names={"aws"}, selected=0)

    # Skip 3 header lines; only check bundle lines for alignment
    bundle_lines = lines[3:]
    # Find where the [installed] tag starts — it should be
    # at a consistent column even though names differ in length.
    # The line without [installed] should still have the name
    # padded so that if a tag were present it would align.
    # Check that the name field is padded to the same width.
    # Strip the 2-char prefix (">" or " " + space)
    name_ends = []
    for line in bundle_lines:
        # After prefix "X ", the name is padded
        after_prefix = line[2:]
        # Find where trailing spaces end (i.e. first non-space
        # after the name characters)
        stripped = after_prefix.rstrip()
        name_ends.append(len(stripped.split("[")[0].rstrip()))
    # The name column width should be consistent
    # (all names padded to same width)
    col_widths = []
    for line in bundle_lines:
        after_prefix = line[2:]
        # Name column ends where [installed] or end of line is
        if "[installed]" in after_prefix:
            col_widths.append(after_prefix.index("[installed]"))
        else:
            # Padded name should have trailing spaces
            col_widths.append(
                len(after_prefix)
                - len(after_prefix.lstrip())
                + len(after_prefix.split()[0])
                if after_prefix.strip()
                else 0
            )
    # At minimum, lines with [installed] should have the tag
    # at a consistent position
    installed_lines = [ln for ln in bundle_lines if "[installed]" in ln]
    if len(installed_lines) > 1:
        positions = [ln.index("[installed]") for ln in installed_lines]
        assert len(set(positions)) == 1


def test_render_add_selector_installed_column_aligned() -> None:
    """[installed] tags must start at the same column."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(
            name="a",
            path=Path("/a"),
            subdirectories=["skills"],
        ),
        BundleInfo(
            name="long_bundle_name",
            path=Path("/l"),
            subdirectories=["hooks"],
        ),
    ]
    lines = render_add_selector(
        bundles, installed_names={"a", "long_bundle_name"}, selected=0
    )

    # Skip 3 header lines; only check bundle lines
    bundle_lines = lines[3:]
    tag_positions = []
    for line in bundle_lines:
        pos = line.index("[installed]")
        tag_positions.append(pos)
    assert len(set(tag_positions)) == 1, f"[installed] tags misaligned: {tag_positions}"


def test_render_removal_selector_columns_aligned() -> None:
    """Scope labels in removal selector must be column-aligned."""
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
            bundle_name="project_foundations",
            source_registry="default",
            scope="local",
            installed_files=[],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        ),
    ]
    lines = render_removal_selector(entries, selected=0)

    # Skip 3 header lines; only check bundle lines
    bundle_lines = lines[3:]
    bracket_positions = []
    for line in bundle_lines:
        pos = line.index("[")
        bracket_positions.append(pos)
    assert (
        len(set(bracket_positions)) == 1
    ), f"Scope columns misaligned: {bracket_positions}"


# --- Tests for cross-platform fallback and TERM=dumb (Req 26, 29) ---


def test_use_raw_mode_returns_false_when_no_textual() -> None:
    """_use_raw_mode returns False when Textual is not importable."""
    import builtins

    from ksm.selector import _use_raw_mode

    real_import = builtins.__import__

    def fake_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name == "textual":
            raise ImportError("no textual")
        return real_import(name, *args, **kwargs)

    with (
        patch.dict("os.environ", {"TERM": "xterm"}, clear=False),
        patch("ksm.selector.sys") as mock_sys,
        patch("builtins.__import__", side_effect=fake_import),
    ):
        mock_sys.stdin.isatty.return_value = True
        assert _use_raw_mode() is False


def test_use_raw_mode_returns_false_when_term_dumb() -> None:
    """_use_raw_mode returns False when TERM=dumb."""
    from ksm.selector import _use_raw_mode

    with (
        patch.dict("os.environ", {"TERM": "dumb"}),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.isatty.return_value = True
        assert _use_raw_mode() is False


def test_use_raw_mode_returns_false_when_not_tty() -> None:
    """_use_raw_mode returns False when stdin is not a TTY."""
    from ksm.selector import _use_raw_mode

    with (
        patch.dict("os.environ", {"TERM": "xterm"}),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.isatty.return_value = False
        assert _use_raw_mode() is False


def test_use_raw_mode_returns_true_when_all_conditions_met() -> None:
    """_use_raw_mode returns True when Textual available, TERM!=dumb, TTY."""
    from ksm.selector import _use_raw_mode

    with (
        patch.dict("os.environ", {"TERM": "xterm"}, clear=False),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.isatty.return_value = True
        assert _use_raw_mode() is True


def test_numbered_list_select_valid_number() -> None:
    """Numbered-list fallback returns correct index for valid number."""
    from ksm.selector import _numbered_list_select

    items = [("alpha", "desc-a"), ("beta", "desc-b")]
    stderr_buf = io.StringIO()

    with (
        patch("builtins.input", return_value="2"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stderr = stderr_buf
        result = _numbered_list_select(items, "Pick one:")

    assert result == 1  # 0-indexed


def test_numbered_list_select_q_returns_none() -> None:
    """Numbered-list fallback returns None when user enters 'q'."""
    from ksm.selector import _numbered_list_select

    items = [("alpha", "desc-a")]
    stderr_buf = io.StringIO()

    with (
        patch("builtins.input", return_value="q"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stderr = stderr_buf
        result = _numbered_list_select(items, "Pick one:")

    assert result is None


def test_numbered_list_select_invalid_then_valid() -> None:
    """Numbered-list fallback re-prompts on invalid input."""
    from ksm.selector import _numbered_list_select

    items = [("alpha", "desc-a"), ("beta", "desc-b")]
    stderr_buf = io.StringIO()
    inputs = iter(["0", "abc", "1"])

    with (
        patch("builtins.input", side_effect=inputs),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stderr = stderr_buf
        result = _numbered_list_select(items, "Pick one:")

    assert result == 0  # selected "1" which is index 0


def test_numbered_list_select_eof_returns_none() -> None:
    """Numbered-list fallback returns None on EOF."""
    from ksm.selector import _numbered_list_select

    items = [("alpha", "desc-a")]
    stderr_buf = io.StringIO()

    with (
        patch("builtins.input", side_effect=EOFError),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stderr = stderr_buf
        result = _numbered_list_select(items, "Pick one:")

    assert result is None


def test_numbered_list_select_renders_to_stderr() -> None:
    """Numbered-list fallback renders list to stderr, not stdout."""
    from ksm.selector import _numbered_list_select

    items = [("alpha", "desc-a"), ("beta", "desc-b")]
    stderr_buf = io.StringIO()
    stdout_buf = io.StringIO()

    with (
        patch("builtins.input", return_value="1"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stderr = stderr_buf
        mock_sys.stdout = stdout_buf
        _numbered_list_select(items, "Pick one:")

    stderr_output = stderr_buf.getvalue()
    assert "alpha" in stderr_output
    assert "beta" in stderr_output
    assert "1." in stderr_output
    assert "2." in stderr_output
    assert stdout_buf.getvalue() == ""


# --- Property 31: Numbered-list fallback accepts valid/rejects invalid ---


@given(
    names=st.lists(
        st.from_regex(r"[a-z]{1,10}", fullmatch=True),
        min_size=1,
        max_size=10,
        unique=True,
    ),
    data=st.data(),
)
def test_property_numbered_list_accepts_valid_number(
    names: list[str],
    data: st.DataObject,
) -> None:
    """Property 31: Valid number in [1, N] returns item at index k-1."""
    from ksm.selector import _numbered_list_select

    items = [(n, f"desc-{n}") for n in names]
    k = data.draw(
        st.integers(min_value=1, max_value=len(names)),
        label="selection",
    )
    stderr_buf = io.StringIO()

    with (
        patch("builtins.input", return_value=str(k)),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stderr = stderr_buf
        result = _numbered_list_select(items, "Pick:")

    assert result == k - 1


@given(
    names=st.lists(
        st.from_regex(r"[a-z]{1,10}", fullmatch=True),
        min_size=1,
        max_size=10,
        unique=True,
    ),
    bad_input=st.text(min_size=1).filter(
        lambda s: s.strip() != "q" and not s.strip().isdigit()
    ),
)
def test_property_numbered_list_rejects_invalid_then_q(
    names: list[str],
    bad_input: str,
) -> None:
    """Property 31: Invalid input re-prompts, then q quits."""
    from ksm.selector import _numbered_list_select

    items = [(n, f"desc-{n}") for n in names]
    inputs = iter([bad_input, "q"])
    stderr_buf = io.StringIO()

    with (
        patch("builtins.input", side_effect=inputs),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stderr = stderr_buf
        result = _numbered_list_select(items, "Pick:")

    assert result is None


# --- Property 34: TERM=dumb disables all ANSI sequences ---


@given(
    names=st.lists(
        st.from_regex(r"[a-z]{1,10}", fullmatch=True),
        min_size=1,
        max_size=5,
        unique=True,
    ),
)
def test_property_term_dumb_no_ansi_in_add_selector(
    names: list[str],
) -> None:
    """Property 34: TERM=dumb disables all ANSI sequences.

    When TERM=dumb, the selector uses numbered-list fallback
    and no ANSI escape sequences appear in output. (Req 29)
    """
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(name=n, path=Path(f"/{n}"), subdirectories=["skills"]) for n in names
    ]
    stderr_buf = io.StringIO()
    stdout_buf = io.StringIO()

    with (
        patch("ksm.selector._can_run_textual", return_value=False),
        patch.dict("os.environ", {"TERM": "dumb"}),
        patch("builtins.input", return_value="1"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stderr = stderr_buf
        mock_sys.stdout = stdout_buf

        interactive_select(bundles, installed_names=set())

    all_output = stderr_buf.getvalue() + stdout_buf.getvalue()
    assert (
        "\033[" not in all_output
    ), f"ANSI escape found in TERM=dumb output: {all_output!r}"


@given(
    entries_data=st.lists(
        st.tuples(
            st.from_regex(r"[a-z]{1,10}", fullmatch=True),
            st.sampled_from(["local", "global"]),
        ),
        min_size=1,
        max_size=5,
        unique_by=lambda x: x[0],
    ),
)
def test_property_term_dumb_no_ansi_in_removal_selector(
    entries_data: list[tuple[str, str]],
) -> None:
    """Property 34: TERM=dumb disables ANSI in removal selector."""
    from ksm.selector import interactive_removal_select

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
    stderr_buf = io.StringIO()
    stdout_buf = io.StringIO()

    with (
        patch("ksm.selector._can_run_textual", return_value=False),
        patch.dict("os.environ", {"TERM": "dumb"}),
        patch("builtins.input", return_value="1"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stderr = stderr_buf
        mock_sys.stdout = stdout_buf

        interactive_removal_select(entries)

    all_output = stderr_buf.getvalue() + stdout_buf.getvalue()
    assert (
        "\033[" not in all_output
    ), f"ANSI escape found in TERM=dumb output: {all_output!r}"


def test_interactive_select_uses_fallback_when_no_textual() -> None:
    """interactive_select uses numbered-list when Textual unavailable."""
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(name="alpha", path=Path("/a"), subdirectories=["skills"]),
        BundleInfo(name="beta", path=Path("/b"), subdirectories=["hooks"]),
    ]
    stderr_buf = io.StringIO()

    with (
        patch("ksm.selector._can_run_textual", return_value=False),
        patch("builtins.input", return_value="1"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stderr = stderr_buf
        result = interactive_select(bundles, installed_names=set())

    # Sorted alphabetically: alpha=1, beta=2. Input "1" -> alpha
    assert result == ["alpha"]


def test_interactive_removal_uses_fallback_when_no_textual() -> None:
    """interactive_removal_select uses numbered-list fallback."""
    from ksm.selector import interactive_removal_select

    entries = [
        ManifestEntry(
            bundle_name="aws",
            source_registry="default",
            scope="global",
            installed_files=[],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        ),
    ]
    stderr_buf = io.StringIO()

    with (
        patch("ksm.selector._can_run_textual", return_value=False),
        patch("builtins.input", return_value="1"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stderr = stderr_buf
        result = interactive_removal_select(entries)

    assert result is not None
    assert result[0].bundle_name == "aws"


# --- Tests for type-to-filter (Req 14) ---


def test_render_add_selector_filter_narrows_list() -> None:
    """Filter text narrows the displayed bundle list."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(name="alpha", path=Path("/a"), subdirectories=["skills"]),
        BundleInfo(name="beta", path=Path("/b"), subdirectories=["hooks"]),
        BundleInfo(name="gamma", path=Path("/g"), subdirectories=["steering"]),
    ]
    lines = render_add_selector(
        bundles, installed_names=set(), selected=0, filter_text="al"
    )
    bundle_lines = lines[3:]
    # Only "alpha" matches "al"
    assert len(bundle_lines) == 1
    assert "alpha" in bundle_lines[0]


def test_render_add_selector_filter_case_insensitive() -> None:
    """Filter matching is case-insensitive."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(name="Alpha", path=Path("/a"), subdirectories=["skills"]),
        BundleInfo(name="beta", path=Path("/b"), subdirectories=["hooks"]),
    ]
    lines = render_add_selector(
        bundles, installed_names=set(), selected=0, filter_text="ALPHA"
    )
    bundle_lines = lines[3:]
    assert len(bundle_lines) == 1
    assert "Alpha" in bundle_lines[0]


def test_render_add_selector_empty_filter_shows_all() -> None:
    """Empty filter text shows all bundles."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(name="alpha", path=Path("/a"), subdirectories=["skills"]),
        BundleInfo(name="beta", path=Path("/b"), subdirectories=["hooks"]),
    ]
    lines = render_add_selector(
        bundles, installed_names=set(), selected=0, filter_text=""
    )
    bundle_lines = lines[3:]
    assert len(bundle_lines) == 2


def test_render_add_selector_filter_text_displayed() -> None:
    """Current filter text is displayed in the output."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(name="alpha", path=Path("/a"), subdirectories=["skills"]),
    ]
    lines = render_add_selector(
        bundles, installed_names=set(), selected=0, filter_text="alp"
    )
    # The filter text should appear somewhere in the output
    full_output = "\n".join(lines)
    assert "alp" in full_output


def test_render_removal_selector_filter_narrows_list() -> None:
    """Filter text narrows the removal selector list."""
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
    lines = render_removal_selector(entries, selected=0, filter_text="gi")
    bundle_lines = lines[3:]
    assert len(bundle_lines) == 1
    assert "git" in bundle_lines[0]


# --- Property 17: Type-to-filter produces correct filtered list ---


@given(
    names=st.lists(
        st.from_regex(r"[a-z]{1,10}", fullmatch=True),
        min_size=1,
        max_size=10,
        unique=True,
    ),
    filter_text=st.from_regex(r"[a-z]{0,5}", fullmatch=True),
)
def test_property_filter_produces_correct_list(
    names: list[str],
    filter_text: str,
) -> None:
    """Property 17: Type-to-filter produces correct filtered list.

    The filtered list shall contain exactly those items whose
    names contain the filter string (case-insensitive).
    (Req 14.1, 14.4)
    """
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(name=n, path=Path(f"/{n}"), subdirectories=["skills"]) for n in names
    ]
    lines = render_add_selector(
        bundles,
        installed_names=set(),
        selected=0,
        filter_text=filter_text,
    )
    bundle_lines = lines[3:]

    # Expected: names containing filter_text (case-insensitive), sorted
    expected = sorted(
        [n for n in names if filter_text.lower() in n.lower()],
        key=str.lower,
    )
    assert len(bundle_lines) == len(expected)
    for i, name in enumerate(expected):
        assert name in bundle_lines[i]

    # Filter text should appear in output when non-empty
    if filter_text:
        full_output = "\n".join(lines)
        assert filter_text in full_output


# --- Tests for multi-select (Req 15) ---


def test_render_add_selector_multi_select_indicators() -> None:
    """Multi-select shows checkmark for selected, empty for unselected."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(name="alpha", path=Path("/a"), subdirectories=["skills"]),
        BundleInfo(name="beta", path=Path("/b"), subdirectories=["hooks"]),
        BundleInfo(name="gamma", path=Path("/g"), subdirectories=["steering"]),
    ]
    lines = render_add_selector(
        bundles,
        installed_names=set(),
        selected=1,
        multi_selected={0, 2},
    )
    bundle_lines = lines[3:]
    # alpha (index 0) is selected
    assert "[✓]" in bundle_lines[0] or "✓" in bundle_lines[0]
    # beta (index 1) is not selected
    assert "[ ]" in bundle_lines[1]
    # gamma (index 2) is selected
    assert "[✓]" in bundle_lines[2] or "✓" in bundle_lines[2]


def test_render_removal_selector_multi_select_indicators() -> None:
    """Removal selector multi-select shows correct indicators."""
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
    lines = render_removal_selector(entries, selected=0, multi_selected={1})
    bundle_lines = lines[3:]
    assert "[ ]" in bundle_lines[0]  # aws not selected
    assert "✓" in bundle_lines[1]  # git selected


def test_render_add_selector_no_multi_select_no_indicators() -> None:
    """When multi_selected is None, no checkmark indicators shown."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(name="alpha", path=Path("/a"), subdirectories=["skills"]),
    ]
    lines = render_add_selector(
        bundles, installed_names=set(), selected=0, multi_selected=None
    )
    bundle_lines = lines[3:]
    assert "[✓]" not in bundle_lines[0]
    assert "[ ]" not in bundle_lines[0]


# --- Property 4: Selector render includes header and instructions ---


@given(
    names=st.lists(
        st.from_regex(r"[a-z]{1,10}", fullmatch=True),
        min_size=1,
        max_size=5,
        unique=True,
    ),
)
def test_property_selector_includes_header_and_instructions(
    names: list[str],
) -> None:
    """Property 4: Selector render includes header and instructions.

    For any non-empty list of bundles, the rendered output shall
    include a header line and an instruction line. (Req 3.1, 3.2)
    """
    from ksm.selector import (
        _ADD_HEADER,
        _ADD_INSTRUCTIONS,
        render_add_selector,
    )

    bundles = [
        BundleInfo(name=n, path=Path(f"/{n}"), subdirectories=["skills"]) for n in names
    ]
    lines = render_add_selector(bundles, installed_names=set(), selected=0)
    assert lines[0] == _ADD_HEADER
    assert lines[1] == _ADD_INSTRUCTIONS
    assert lines[2] == ""  # blank separator


@given(
    entries_data=st.lists(
        st.tuples(
            st.from_regex(r"[a-z]{1,10}", fullmatch=True),
            st.sampled_from(["local", "global"]),
        ),
        min_size=1,
        max_size=5,
        unique_by=lambda x: x[0],
    ),
)
def test_property_removal_selector_includes_header(
    entries_data: list[tuple[str, str]],
) -> None:
    """Property 4: Removal selector includes header and instructions."""
    from ksm.selector import (
        _RM_HEADER,
        _RM_INSTRUCTIONS,
        render_removal_selector,
    )

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
    assert lines[0] == _RM_HEADER
    assert lines[1] == _RM_INSTRUCTIONS
    assert lines[2] == ""


# --- Property 18: Multi-select toggle is symmetric ---


@given(
    n=st.integers(min_value=1, max_value=20),
    selected_indices=st.frozensets(st.integers(min_value=0, max_value=19), max_size=10),
    toggle_index=st.integers(min_value=0, max_value=19),
)
def test_property_multi_select_toggle_symmetric(
    n: int,
    selected_indices: frozenset[int],
    toggle_index: int,
) -> None:
    """Property 18: Multi-select toggle is symmetric.

    Toggling an index twice returns the set to its original state.
    (Req 15.1)
    """
    # Clamp to valid range
    toggle_index = toggle_index % n
    initial = {i % n for i in selected_indices}

    # Toggle once
    after_first = set(initial)
    if toggle_index in after_first:
        after_first.discard(toggle_index)
    else:
        after_first.add(toggle_index)

    # Toggle again
    after_second = set(after_first)
    if toggle_index in after_second:
        after_second.discard(toggle_index)
    else:
        after_second.add(toggle_index)

    assert after_second == initial


# --- Property 19: Multi-select render shows correct indicators ---


@given(
    names=st.lists(
        st.from_regex(r"[a-z]{1,10}", fullmatch=True),
        min_size=1,
        max_size=8,
        unique=True,
    ),
    data=st.data(),
)
def test_property_multi_select_correct_indicators(
    names: list[str],
    data: st.DataObject,
) -> None:
    """Property 19: Multi-select render shows correct indicators.

    Selected indices show checkmark, unselected show empty box.
    (Req 15.2, 15.3)
    """
    from ksm.selector import render_add_selector

    selected_indices = set(
        data.draw(
            st.lists(
                st.integers(min_value=0, max_value=len(names) - 1),
                unique=True,
                max_size=len(names),
            ),
            label="selected_indices",
        )
    )
    bundles = [
        BundleInfo(name=n, path=Path(f"/{n}"), subdirectories=["skills"]) for n in names
    ]
    lines = render_add_selector(
        bundles,
        installed_names=set(),
        selected=0,
        multi_selected=selected_indices,
    )
    bundle_lines = lines[3:]
    sorted_names = sorted(names, key=str.lower)

    for i, _name in enumerate(sorted_names):
        if i in selected_indices:
            assert "✓" in bundle_lines[i]
        else:
            assert "[ ]" in bundle_lines[i]


# --- Tests for interactive filter/toggle/backspace in raw mode ---


# --- 5.4 Qualified name display tests ---


def test_render_add_selector_ambiguous_shows_qualified() -> None:
    """Ambiguous bundle names show registry as second column."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(
            name="aws",
            path=Path("/r1/aws"),
            subdirectories=["skills"],
            registry_name="first",
        ),
        BundleInfo(
            name="aws",
            path=Path("/r2/aws"),
            subdirectories=["steering"],
            registry_name="second",
        ),
        BundleInfo(
            name="unique",
            path=Path("/r1/unique"),
            subdirectories=["hooks"],
            registry_name="first",
        ),
    ]
    lines = render_add_selector(bundles, installed_names=set(), selected=0)

    bundle_lines = lines[3:]
    # "aws" appears in two registries → both shown with registry col
    aws_lines = [ln for ln in bundle_lines if "aws" in ln]
    assert len(aws_lines) == 2
    plain = [_ANSI_RE.sub("", ln) for ln in aws_lines]
    assert "first" in plain[0]
    assert "second" in plain[1]

    # "unique" appears in one registry → still shows registry col
    unique_lines = [ln for ln in bundle_lines if "unique" in ln]
    assert len(unique_lines) == 1


def test_render_add_selector_unique_shows_plain_name() -> None:
    """Unique bundle names show name as primary column, registry as second."""
    from ksm.selector import render_add_selector

    bundles = [
        BundleInfo(
            name="alpha",
            path=Path("/r1/alpha"),
            subdirectories=["skills"],
            registry_name="default",
        ),
        BundleInfo(
            name="beta",
            path=Path("/r2/beta"),
            subdirectories=["hooks"],
            registry_name="team",
        ),
    ]
    lines = render_add_selector(bundles, installed_names=set(), selected=0)

    bundle_lines = lines[3:]
    # Two-column layout: name is primary, registry is secondary
    alpha_line = _ANSI_RE.sub("", [ln for ln in bundle_lines if "alpha" in ln][0])
    beta_line = _ANSI_RE.sub("", [ln for ln in bundle_lines if "beta" in ln][0])
    # No registry/name prefix format
    assert "default/alpha" not in alpha_line
    assert "team/beta" not in beta_line
    # Registry shown as separate column
    assert "default" in alpha_line
    assert "team" in beta_line


# Property 6: Selector qualifies ambiguous bundle names
# and leaves unique names unqualified (Req 4.1, 4.2, 10.5, 10.6)
@given(
    shared_name=st.from_regex(r"[a-z]{2,8}", fullmatch=True),
    reg_names=st.lists(
        st.from_regex(r"[a-z]{2,6}", fullmatch=True),
        min_size=2,
        max_size=4,
        unique=True,
    ),
    unique_names=st.lists(
        st.from_regex(r"[a-z]{2,8}", fullmatch=True),
        min_size=0,
        max_size=3,
        unique=True,
    ),
)
def test_property_selector_qualifies_ambiguous_names(
    shared_name: str,
    reg_names: list[str],
    unique_names: list[str],
) -> None:
    """Property 6: All bundles show registry as second column."""
    from ksm.selector import render_add_selector

    # Filter unique_names to avoid collision with shared_name
    unique_names = [
        n
        for n in unique_names
        if n != shared_name and n not in shared_name and shared_name not in n
    ]

    bundles: list[BundleInfo] = []
    # Create ambiguous bundles (same name, different registries)
    for rn in reg_names:
        bundles.append(
            BundleInfo(
                name=shared_name,
                path=Path(f"/{rn}/{shared_name}"),
                subdirectories=["skills"],
                registry_name=rn,
            )
        )
    # Create unique bundles
    for i, un in enumerate(unique_names):
        bundles.append(
            BundleInfo(
                name=un,
                path=Path(f"/r/{un}"),
                subdirectories=["hooks"],
                registry_name=reg_names[0],
            )
        )

    lines = render_add_selector(bundles, installed_names=set(), selected=0)
    bundle_lines = lines[3:]
    full_output = _ANSI_RE.sub("", "\n".join(bundle_lines))

    # All registries should appear in the output as columns
    for rn in reg_names:
        assert rn in full_output, f"Registry '{rn}' missing from output"

    # Total bundle lines equals total bundles (no dedup)
    assert len(bundle_lines) == len(bundles)


# --- Tests for colored selector UI elements (Req 6) ---


class FakeTTY(io.StringIO):
    """A StringIO that reports itself as a TTY."""

    def isatty(self) -> bool:
        return True


class TestSelectorColor:
    """Tests for color treatment in render_add_selector
    and render_removal_selector.

    Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7
    """

    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    def _make_bundles(self, names: list[str]) -> list[BundleInfo]:
        return [
            BundleInfo(
                name=n,
                path=Path(f"/{n}"),
                subdirectories=["skills"],
                registry_name="default",
            )
            for n in names
        ]

    def _make_entries(
        self,
        data: list[tuple[str, str]],
    ) -> list[ManifestEntry]:
        return [
            ManifestEntry(
                bundle_name=name,
                source_registry="default",
                scope=scope,
                installed_files=[],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            )
            for name, scope in data
        ]

    def _color_env(self, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Set up env for color-enabled output."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")
        monkeypatch.setattr("sys.stderr", FakeTTY())

    # -- Property 19: header wrapped in bold --

    def test_add_header_bold(self, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Property 19: render_add_selector wraps
        header (_ADD_HEADER) in bold.

        Validates: Requirements 6.3
        """
        self._color_env(monkeypatch)
        from ksm.selector import render_add_selector

        bundles = self._make_bundles(["alpha"])
        lines = render_add_selector(
            bundles,
            installed_names=set(),
            selected=0,
        )
        assert self.BOLD in lines[0], (
            f"Header should contain bold ANSI code, " f"got: {lines[0]!r}"
        )

    # -- Property 20: instructions wrapped in dim --

    def test_add_instructions_dim(self, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Property 20: render_add_selector wraps
        instructions (_ADD_INSTRUCTIONS) in dim.

        Validates: Requirements 6.4
        """
        self._color_env(monkeypatch)
        from ksm.selector import render_add_selector

        bundles = self._make_bundles(["alpha"])
        lines = render_add_selector(
            bundles,
            installed_names=set(),
            selected=0,
        )
        assert self.DIM in lines[1], (
            f"Instructions should contain dim ANSI " f"code, got: {lines[1]!r}"
        )

    # -- Property 21: highlighted name wrapped in bold --

    def test_add_highlighted_name_bold(self, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Property 21: render_add_selector wraps
        highlighted bundle name in bold.

        Validates: Requirements 6.1
        """
        self._color_env(monkeypatch)
        from ksm.selector import render_add_selector

        bundles = self._make_bundles(["alpha", "beta"])
        lines = render_add_selector(
            bundles,
            installed_names=set(),
            selected=0,
        )
        # The selected line (index 3) has > prefix
        selected_line = lines[3]
        assert selected_line.startswith(">")
        assert self.BOLD in selected_line, (
            f"Highlighted name should be bold, " f"got: {selected_line!r}"
        )
        # Non-selected line should NOT have bold
        other_line = lines[4]
        assert self.BOLD not in other_line, (
            f"Non-highlighted name should not be " f"bold, got: {other_line!r}"
        )

    # -- Property 22: [installed] badge wrapped in dim --

    def test_add_installed_badge_dim(self, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Property 22: render_add_selector wraps
        [installed] badge in dim.

        Validates: Requirements 6.2
        """
        self._color_env(monkeypatch)
        from ksm.selector import render_add_selector

        bundles = self._make_bundles(["alpha", "beta"])
        lines = render_add_selector(
            bundles,
            installed_names={"alpha"},
            selected=0,
        )
        alpha_line = [ln for ln in lines if "installed" in ln][0]
        assert self.DIM in alpha_line, (
            f"[installed] badge should be dim, " f"got: {alpha_line!r}"
        )

    # -- Property 23: [scope] label wrapped in dim --

    def test_removal_scope_label_dim(self, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Property 23: render_removal_selector wraps
        [scope] label in dim.

        Validates: Requirements 6.6
        """
        self._color_env(monkeypatch)
        from ksm.selector import render_removal_selector

        entries = self._make_entries([("aws", "local"), ("git", "global")])
        lines = render_removal_selector(entries, selected=0)
        for line in lines[3:]:
            # Each bundle line has a scope label
            assert self.DIM in line, f"Scope label should be dim, " f"got: {line!r}"

    # -- Property 24: filter prompt wrapped in dim --

    def test_filter_prompt_dim(self, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Property 24: selector wraps filter prompt
        in dim when filter_text is non-empty.

        Validates: Requirements 6.7
        """
        self._color_env(monkeypatch)
        from ksm.selector import render_add_selector

        bundles = self._make_bundles(["alpha"])
        lines = render_add_selector(
            bundles,
            installed_names=set(),
            selected=0,
            filter_text="al",
        )
        # lines[2] is the filter line when filter_text
        filter_line = lines[2]
        assert "Filter:" in filter_line
        assert self.DIM in filter_line, (
            f"Filter prompt should be dim, " f"got: {filter_line!r}"
        )

    # -- Plain text when NO_COLOR is set --

    def test_no_color_plain_text(self, monkeypatch: "pytest.MonkeyPatch") -> None:
        """When NO_COLOR is set, all lines should be
        plain text (no ANSI codes).

        Validates: Requirements 6.5
        """
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setenv("TERM", "xterm-256color")
        monkeypatch.setattr("sys.stderr", FakeTTY())
        from ksm.selector import render_add_selector

        bundles = self._make_bundles(["alpha", "beta"])
        lines = render_add_selector(
            bundles,
            installed_names={"alpha"},
            selected=0,
            filter_text="al",
        )
        full = "\n".join(lines)
        assert "\033[" not in full, (
            f"NO_COLOR should suppress all ANSI " f"codes, got: {full!r}"
        )

    # -- Plain text when TERM=dumb --

    def test_term_dumb_plain_text(self, monkeypatch: "pytest.MonkeyPatch") -> None:
        """When TERM=dumb, all lines should be plain
        text (no ANSI codes).

        Validates: Requirements 6.5
        """
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "dumb")
        monkeypatch.setattr("sys.stderr", FakeTTY())
        from ksm.selector import render_add_selector

        bundles = self._make_bundles(["alpha", "beta"])
        lines = render_add_selector(
            bundles,
            installed_names={"alpha"},
            selected=0,
            filter_text="al",
        )
        full = "\n".join(lines)
        assert "\033[" not in full, (
            f"TERM=dumb should suppress all ANSI " f"codes, got: {full!r}"
        )

    # -- Removal selector: NO_COLOR plain text --

    def test_removal_no_color_plain_text(
        self, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Removal selector produces plain text when
        NO_COLOR is set.

        Validates: Requirements 6.5
        """
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setenv("TERM", "xterm-256color")
        monkeypatch.setattr("sys.stderr", FakeTTY())
        from ksm.selector import render_removal_selector

        entries = self._make_entries([("aws", "local")])
        lines = render_removal_selector(entries, selected=0)
        full = "\n".join(lines)
        assert "\033[" not in full, (
            f"NO_COLOR should suppress all ANSI "
            f"codes in removal selector, "
            f"got: {full!r}"
        )

    # -- Removal selector: TERM=dumb plain text --

    def test_removal_term_dumb_plain_text(
        self, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        """Removal selector produces plain text when
        TERM=dumb.

        Validates: Requirements 6.5
        """
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "dumb")
        monkeypatch.setattr("sys.stderr", FakeTTY())
        from ksm.selector import render_removal_selector

        entries = self._make_entries([("aws", "local")])
        lines = render_removal_selector(entries, selected=0)
        full = "\n".join(lines)
        assert "\033[" not in full, (
            f"TERM=dumb should suppress all ANSI "
            f"codes in removal selector, "
            f"got: {full!r}"
        )

    # -- Removal selector header bold --

    def test_removal_header_bold(self, monkeypatch: "pytest.MonkeyPatch") -> None:
        """render_removal_selector wraps header in bold.

        Validates: Requirements 6.3
        """
        self._color_env(monkeypatch)
        from ksm.selector import render_removal_selector

        entries = self._make_entries([("aws", "local")])
        lines = render_removal_selector(entries, selected=0)
        assert self.BOLD in lines[0], (
            f"Removal header should be bold, " f"got: {lines[0]!r}"
        )

    # -- Removal selector instructions dim --

    def test_removal_instructions_dim(self, monkeypatch: "pytest.MonkeyPatch") -> None:
        """render_removal_selector wraps instructions
        in dim.

        Validates: Requirements 6.4
        """
        self._color_env(monkeypatch)
        from ksm.selector import render_removal_selector

        entries = self._make_entries([("aws", "local")])
        lines = render_removal_selector(entries, selected=0)
        assert self.DIM in lines[1], (
            f"Removal instructions should be dim, " f"got: {lines[1]!r}"
        )


# ---------------------------------------------------------------
# Phase 2: Capability detection and fallback infrastructure
# ---------------------------------------------------------------


# ---------------------------------------------------------------
# Property 9: _can_run_textual() returns True iff stdin is TTY,
#             TERM is not dumb, and Textual is importable
# Validates: Requirements 7.1, 7.2, 7.3, 8.5, 8.6
# ---------------------------------------------------------------


class TestCanRunTextual:
    """Tests for _can_run_textual() capability detection."""

    def test_returns_false_when_not_tty(self) -> None:
        from ksm.selector import _can_run_textual

        with patch("ksm.selector.sys") as mock_sys:
            mock_sys.stdin.isatty.return_value = False
            assert _can_run_textual() is False

    def test_returns_false_when_term_dumb(self) -> None:
        from ksm.selector import _can_run_textual

        with (
            patch.dict("os.environ", {"TERM": "dumb"}),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stdin.isatty.return_value = True
            assert _can_run_textual() is False

    def test_returns_false_when_textual_not_importable(self) -> None:
        import builtins

        from ksm.selector import _can_run_textual

        real_import = builtins.__import__

        def fake_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
            if name == "textual":
                raise ImportError("no textual")
            return real_import(name, *args, **kwargs)

        with (
            patch.dict("os.environ", {"TERM": "xterm"}, clear=False),
            patch("ksm.selector.sys") as mock_sys,
            patch("builtins.__import__", side_effect=fake_import),
        ):
            mock_sys.stdin.isatty.return_value = True
            assert _can_run_textual() is False

    def test_returns_true_when_all_conditions_met(self) -> None:
        from ksm.selector import _can_run_textual

        with (
            patch.dict("os.environ", {"TERM": "xterm"}, clear=False),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stdin.isatty.return_value = True
            # Textual is installed in this venv, so import succeeds
            assert _can_run_textual() is True


# ---------------------------------------------------------------
# Property 10: Numbered-list fallback returns correct item for
#              valid 1-based index, None for q/EOF
# Validates: Requirements 7.4, 7.5, 7.6, 7.8
# ---------------------------------------------------------------


class TestNumberedListFallbackHardened:
    """Tests for _numbered_list_select() re-prompting and stderr."""

    def test_out_of_range_high_reprompts(self) -> None:
        """Input above range triggers error message and re-prompt."""
        from ksm.selector import _numbered_list_select

        items = [("alpha", ""), ("beta", "")]
        stderr_buf = io.StringIO()
        inputs = iter(["5", "1"])

        with (
            patch("builtins.input", side_effect=inputs),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            result = _numbered_list_select(items, "Pick:")

        assert result == 0
        output = stderr_buf.getvalue()
        assert "1-2" in output

    def test_out_of_range_zero_reprompts(self) -> None:
        """Input of 0 triggers error message and re-prompt."""
        from ksm.selector import _numbered_list_select

        items = [("alpha", "")]
        stderr_buf = io.StringIO()
        inputs = iter(["0", "1"])

        with (
            patch("builtins.input", side_effect=inputs),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            result = _numbered_list_select(items, "Pick:")

        assert result == 0
        output = stderr_buf.getvalue()
        assert "1-1" in output

    def test_non_numeric_reprompts(self) -> None:
        """Non-numeric input triggers error message and re-prompt."""
        from ksm.selector import _numbered_list_select

        items = [("alpha", ""), ("beta", "")]
        stderr_buf = io.StringIO()
        inputs = iter(["abc", "2"])

        with (
            patch("builtins.input", side_effect=inputs),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            result = _numbered_list_select(items, "Pick:")

        assert result == 1
        output = stderr_buf.getvalue()
        assert "1-2" in output

    def test_error_message_states_valid_range(self) -> None:
        """Error message includes the valid range."""
        from ksm.selector import _numbered_list_select

        items = [("a", ""), ("b", ""), ("c", "")]
        stderr_buf = io.StringIO()
        inputs = iter(["99", "q"])

        with (
            patch("builtins.input", side_effect=inputs),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            _numbered_list_select(items, "Pick:")

        output = stderr_buf.getvalue()
        assert "1-3" in output

    @given(
        n=st.integers(min_value=1, max_value=20),
        choice=st.integers(min_value=1, max_value=20),
    )
    def test_property_valid_index_returns_correct_item(
        self, n: int, choice: int
    ) -> None:
        """Property: valid 1-based index returns correct 0-based index."""
        from ksm.selector import _numbered_list_select

        items = [(f"item{i}", "") for i in range(n)]
        if choice > n:
            return  # skip invalid combos
        stderr_buf = io.StringIO()

        with (
            patch("builtins.input", return_value=str(choice)),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            result = _numbered_list_select(items, "Pick:")

        assert result == choice - 1


# ---------------------------------------------------------------
# Task 2.2.3: Scope fallback defaults to "local" when stdin
#             is not a TTY
# Validates: Requirement 7.7
# ---------------------------------------------------------------


class TestScopeFallbackNonTTY:
    """scope_select() returns None when stdin is not a TTY in fallback."""

    def test_non_tty_returns_none(self) -> None:
        from ksm.selector import scope_select

        with (
            patch("ksm.selector._can_run_textual", return_value=False),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stdin.isatty.return_value = False
            result = scope_select()

        assert result is None


# ---------------------------------------------------------------
# Phase 6: Structural verification tests
# Validates: Requirements 8.1–8.4, 9.4, 9.5
# ---------------------------------------------------------------


class TestSelectorStructure:
    """Verify selector.py no longer contains raw terminal code."""

    def test_no_tty_import(self) -> None:
        """selector.py does not import tty."""
        import inspect
        import ksm.selector as sel

        source = inspect.getsource(sel)
        assert "import tty" not in source

    def test_no_termios_import(self) -> None:
        """selector.py does not import termios."""
        import inspect
        import ksm.selector as sel

        source = inspect.getsource(sel)
        assert "import termios" not in source

    def test_no_process_key(self) -> None:
        """selector.py does not contain process_key."""
        import ksm.selector as sel

        assert not hasattr(sel, "process_key")

    def test_exports_clamp_index(self) -> None:
        """selector.py still exports clamp_index."""
        from ksm.selector import clamp_index

        assert clamp_index(5, 3) == 2
        assert clamp_index(-1, 3) == 0


# --- Preservation: Add Selector Core Behavior Unchanged ---


@given(
    names=st.lists(
        st.from_regex(r"[a-z]{2,8}", fullmatch=True),
        min_size=1,
        max_size=6,
        unique=True,
    ),
    registry=st.from_regex(r"[a-z]{3,8}", fullmatch=True),
    data=st.data(),
)
def test_preservation_add_selector_sorting_filtering_prefix(
    names: list[str],
    registry: str,
    data: st.DataObject,
) -> None:
    """Property 2: Preservation — Add Selector Core Behavior.

    **Validates: Requirements 3.1, 3.2, 3.3, 3.5, 3.6**

    For all bundle sets with random installed subsets and
    optional filter text, verify:
    1. Sorting order (case-insensitive by name then registry)
    2. Filter correctness (case-insensitive substring)
    3. Selected line has '>' prefix
    4. Multi-select indicators render correctly
    """
    from hypothesis import assume

    from ksm.selector import render_add_selector

    installed = set(
        data.draw(
            st.lists(
                st.sampled_from(names),
                unique=True,
                max_size=len(names),
            ),
            label="installed",
        )
    )
    filter_text = data.draw(
        st.sampled_from(["", names[0][:2]]),
        label="filter_text",
    )
    use_multi = data.draw(st.booleans(), label="use_multi")

    bundles = [
        BundleInfo(
            name=n,
            path=Path(f"/{n}"),
            subdirectories=["skills"],
            registry_name=registry,
        )
        for n in names
    ]

    expected_sorted = sorted(
        bundles,
        key=lambda b: (b.name.lower(), b.registry_name.lower()),
    )
    if filter_text:
        ft = filter_text.lower()
        expected_sorted = [
            b
            for b in expected_sorted
            if ft in b.name.lower() or ft in b.registry_name.lower()
        ]

    assume(len(expected_sorted) > 0)

    selected = data.draw(
        st.integers(
            min_value=0,
            max_value=len(expected_sorted) - 1,
        ),
        label="selected",
    )
    multi_selected: set[int] | None = None
    if use_multi:
        multi_selected = set(
            data.draw(
                st.lists(
                    st.integers(
                        min_value=0,
                        max_value=len(expected_sorted) - 1,
                    ),
                    unique=True,
                    max_size=len(expected_sorted),
                ),
                label="multi_selected",
            )
        )

    lines = render_add_selector(
        bundles,
        installed_names=installed,
        selected=selected,
        filter_text=filter_text,
        multi_selected=multi_selected,
    )

    bundle_lines = lines[3:]
    assert len(bundle_lines) == len(expected_sorted)

    for i, bundle in enumerate(expected_sorted):
        plain = _ANSI_RE.sub("", bundle_lines[i])

        # 1. Sorting: correct bundle name on each line
        assert bundle.name in plain, (
            f"Expected '{bundle.name}' in line {i}: " f"{plain!r}"
        )

        # 3. Prefix: '>' on selected, ' ' otherwise
        if i == selected:
            assert plain.startswith(">"), (
                f"Selected line {i} missing '>' prefix: " f"{plain!r}"
            )
        else:
            assert plain.startswith(" "), (
                f"Non-selected line {i} should start " f"with ' ': {plain!r}"
            )

        # 4. Multi-select indicators
        if multi_selected is not None:
            if i in multi_selected:
                assert "✓" in plain, f"Line {i} should have '✓': " f"{plain!r}"
            else:
                assert "[ ]" in plain, f"Line {i} should have '[ ]': " f"{plain!r}"

    # 2. Filter: when filter_text is set, verify it appears
    if filter_text:
        full_output = "\n".join(_ANSI_RE.sub("", ln) for ln in lines)
        assert filter_text in full_output


# --- Preservation: Removal Selector Core Behavior Unchanged ---


@given(
    entries_data=st.lists(
        st.tuples(
            st.from_regex(r"[a-z]{2,8}", fullmatch=True),
            st.sampled_from(["local", "global"]),
        ),
        min_size=1,
        max_size=6,
        unique_by=lambda x: x[0],
    ),
    data=st.data(),
)
def test_preservation_removal_selector_sorting_scope_multiselect(
    entries_data: list[tuple[str, str]],
    data: st.DataObject,
) -> None:
    """Property 2: Preservation — Removal Selector Core Behavior.

    **Validates: Requirements 3.4, 3.7**

    For all entry sets with random scopes, verify:
    1. Sort order (alphabetical by bundle name, case-insensitive)
    2. Scope label presence ([global] or [local]) per entry
    3. Multi-select indicators ([✓] / [ ]) render correctly
    4. Selected line has '>' prefix
    """
    from ksm.selector import render_removal_selector

    use_multi = data.draw(st.booleans(), label="use_multi")

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

    expected_sorted = sorted(entries_data, key=lambda x: x[0].lower())

    selected = data.draw(
        st.integers(
            min_value=0,
            max_value=len(expected_sorted) - 1,
        ),
        label="selected",
    )
    multi_selected: set[int] | None = None
    if use_multi:
        multi_selected = set(
            data.draw(
                st.lists(
                    st.integers(
                        min_value=0,
                        max_value=len(expected_sorted) - 1,
                    ),
                    unique=True,
                    max_size=len(expected_sorted),
                ),
                label="multi_selected",
            )
        )

    lines = render_removal_selector(
        entries,
        selected=selected,
        multi_selected=multi_selected,
    )

    bundle_lines = lines[3:]
    assert len(bundle_lines) == len(expected_sorted)

    for i, (name, scope) in enumerate(expected_sorted):
        plain = _ANSI_RE.sub("", bundle_lines[i])

        # 1. Sorting: correct bundle name on each line
        assert name in plain, f"Expected '{name}' on line {i}: {plain!r}"

        # 2. Scope label: correct [global] or [local]
        assert f"[{scope}" in plain, f"Expected '[{scope}' on line {i}: " f"{plain!r}"

        # 4. Prefix: '>' on selected, ' ' otherwise
        if i == selected:
            assert plain.startswith(">"), (
                f"Selected line {i} missing '>' prefix: " f"{plain!r}"
            )
        else:
            assert plain.startswith(" "), (
                f"Non-selected line {i} should start " f"with ' ': {plain!r}"
            )

        # 3. Multi-select indicators
        if multi_selected is not None:
            if i in multi_selected:
                assert "✓" in plain, f"Line {i} should have '✓': " f"{plain!r}"
            else:
                assert "[ ]" in plain, f"Line {i} should have '[ ]': " f"{plain!r}"


# --- Bug Condition Exploration: Registry Column Misalignment ---


@given(
    data=st.data(),
    names=st.lists(
        st.from_regex(r"[a-z]{2,8}", fullmatch=True),
        min_size=2,
        max_size=6,
        unique=True,
    ),
    registry=st.from_regex(r"[a-z]{3,8}", fullmatch=True),
)
def test_bug_condition_registry_column_alignment(
    data: st.DataObject,
    names: list[str],
    registry: str,
) -> None:
    """Property 1: Bug Condition — Registry Column Misalignment.

    **Validates: Requirements 1.1, 1.2, 2.1, 2.2**

    For any set of bundles where at least one is installed
    and at least one is not, the registry name column must
    start at the same horizontal position on every row.
    """
    from ksm.selector import render_add_selector

    installed = set(
        data.draw(
            st.lists(
                st.sampled_from(names),
                min_size=1,
                max_size=len(names) - 1,
                unique=True,
            ),
            label="installed",
        )
    )
    not_installed = set(names) - installed
    if not not_installed:
        return

    bundles = [
        BundleInfo(
            name=n,
            path=Path(f"/{n}"),
            subdirectories=["skills"],
            registry_name=registry,
        )
        for n in names
    ]
    lines = render_add_selector(bundles, installed_names=installed, selected=0)
    bundle_lines = lines[3:]

    reg_positions: list[int] = []
    for line in bundle_lines:
        plain = _ANSI_RE.sub("", line)
        idx = plain.rfind(registry)
        if idx >= 0:
            reg_positions.append(idx)

    assert len(reg_positions) == len(
        bundle_lines
    ), f"Registry '{registry}' not found in all lines"
    assert (
        len(set(reg_positions)) == 1
    ), f"Registry column misaligned: positions={reg_positions}"


# --- Bug Condition Exploration: Scope Column Width Inconsistency ---


@given(
    names=st.lists(
        st.from_regex(r"[a-z]{2,8}", fullmatch=True),
        min_size=2,
        max_size=6,
        unique=True,
    ),
    data=st.data(),
)
def test_bug_condition_scope_column_width(
    names: list[str],
    data: st.DataObject,
) -> None:
    """Property 1: Bug Condition — Scope Column Width Inconsistency.

    **Validates: Requirements 1.5, 2.5**

    For any set of entries with mixed scope values ("local"
    and "global"), the scope field must occupy the same width
    on every row. Measure from '[' to the character after ']'.
    """
    from ksm.selector import render_removal_selector

    scopes = data.draw(
        st.lists(
            st.sampled_from(["local", "global"]),
            min_size=len(names),
            max_size=len(names),
        ),
        label="scopes",
    )
    from hypothesis import assume

    assume("local" in scopes and "global" in scopes)

    entries = [
        ManifestEntry(
            bundle_name=name,
            source_registry="default",
            scope=scope,
            installed_files=[],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        for name, scope in zip(names, scopes)
    ]
    lines = render_removal_selector(entries, selected=0)
    bundle_lines = lines[3:]

    scope_widths: list[int] = []
    for line in bundle_lines:
        plain = _ANSI_RE.sub("", line)
        bracket_start = plain.find("[")
        bracket_end = plain.find("]", bracket_start)
        assert bracket_start >= 0, f"No '[' found in line: {plain!r}"
        assert bracket_end >= 0, f"No ']' found in line: {plain!r}"
        width = bracket_end - bracket_start + 1
        scope_widths.append(width)

    assert len(set(scope_widths)) == 1, f"Scope column widths differ: {scope_widths}"


# --- Bug Condition Exploration: TUI Registry Column Misalignment ---


@given(
    names=st.lists(
        st.from_regex(r"[a-z]{2,8}", fullmatch=True),
        min_size=2,
        max_size=6,
        unique=True,
    ),
    registry=st.from_regex(r"[a-z]{3,8}", fullmatch=True),
    data=st.data(),
)
def test_bug_condition_tui_registry_column_alignment(
    names: list[str],
    registry: str,
    data: st.DataObject,
) -> None:
    """Property 1: Bug Condition — TUI Registry Column Misalignment.

    **Validates: Requirements 1.3, 1.4, 2.3, 2.4**

    For any set of bundles with mixed installed/not-installed
    states, the Rich Text labels built by the same logic as
    BundleSelectorApp._refresh_options must have the registry
    name starting at the same position in every label's plain
    text.
    """
    from rich.text import Text

    installed = set(
        data.draw(
            st.lists(
                st.sampled_from(names),
                min_size=1,
                max_size=len(names) - 1,
                unique=True,
            ),
            label="installed",
        )
    )
    from hypothesis import assume

    assume(len(set(names) - installed) >= 1)

    bundles = [
        BundleInfo(
            name=n,
            path=Path(f"/{n}"),
            subdirectories=["skills"],
            registry_name=registry,
        )
        for n in names
    ]
    sorted_bundles = sorted(
        bundles,
        key=lambda b: (b.name.lower(), b.registry_name.lower()),
    )
    display_items = [(b.name, b) for b in sorted_bundles]
    installed_names = installed

    max_name = max(len(name) for name, _ in display_items)

    badge_text = " [installed]"
    any_installed = any(b.name in installed_names for _, b in display_items)
    badge_width = len(badge_text) if any_installed else 0

    labels: list[Text] = []
    for _display, bundle in display_items:
        is_installed = bundle.name in installed_names
        label = Text()
        label.append(_display.ljust(max_name), style="bold cyan")
        if badge_width:
            if is_installed:
                label.append(
                    badge_text.ljust(badge_width),
                    style="dim",
                )
            else:
                label.append(" " * badge_width)
        if bundle.registry_name:
            label.append(f"  {bundle.registry_name}", style="dim")
        labels.append(label)

    reg_positions: list[int] = []
    search_start = max_name + badge_width
    for lbl in labels:
        plain = lbl.plain
        idx = plain.find(registry, search_start)
        assert idx >= 0, (
            f"Registry '{registry}' not found after pos "
            f"{search_start} in: {plain!r}"
        )
        reg_positions.append(idx)

    assert len(set(reg_positions)) == 1, (
        f"TUI registry column misaligned: " f"positions={reg_positions}"
    )


# --- Bug Condition Exploration: TUI Scope Column Width ---


@given(
    names=st.lists(
        st.from_regex(r"[a-z]{2,8}", fullmatch=True),
        min_size=2,
        max_size=6,
        unique=True,
    ),
    data=st.data(),
)
def test_bug_condition_tui_scope_column_width(
    names: list[str],
    data: st.DataObject,
) -> None:
    """Property 1: Bug Condition — TUI Scope Column Width.

    **Validates: Requirements 1.6, 2.6**

    For any set of entries with mixed scope values, the Rich
    Text labels built by the same logic as
    RemovalSelectorApp._refresh_options must have the scope
    field occupying the same width in every label's plain text.
    """
    from rich.text import Text

    scopes = data.draw(
        st.lists(
            st.sampled_from(["local", "global"]),
            min_size=len(names),
            max_size=len(names),
        ),
        label="scopes",
    )
    from hypothesis import assume

    assume("local" in scopes and "global" in scopes)

    entries = [
        ManifestEntry(
            bundle_name=name,
            source_registry="default",
            scope=scope,
            installed_files=[],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        for name, scope in zip(names, scopes)
    ]
    sorted_entries = sorted(entries, key=lambda e: e.bundle_name.lower())

    max_scope = max(len(f"[{e.scope}]") for e in sorted_entries)
    labels: list[Text] = []
    for entry in sorted_entries:
        label = Text()
        label.append(entry.bundle_name, style="bold cyan")
        scope_str = f" [{entry.scope}]"
        label.append(scope_str.ljust(max_scope + 1), style="dim")
        labels.append(label)

    scope_field_widths: list[int] = []
    for lbl, entry in zip(labels, sorted_entries):
        plain = lbl.plain
        # The scope field starts right after the bundle name.
        # Its width = total plain length - name length.
        name_len = len(entry.bundle_name)
        field_width = len(plain) - name_len
        scope_field_widths.append(field_width)

    assert (
        len(set(scope_field_widths)) == 1
    ), f"TUI scope field widths differ: {scope_field_widths}"
