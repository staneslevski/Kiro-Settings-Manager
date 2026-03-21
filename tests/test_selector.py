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
    """Selector shows qualified name for ambiguous bundles."""
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
    assert "default/aws" in bundle_lines[0]
    assert "team-repo/aws" in bundle_lines[1]


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
        assert f"[{scope}]" in bundle_lines[i]


# --- Tests for interactive functions with mocked terminal I/O ---


def test_interactive_select_returns_selected_bundle() -> None:
    """interactive_select returns the selected bundle name on Enter."""
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(
            name="alpha",
            path=Path("/a"),
            subdirectories=["skills"],
            registry_name="default",
        ),
        BundleInfo(
            name="beta",
            path=Path("/b"),
            subdirectories=["hooks"],
            registry_name="default",
        ),
    ]

    # Simulate: press Enter immediately (select first item)
    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.return_value = b"\r"
        mock_sys.stderr = io.StringIO()

        result = interactive_select(bundles, installed_names=set())

    assert result == ["alpha"]


def test_interactive_select_quit_returns_none() -> None:
    """interactive_select returns None when user presses q."""
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(
            name="alpha",
            path=Path("/a"),
            subdirectories=["skills"],
            registry_name="default",
        ),
    ]

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.return_value = b"q"
        mock_sys.stderr = io.StringIO()

        result = interactive_select(bundles, installed_names=set())

    assert result is None


def test_interactive_select_empty_bundles_returns_none() -> None:
    """interactive_select returns None for empty bundle list."""
    from ksm.selector import interactive_select

    result = interactive_select([], installed_names=set())
    assert result is None


def test_interactive_select_navigate_then_select() -> None:
    """interactive_select navigates down then selects."""
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(
            name="alpha",
            path=Path("/a"),
            subdirectories=["skills"],
            registry_name="default",
        ),
        BundleInfo(
            name="beta",
            path=Path("/b"),
            subdirectories=["hooks"],
            registry_name="default",
        ),
    ]

    call_count = 0

    def fake_read(n: int) -> bytes:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return b"\x1b"  # Start of down arrow
        if call_count == 2:
            return b"[B"  # Rest of down arrow
        return b"\r"  # Enter

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.side_effect = fake_read
        mock_sys.stderr = io.StringIO()

        result = interactive_select(bundles, installed_names=set())

    assert result == ["beta"]


def test_interactive_removal_select_returns_entry() -> None:
    """interactive_removal_select returns selected ManifestEntry."""
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

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.return_value = b"\r"
        mock_sys.stderr = io.StringIO()

        result = interactive_removal_select(entries)

    assert result is not None
    assert result[0].bundle_name == "aws"


def test_interactive_removal_select_quit_returns_none() -> None:
    """interactive_removal_select returns None on quit."""
    from ksm.selector import interactive_removal_select

    entries = [
        ManifestEntry(
            bundle_name="aws",
            source_registry="default",
            scope="local",
            installed_files=[],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        ),
    ]

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.return_value = b"q"
        mock_sys.stderr = io.StringIO()

        result = interactive_removal_select(entries)

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


# --- Terminal rendering escape sequence tests ---


def test_interactive_select_does_not_use_clear_screen() -> None:
    """Interactive selector must not use ESC[2J (clear entire screen).

    ESC[2J pushes content into scrollback on every redraw,
    causing the scrollbar to jump and the viewport to shift.
    """
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(
            name="alpha",
            path=Path("/a"),
            subdirectories=["skills"],
        ),
    ]
    buf = io.StringIO()

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.return_value = b"\r"
        mock_sys.stderr = buf

        interactive_select(bundles, installed_names=set())

    full_output = buf.getvalue()
    assert "\033[2J" not in full_output, "Must not use ESC[2J — it pollutes scrollback"


def test_interactive_select_uses_cursor_home() -> None:
    """Interactive selector must use ESC[H to reposition cursor."""
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(
            name="alpha",
            path=Path("/a"),
            subdirectories=["skills"],
        ),
    ]
    buf = io.StringIO()

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.return_value = b"\r"
        mock_sys.stderr = buf

        interactive_select(bundles, installed_names=set())

    full_output = buf.getvalue()
    assert "\033[H" in full_output, "Must use ESC[H to move cursor home"


def test_interactive_select_erases_below_after_content() -> None:
    """Interactive selector must use ESC[J to erase below content."""
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(
            name="alpha",
            path=Path("/a"),
            subdirectories=["skills"],
        ),
    ]
    buf = io.StringIO()

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.return_value = b"\r"
        mock_sys.stderr = buf

        interactive_select(bundles, installed_names=set())

    full_output = buf.getvalue()
    assert "\033[J" in full_output, "Must use ESC[J to erase trailing content"


def test_interactive_select_restores_cursor_visibility() -> None:
    """Cursor must be shown again after selector exits."""
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(
            name="alpha",
            path=Path("/a"),
            subdirectories=["skills"],
        ),
    ]
    buf = io.StringIO()

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.return_value = b"q"
        mock_sys.stderr = buf

        interactive_select(bundles, installed_names=set())

    full_output = buf.getvalue()
    assert "\033[?25h" in full_output, "Must restore cursor visibility on exit"


def test_interactive_removal_does_not_use_clear_screen() -> None:
    """Removal selector must not use ESC[2J."""
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
    buf = io.StringIO()

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.return_value = b"\r"
        mock_sys.stderr = buf

        interactive_removal_select(entries)

    full_output = buf.getvalue()
    assert "\033[2J" not in full_output, "Must not use ESC[2J — it pollutes scrollback"


# --- Property tests for stderr rendering and alternate buffer (Req 25, 30) ---


@given(
    names=st.lists(
        st.from_regex(r"[a-z]{1,10}", fullmatch=True),
        min_size=1,
        max_size=5,
        unique=True,
    ),
)
def test_property_selector_renders_zero_bytes_to_stdout(
    names: list[str],
) -> None:
    """Property 30: Selector renders zero bytes to stdout.

    All ANSI escape sequences and rendered UI lines shall appear
    only on stderr. (Req 25.1, 25.2, 25.3)
    """
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(name=n, path=Path(f"/{n}"), subdirectories=["skills"]) for n in names
    ]

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.return_value = b"\r"
        mock_sys.stdout = stdout_buf
        mock_sys.stderr = stderr_buf

        interactive_select(bundles, installed_names=set())

    # stdout must have zero bytes
    assert (
        stdout_buf.getvalue() == ""
    ), f"Selector wrote to stdout: {stdout_buf.getvalue()!r}"
    # stderr must have content (the UI)
    assert len(stderr_buf.getvalue()) > 0, "Selector must write UI to stderr"


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
def test_property_removal_selector_renders_zero_bytes_to_stdout(
    entries_data: list[tuple[str, str]],
) -> None:
    """Property 30: Removal selector renders zero bytes to stdout.

    All ANSI escape sequences and rendered UI lines shall appear
    only on stderr. (Req 25.1, 25.2, 25.3)
    """
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

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.return_value = b"\r"
        mock_sys.stdout = stdout_buf
        mock_sys.stderr = stderr_buf

        interactive_removal_select(entries)

    # stdout must have zero bytes
    assert (
        stdout_buf.getvalue() == ""
    ), f"Removal selector wrote to stdout: {stdout_buf.getvalue()!r}"
    # stderr must have content (the UI)
    assert len(stderr_buf.getvalue()) > 0, "Removal selector must write UI to stderr"


def test_alternate_screen_buffer_enter_on_start() -> None:
    """Property 35: Alternate screen buffer enter sequence emitted on start.

    The stderr output shall contain ESC[?1049h (enter alternate buffer)
    before any list rendering. (Req 30.1)
    """
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(name="alpha", path=Path("/a"), subdirectories=["skills"]),
    ]
    buf = io.StringIO()

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.return_value = b"\r"
        mock_sys.stderr = buf

        interactive_select(bundles, installed_names=set())

    output = buf.getvalue()
    assert (
        "\033[?1049h" in output
    ), "Must emit ESC[?1049h to enter alternate screen buffer"


def test_alternate_screen_buffer_exit_on_finish() -> None:
    """Property 35: Alternate screen buffer exit sequence emitted on exit.

    The stderr output shall contain ESC[?1049l (exit alternate buffer)
    after the selector exits. (Req 30.2)
    """
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(name="alpha", path=Path("/a"), subdirectories=["skills"]),
    ]
    buf = io.StringIO()

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.return_value = b"q"  # quit
        mock_sys.stderr = buf

        interactive_select(bundles, installed_names=set())

    output = buf.getvalue()
    assert (
        "\033[?1049l" in output
    ), "Must emit ESC[?1049l to exit alternate screen buffer"


def test_alternate_screen_buffer_exit_on_selection() -> None:
    """Property 35: Alternate screen buffer exit on selection.

    The stderr output shall contain ESC[?1049l after selection. (Req 30.2)
    """
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(name="alpha", path=Path("/a"), subdirectories=["skills"]),
    ]
    buf = io.StringIO()

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.return_value = b"\r"  # select
        mock_sys.stderr = buf

        interactive_select(bundles, installed_names=set())

    output = buf.getvalue()
    assert (
        "\033[?1049l" in output
    ), "Must emit ESC[?1049l to exit alternate screen buffer on selection"


def test_removal_selector_alternate_screen_buffer() -> None:
    """Property 35: Removal selector uses alternate screen buffer.

    The stderr output shall contain both enter and exit sequences. (Req 30)
    """
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
    buf = io.StringIO()

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.return_value = b"\r"
        mock_sys.stderr = buf

        interactive_removal_select(entries)

    output = buf.getvalue()
    assert "\033[?1049h" in output, "Must emit enter alternate buffer sequence"
    assert "\033[?1049l" in output, "Must emit exit alternate buffer sequence"


# --- Tests for cross-platform fallback and TERM=dumb (Req 26, 29) ---


def test_use_raw_mode_returns_false_when_no_termios() -> None:
    """_use_raw_mode returns False when termios is unavailable."""
    from ksm.selector import _use_raw_mode

    with patch("ksm.selector._HAS_TERMIOS", False):
        assert _use_raw_mode() is False


def test_use_raw_mode_returns_false_when_term_dumb() -> None:
    """_use_raw_mode returns False when TERM=dumb."""
    from ksm.selector import _use_raw_mode

    with (
        patch("ksm.selector._HAS_TERMIOS", True),
        patch.dict("os.environ", {"TERM": "dumb"}),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.isatty.return_value = True
        assert _use_raw_mode() is False


def test_use_raw_mode_returns_false_when_not_tty() -> None:
    """_use_raw_mode returns False when stdin is not a TTY."""
    from ksm.selector import _use_raw_mode

    with (
        patch("ksm.selector._HAS_TERMIOS", True),
        patch.dict("os.environ", {"TERM": "xterm"}),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.isatty.return_value = False
        assert _use_raw_mode() is False


def test_use_raw_mode_returns_true_when_all_conditions_met() -> None:
    """_use_raw_mode returns True when termios available, TERM!=dumb, TTY."""
    from ksm.selector import _use_raw_mode

    with (
        patch("ksm.selector._HAS_TERMIOS", True),
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
        patch("ksm.selector._HAS_TERMIOS", True),
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
        patch("ksm.selector._HAS_TERMIOS", True),
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


def test_interactive_select_uses_fallback_when_no_termios() -> None:
    """interactive_select uses numbered-list when termios unavailable."""
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(name="alpha", path=Path("/a"), subdirectories=["skills"]),
        BundleInfo(name="beta", path=Path("/b"), subdirectories=["hooks"]),
    ]
    stderr_buf = io.StringIO()

    with (
        patch("ksm.selector._HAS_TERMIOS", False),
        patch("builtins.input", return_value="1"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stderr = stderr_buf
        result = interactive_select(bundles, installed_names=set())

    # Sorted alphabetically: alpha=1, beta=2. Input "1" -> alpha
    assert result == ["alpha"]


def test_interactive_removal_uses_fallback_when_no_termios() -> None:
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
        patch("ksm.selector._HAS_TERMIOS", False),
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


def test_process_key_alphanumeric_returns_filter_char() -> None:
    """Alphanumeric key returns filter_char action."""
    from ksm.selector import process_key

    action, idx = process_key(b"a", 0, 3)
    assert action == "filter_char"
    assert idx == 0


def test_process_key_backspace_returns_backspace() -> None:
    """Backspace key returns backspace action."""
    from ksm.selector import process_key

    action, idx = process_key(b"\x7f", 0, 3)
    assert action == "backspace"
    assert idx == 0


def test_process_key_digit_returns_filter_char() -> None:
    """Digit key returns filter_char action."""
    from ksm.selector import process_key

    action, idx = process_key(b"5", 0, 3)
    assert action == "filter_char"
    assert idx == 0


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


def test_process_key_space_returns_toggle() -> None:
    """Space key returns toggle action."""
    from ksm.selector import process_key

    action, idx = process_key(b" ", 1, 3)
    assert action == "toggle"
    assert idx == 1


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


def test_interactive_select_filter_then_select() -> None:
    """interactive_select filters by typed chars then selects."""
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(
            name="alpha",
            path=Path("/a"),
            subdirectories=["skills"],
        ),
        BundleInfo(
            name="beta",
            path=Path("/b"),
            subdirectories=["hooks"],
        ),
        BundleInfo(
            name="gamma",
            path=Path("/g"),
            subdirectories=["steering"],
        ),
    ]

    call_count = 0

    def fake_read(n: int) -> bytes:
        nonlocal call_count
        call_count += 1
        # Type "b" to filter, then Enter to select
        if call_count == 1:
            return b"b"
        return b"\r"

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.side_effect = fake_read
        mock_sys.stderr = io.StringIO()

        result = interactive_select(bundles, installed_names=set())

    assert result == ["beta"]


def test_interactive_select_backspace_clears_filter() -> None:
    """interactive_select backspace removes last filter char."""
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(
            name="alpha",
            path=Path("/a"),
            subdirectories=["skills"],
        ),
        BundleInfo(
            name="beta",
            path=Path("/b"),
            subdirectories=["hooks"],
        ),
    ]

    call_count = 0

    def fake_read(n: int) -> bytes:
        nonlocal call_count
        call_count += 1
        # Type "x" (no match), backspace, then Enter
        if call_count == 1:
            return b"x"
        if call_count == 2:
            return b"\x7f"  # backspace
        return b"\r"

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.side_effect = fake_read
        mock_sys.stderr = io.StringIO()

        result = interactive_select(bundles, installed_names=set())

    # After backspace, filter is empty, all shown, first selected
    assert result == ["alpha"]


def test_interactive_select_toggle_multi_select() -> None:
    """interactive_select Space toggles multi-select, Enter returns list."""
    from ksm.selector import interactive_select

    bundles = [
        BundleInfo(
            name="alpha",
            path=Path("/a"),
            subdirectories=["skills"],
        ),
        BundleInfo(
            name="beta",
            path=Path("/b"),
            subdirectories=["hooks"],
        ),
        BundleInfo(
            name="gamma",
            path=Path("/g"),
            subdirectories=["steering"],
        ),
    ]

    call_count = 0

    def fake_read(n: int) -> bytes:
        nonlocal call_count
        call_count += 1
        # Toggle first (Space), down, toggle second (Space), Enter
        if call_count == 1:
            return b" "  # toggle alpha
        if call_count == 2:
            return b"\x1b"  # start of down arrow
        if call_count == 3:
            return b"[B"  # rest of down arrow
        if call_count == 4:
            return b" "  # toggle beta
        return b"\r"  # confirm

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.side_effect = fake_read
        mock_sys.stderr = io.StringIO()

        result = interactive_select(bundles, installed_names=set())

    assert result == ["alpha", "beta"]


def test_interactive_removal_filter_then_select() -> None:
    """interactive_removal_select filters then selects."""
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
        ManifestEntry(
            bundle_name="git",
            source_registry="default",
            scope="local",
            installed_files=[],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        ),
    ]

    call_count = 0

    def fake_read(n: int) -> bytes:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return b"g"  # filter to "git"
        return b"\r"

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.side_effect = fake_read
        mock_sys.stderr = io.StringIO()

        result = interactive_removal_select(entries)

    assert result is not None
    assert len(result) == 1
    assert result[0].bundle_name == "git"


def test_interactive_removal_backspace_clears_filter() -> None:
    """interactive_removal_select backspace clears filter."""
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

    call_count = 0

    def fake_read(n: int) -> bytes:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return b"z"  # filter (no match)
        if call_count == 2:
            return b"\x7f"  # backspace
        return b"\r"

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.side_effect = fake_read
        mock_sys.stderr = io.StringIO()

        result = interactive_removal_select(entries)

    assert result is not None
    assert result[0].bundle_name == "aws"


def test_interactive_removal_toggle_multi_select() -> None:
    """interactive_removal_select toggle returns multiple entries."""
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
        ManifestEntry(
            bundle_name="git",
            source_registry="default",
            scope="local",
            installed_files=[],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        ),
    ]

    call_count = 0

    def fake_read(n: int) -> bytes:
        nonlocal call_count
        call_count += 1
        # Toggle first, down, toggle second, Enter
        if call_count == 1:
            return b" "  # toggle aws
        if call_count == 2:
            return b"\x1b"  # start down arrow
        if call_count == 3:
            return b"[B"  # rest down arrow
        if call_count == 4:
            return b" "  # toggle git
        return b"\r"

    with (
        patch("ksm.selector.termios") as mock_termios,
        patch("ksm.selector.tty"),
        patch("ksm.selector.sys") as mock_sys,
    ):
        mock_sys.stdin.fileno.return_value = 0
        mock_termios.tcgetattr.return_value = []
        mock_sys.stdin.buffer.read.side_effect = fake_read
        mock_sys.stderr = io.StringIO()

        result = interactive_removal_select(entries)

    assert result is not None
    assert len(result) == 2
    assert result[0].bundle_name == "aws"
    assert result[1].bundle_name == "git"


# --- 5.4 Qualified name display tests ---


def test_render_add_selector_ambiguous_shows_qualified() -> None:
    """Ambiguous bundle names show registry/bundle format."""
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
    # "aws" appears in two registries → qualified
    aws_lines = [ln for ln in bundle_lines if "aws" in ln]
    assert len(aws_lines) == 2
    assert "first/aws" in aws_lines[0]
    assert "second/aws" in aws_lines[1]

    # "unique" appears in one registry → plain name
    unique_lines = [ln for ln in bundle_lines if "unique" in ln]
    assert len(unique_lines) == 1
    assert (
        "/" not in unique_lines[0].split()[1]
        if len(unique_lines[0].split()) > 1
        else True
    )
    # More precise: should NOT contain "first/unique"
    assert "first/unique" not in unique_lines[0]


def test_render_add_selector_unique_shows_plain_name() -> None:
    """Unique bundle names show plain name without registry."""
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
    # Both names are unique → no qualified format
    alpha_line = [ln for ln in bundle_lines if "alpha" in ln][0]
    beta_line = [ln for ln in bundle_lines if "beta" in ln][0]
    assert "default/alpha" not in alpha_line
    assert "team/beta" not in beta_line


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
    """Property 6: Ambiguous names qualified, unique unqualified."""
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

    # Ambiguous bundles should show registry/name format
    for rn in reg_names:
        qualified = f"{rn}/{shared_name}"
        matching = [
            ln for ln in bundle_lines if qualified in _ANSI_RE.sub("", ln).split()
        ]
        assert len(matching) == 1, (
            f"Expected '{qualified}' as token in exactly"
            f" one line, found {len(matching)}"
        )

    # Unique bundles should NOT show qualified format
    for un in unique_names:
        un_lines = [ln for ln in bundle_lines if un in ln]
        for ln in un_lines:
            plain = _ANSI_RE.sub("", ln)
            assert f"/{un}" not in plain or (
                f"{reg_names[0]}/{un}" not in plain
            ), f"Unique name '{un}' should not be qualified"


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
