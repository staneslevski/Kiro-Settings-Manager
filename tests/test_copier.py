"""Tests for ksm.copier module."""

from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from hypothesis import HealthCheck, given, settings as h_settings
from hypothesis import strategies as st

from ksm.copier import (
    CopyResult,
    CopyStatus,
    copy_file,
    copy_tree,
    files_identical,
    format_diff_summary,
)


def test_copy_file_new_file(tmp_path: Path) -> None:
    """copy_file returns NEW status for non-existent destination."""
    src = tmp_path / "src" / "file.txt"
    dst = tmp_path / "dst" / "file.txt"
    src.parent.mkdir(parents=True)
    src.write_bytes(b"hello world\n")

    result = copy_file(src, dst)

    assert result.status == CopyStatus.NEW
    assert result.path == dst
    assert dst.read_bytes() == b"hello world\n"


def test_copy_file_skips_identical(tmp_path: Path) -> None:
    """copy_file returns UNCHANGED for identical content."""
    src = tmp_path / "src" / "file.txt"
    dst = tmp_path / "dst" / "file.txt"
    src.parent.mkdir(parents=True)
    dst.parent.mkdir(parents=True)
    content = b"same content"
    src.write_bytes(content)
    dst.write_bytes(content)

    result = copy_file(src, dst)

    assert result.status == CopyStatus.UNCHANGED
    assert result.path == dst


def test_copy_file_overwrites_different(tmp_path: Path) -> None:
    """copy_file returns UPDATED for different content."""
    src = tmp_path / "src" / "file.txt"
    dst = tmp_path / "dst" / "file.txt"
    src.parent.mkdir(parents=True)
    dst.parent.mkdir(parents=True)
    src.write_bytes(b"new content")
    dst.write_bytes(b"old content")

    result = copy_file(src, dst)

    assert result.status == CopyStatus.UPDATED
    assert result.path == dst
    assert dst.read_bytes() == b"new content"


def test_copy_tree_preserves_structure(tmp_path: Path) -> None:
    """copy_tree preserves directory structure."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "subdir").mkdir(parents=True)
    (src / "file1.txt").write_bytes(b"one")
    (src / "subdir" / "file2.txt").write_bytes(b"two")

    results = copy_tree(src, dst)

    assert (dst / "file1.txt").read_bytes() == b"one"
    assert (dst / "subdir" / "file2.txt").read_bytes() == b"two"
    assert len(results) == 2
    assert all(r.status == CopyStatus.NEW for r in results)


def test_copy_tree_returns_all_results(tmp_path: Path) -> None:
    """copy_tree returns CopyResult for every file."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "a").mkdir(parents=True)
    (src / "a" / "b.txt").write_bytes(b"data")

    results = copy_tree(src, dst)

    paths = [r.path for r in results]
    assert dst / "a" / "b.txt" in paths


def test_copy_tree_unchanged_files_included(
    tmp_path: Path,
) -> None:
    """copy_tree includes UNCHANGED files in results."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    src_file = src / "same.txt"
    dst_file = dst / "same.txt"
    content = b"identical"
    src_file.write_bytes(content)
    dst_file.write_bytes(content)

    results = copy_tree(src, dst)

    assert len(results) == 1
    assert results[0].status == CopyStatus.UNCHANGED


def test_files_identical_true(tmp_path: Path) -> None:
    """files_identical returns True for identical files."""
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    content = b"same bytes"
    a.write_bytes(content)
    b.write_bytes(content)

    assert files_identical(a, b) is True


def test_files_identical_false(tmp_path: Path) -> None:
    """files_identical returns False for different files."""
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_bytes(b"content a")
    b.write_bytes(b"content b")

    assert files_identical(a, b) is False


def test_files_identical_different_sizes(tmp_path: Path) -> None:
    """files_identical returns False for files of different sizes."""
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_bytes(b"short")
    b.write_bytes(b"much longer content here")

    assert files_identical(a, b) is False


# --- Property-based tests ---


# Feature: kiro-settings-manager, Property 18: File copy preserves structure and content
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    data=st.data(),
    file_contents=st.dictionaries(
        keys=st.from_regex(r"[a-z]{1,8}/[a-z]{1,8}\.[a-z]{1,3}", fullmatch=True),
        values=st.binary(min_size=0, max_size=200),
        min_size=1,
        max_size=5,
    ),
)
def test_property_copy_preserves_structure_and_content(
    tmp_path: Path,
    data: st.DataObject,
    file_contents: dict[str, bytes],
) -> None:
    """Property 18: copy_tree preserves directory structure and content."""
    isolation = data.draw(st.uuids().map(str), label="isolation")
    src = tmp_path / isolation / "src"
    dst = tmp_path / isolation / "dst"

    for rel_path, content in file_contents.items():
        src_file = src / rel_path
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_bytes(content)

    copy_tree(src, dst)

    for rel_path, content in file_contents.items():
        dst_file = dst / rel_path
        assert dst_file.exists(), f"{rel_path} missing in destination"
        assert dst_file.read_bytes() == content


# Feature: kiro-settings-manager, Property 19: Identical files are skipped
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    data=st.data(),
    content=st.binary(min_size=1, max_size=200),
)
def test_property_identical_files_skipped(
    tmp_path: Path,
    data: st.DataObject,
    content: bytes,
) -> None:
    """Property 19: Identical files are skipped during copy."""
    isolation = data.draw(st.uuids().map(str), label="isolation")
    src = tmp_path / isolation / "src" / "file.bin"
    dst = tmp_path / isolation / "dst" / "file.bin"
    src.parent.mkdir(parents=True, exist_ok=True)
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(content)
    dst.write_bytes(content)

    result = copy_file(src, dst)

    assert result.status == CopyStatus.UNCHANGED
    assert dst.read_bytes() == content


# Feature: ux-review-fixes
# Property 22: File diff summary uses distinct status symbols
@given(
    statuses=st.lists(
        st.sampled_from(list(CopyStatus)),
        min_size=1,
        max_size=10,
    ),
    filenames=st.lists(
        st.from_regex(r"[a-z]{1,6}/[a-z]{1,6}\.[a-z]{1,3}", fullmatch=True),
        min_size=1,
        max_size=10,
    ),
)
def test_property_diff_summary_distinct_symbols(
    statuses: list[CopyStatus],
    filenames: list[str],
) -> None:
    """Property 22: File diff summary uses distinct status symbols."""
    from ksm.copier import _STATUS_SYMBOLS, format_diff_summary

    # Pair up statuses and filenames (zip to shorter)
    pairs = list(zip(statuses, filenames))
    results = [CopyResult(path=Path(fn), status=st) for st, fn in pairs]

    output = format_diff_summary(results)

    # Verify symbols are pairwise distinct
    symbols = list(_STATUS_SYMBOLS.values())
    assert len(symbols) == len(set(symbols))

    # Verify each result appears with correct symbol
    for r in results:
        expected_sym = _STATUS_SYMBOLS[r.status]
        assert f"{expected_sym} {r.path}" in output
        assert f"({r.status.value})" in output


# ------------------------------------------------------------------
# Colorized format_diff_summary tests (Req 4) — stream parameter
# ------------------------------------------------------------------
# These tests verify that format_diff_summary applies ANSI color
# to symbols and labels when a TTY stream is passed, and returns
# plain text otherwise.
# ------------------------------------------------------------------

# ANSI escape code constants
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def _make_tty_stream() -> MagicMock:
    """Create a mock stream that reports as a TTY."""
    stream = MagicMock(spec=StringIO)
    stream.isatty.return_value = True
    return stream


def _make_non_tty_stream() -> StringIO:
    """Create a non-TTY stream (StringIO has isatty=False)."""
    return StringIO()


def _clean_env() -> dict[str, str]:
    """Env dict with NO_COLOR removed and TERM set."""
    return {"TERM": "xterm-256color"}


# --- Property 8: NEW status wraps + and (new) in green ---


class TestDiffSummaryNewGreen:
    """Validates: Requirements 4.1"""

    def test_new_symbol_green_on_tty(self) -> None:
        """Property 8: NEW status wraps + symbol in green
        when stream is a TTY."""
        results = [CopyResult(path=Path("file.txt"), status=CopyStatus.NEW)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert f"{_GREEN}+{_RESET}" in output

    def test_new_label_green_on_tty(self) -> None:
        """Property 8: NEW status wraps (new) label in green
        when stream is a TTY."""
        results = [CopyResult(path=Path("file.txt"), status=CopyStatus.NEW)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert f"{_GREEN}(new){_RESET}" in output

    def test_new_path_present(self) -> None:
        """File path appears in the output for NEW status."""
        results = [
            CopyResult(
                path=Path("steering/code.md"),
                status=CopyStatus.NEW,
            )
        ]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert "steering/code.md" in output


# --- Property 9: UPDATED wraps ~ and (updated) in yellow ---


class TestDiffSummaryUpdatedYellow:
    """Validates: Requirements 4.2"""

    def test_updated_symbol_yellow_on_tty(self) -> None:
        """Property 9: UPDATED status wraps ~ symbol in yellow
        when stream is a TTY."""
        results = [
            CopyResult(
                path=Path("skills/SKILL.md"),
                status=CopyStatus.UPDATED,
            )
        ]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert f"{_YELLOW}~{_RESET}" in output

    def test_updated_label_yellow_on_tty(self) -> None:
        """Property 9: UPDATED status wraps (updated) label in
        yellow when stream is a TTY."""
        results = [
            CopyResult(
                path=Path("skills/SKILL.md"),
                status=CopyStatus.UPDATED,
            )
        ]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert f"{_YELLOW}(updated){_RESET}" in output

    def test_updated_path_present(self) -> None:
        """File path appears in the output for UPDATED status."""
        results = [
            CopyResult(
                path=Path("hooks/pre-commit.json"),
                status=CopyStatus.UPDATED,
            )
        ]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert "hooks/pre-commit.json" in output


# --- Property 10: UNCHANGED wraps = and (unchanged) in dim ---


class TestDiffSummaryUnchangedDim:
    """Validates: Requirements 4.3"""

    def test_unchanged_symbol_dim_on_tty(self) -> None:
        """Property 10: UNCHANGED status wraps = symbol in dim
        when stream is a TTY."""
        results = [
            CopyResult(
                path=Path("steering/review.md"),
                status=CopyStatus.UNCHANGED,
            )
        ]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert f"{_DIM}={_RESET}" in output

    def test_unchanged_label_dim_on_tty(self) -> None:
        """Property 10: UNCHANGED status wraps (unchanged) label
        in dim when stream is a TTY."""
        results = [
            CopyResult(
                path=Path("steering/review.md"),
                status=CopyStatus.UNCHANGED,
            )
        ]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert f"{_DIM}(unchanged){_RESET}" in output

    def test_unchanged_path_present(self) -> None:
        """File path appears in the output for UNCHANGED."""
        results = [
            CopyResult(
                path=Path("config.json"),
                status=CopyStatus.UNCHANGED,
            )
        ]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert "config.json" in output


# --- Property 11: plain text when NO_COLOR is set ---


class TestDiffSummaryNoColor:
    """Validates: Requirements 4.5"""

    def test_no_color_new(self) -> None:
        """Property 11: NEW returns plain text when NO_COLOR."""
        results = [CopyResult(path=Path("f.txt"), status=CopyStatus.NEW)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            output = format_diff_summary(results, stream=stream)
        assert "\033[" not in output
        assert "+" in output
        assert "(new)" in output

    def test_no_color_updated(self) -> None:
        """Property 11: UPDATED returns plain text when
        NO_COLOR."""
        results = [CopyResult(path=Path("f.txt"), status=CopyStatus.UPDATED)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            output = format_diff_summary(results, stream=stream)
        assert "\033[" not in output
        assert "~" in output
        assert "(updated)" in output

    def test_no_color_unchanged(self) -> None:
        """Property 11: UNCHANGED returns plain text when
        NO_COLOR."""
        results = [CopyResult(path=Path("f.txt"), status=CopyStatus.UNCHANGED)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            output = format_diff_summary(results, stream=stream)
        assert "\033[" not in output
        assert "=" in output
        assert "(unchanged)" in output

    def test_non_tty_plain_text(self) -> None:
        """format_diff_summary returns plain text when stream
        is not a TTY."""
        results = [CopyResult(path=Path("f.txt"), status=CopyStatus.NEW)]
        stream = _make_non_tty_stream()
        output = format_diff_summary(results, stream=stream)
        assert "\033[" not in output
        assert "+" in output
        assert "(new)" in output

    def test_term_dumb_plain_text(self) -> None:
        """format_diff_summary returns plain text when
        TERM=dumb."""
        results = [CopyResult(path=Path("f.txt"), status=CopyStatus.NEW)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"TERM": "dumb"}, clear=True):
            output = format_diff_summary(results, stream=stream)
        assert "\033[" not in output


# --- Mixed statuses test ---


class TestDiffSummaryMixed:
    """Verify all three colors appear in a mixed result set."""

    def test_mixed_statuses_colored(self) -> None:
        """All three status colors appear in mixed output."""
        results = [
            CopyResult(path=Path("new.md"), status=CopyStatus.NEW),
            CopyResult(path=Path("upd.md"), status=CopyStatus.UPDATED),
            CopyResult(path=Path("same.md"), status=CopyStatus.UNCHANGED),
        ]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert _GREEN in output
        assert _YELLOW in output
        assert _DIM in output

    def test_mixed_statuses_no_color(self) -> None:
        """Mixed output has no ANSI codes when NO_COLOR set."""
        results = [
            CopyResult(path=Path("new.md"), status=CopyStatus.NEW),
            CopyResult(path=Path("upd.md"), status=CopyStatus.UPDATED),
            CopyResult(path=Path("same.md"), status=CopyStatus.UNCHANGED),
        ]
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            output = format_diff_summary(results, stream=stream)
        assert "\033[" not in output
        assert "+" in output
        assert "~" in output
        assert "=" in output


# --- Property-based tests for colorized diff summary ---


_status_strategy = st.sampled_from(list(CopyStatus))
_filename_strategy = st.from_regex(r"[a-z]{1,6}/[a-z]{1,6}\.[a-z]{1,3}", fullmatch=True)


@given(
    statuses=st.lists(_status_strategy, min_size=1, max_size=10),
    filenames=st.lists(_filename_strategy, min_size=1, max_size=10),
)
def test_property_diff_summary_color_on_tty(
    statuses: list[CopyStatus],
    filenames: list[str],
) -> None:
    """Property 8-10 (PBT): Each status uses its correct ANSI
    color code when stream is a TTY.
    Validates: Requirements 4.1, 4.2, 4.3"""
    from ksm.copier import _STATUS_SYMBOLS

    color_map = {
        CopyStatus.NEW: _GREEN,
        CopyStatus.UPDATED: _YELLOW,
        CopyStatus.UNCHANGED: _DIM,
    }
    pairs = list(zip(statuses, filenames))
    results = [CopyResult(path=Path(fn), status=s) for s, fn in pairs]
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        output = format_diff_summary(results, stream=stream)
    for r in results:
        sym = _STATUS_SYMBOLS[r.status]
        expected_color = color_map[r.status]
        assert f"{expected_color}{sym}{_RESET}" in output
        label = f"({r.status.value})"
        assert f"{expected_color}{label}{_RESET}" in output
        assert str(r.path) in output


@given(
    statuses=st.lists(_status_strategy, min_size=1, max_size=10),
    filenames=st.lists(_filename_strategy, min_size=1, max_size=10),
)
def test_property_diff_summary_plain_no_color(
    statuses: list[CopyStatus],
    filenames: list[str],
) -> None:
    """Property 11 (PBT): format_diff_summary returns plain
    text when NO_COLOR is set, for arbitrary inputs.
    Validates: Requirements 4.5"""
    pairs = list(zip(statuses, filenames))
    results = [CopyResult(path=Path(fn), status=s) for s, fn in pairs]
    stream = _make_tty_stream()
    with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
        output = format_diff_summary(results, stream=stream)
    assert "\033[" not in output
    for r in results:
        assert str(r.path) in output
        assert f"({r.status.value})" in output
