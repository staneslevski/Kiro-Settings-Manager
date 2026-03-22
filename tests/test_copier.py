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


def test_copy_tree_unchanged_files_included(tmp_path: Path) -> None:
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
    from ksm.copier import _STATUS_SYMBOLS

    pairs = list(zip(statuses, filenames))
    results = [CopyResult(path=Path(fn), status=st) for st, fn in pairs]

    output = format_diff_summary(results)

    symbols = list(_STATUS_SYMBOLS.values())
    assert len(symbols) == len(set(symbols))

    for r in results:
        expected_sym = _STATUS_SYMBOLS[r.status]
        assert f"{expected_sym} {r.path}" in output
        assert f"({r.status.value})" in output


# ------------------------------------------------------------------
# Colorized format_diff_summary tests — semantic colors
# ------------------------------------------------------------------

# ANSI escape code constants (semantic colors)
_SUCCESS = "\033[92m"  # bright green
_WARNING_STYLE = "\033[93m"  # bright yellow
_MUTED = "\033[2m"  # dim
_RESET = "\033[0m"


def _make_tty_stream() -> MagicMock:
    stream = MagicMock(spec=StringIO)
    stream.isatty.return_value = True
    return stream


def _make_non_tty_stream() -> StringIO:
    return StringIO()


def _clean_env() -> dict[str, str]:
    return {"TERM": "xterm-256color"}


class TestDiffSummaryNewSuccess:
    """Validates: Req 15.2 — NEW uses success color."""

    def test_new_symbol_success_on_tty(self) -> None:
        results = [CopyResult(path=Path("file.txt"), status=CopyStatus.NEW)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert f"{_SUCCESS}+{_RESET}" in output

    def test_new_label_muted_on_tty(self) -> None:
        results = [CopyResult(path=Path("file.txt"), status=CopyStatus.NEW)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert f"{_MUTED}(new){_RESET}" in output

    def test_new_path_present(self) -> None:
        results = [CopyResult(path=Path("steering/code.md"), status=CopyStatus.NEW)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert "steering/code.md" in output


class TestDiffSummaryUpdatedWarning:
    """Validates: Req 15.3 — UPDATED uses warning_style."""

    def test_updated_symbol_warning_on_tty(self) -> None:
        results = [CopyResult(path=Path("skills/SKILL.md"), status=CopyStatus.UPDATED)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert f"{_WARNING_STYLE}~{_RESET}" in output

    def test_updated_label_muted_on_tty(self) -> None:
        results = [CopyResult(path=Path("skills/SKILL.md"), status=CopyStatus.UPDATED)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert f"{_MUTED}(updated){_RESET}" in output


class TestDiffSummaryUnchangedMuted:
    """Validates: Req 15.4 — UNCHANGED uses muted."""

    def test_unchanged_symbol_muted_on_tty(self) -> None:
        results = [CopyResult(path=Path("review.md"), status=CopyStatus.UNCHANGED)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert f"{_MUTED}={_RESET}" in output

    def test_unchanged_label_muted_on_tty(self) -> None:
        results = [CopyResult(path=Path("review.md"), status=CopyStatus.UNCHANGED)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert f"{_MUTED}(unchanged){_RESET}" in output


class TestDiffSummaryRelativePaths:
    """Validates: Req 15.1 — relative paths with base_path."""

    def test_relative_path_with_base(self) -> None:
        results = [
            CopyResult(
                path=Path("/home/user/.kiro/steering/code.md"),
                status=CopyStatus.NEW,
            )
        ]
        output = format_diff_summary(results, base_path=Path("/home/user/.kiro"))
        assert "steering/code.md" in output
        assert "/home/user/.kiro" not in output

    def test_absolute_path_without_base(self) -> None:
        results = [
            CopyResult(
                path=Path("/home/user/.kiro/steering/code.md"),
                status=CopyStatus.NEW,
            )
        ]
        output = format_diff_summary(results)
        assert "/home/user/.kiro/steering/code.md" in output


class TestDiffSummaryNoColor:
    """Validates: plain text when NO_COLOR set."""

    def test_no_color_new(self) -> None:
        results = [CopyResult(path=Path("f.txt"), status=CopyStatus.NEW)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            output = format_diff_summary(results, stream=stream)
        assert "\033[" not in output
        assert "+" in output
        assert "(new)" in output

    def test_no_color_updated(self) -> None:
        results = [CopyResult(path=Path("f.txt"), status=CopyStatus.UPDATED)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            output = format_diff_summary(results, stream=stream)
        assert "\033[" not in output
        assert "~" in output
        assert "(updated)" in output

    def test_no_color_unchanged(self) -> None:
        results = [CopyResult(path=Path("f.txt"), status=CopyStatus.UNCHANGED)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            output = format_diff_summary(results, stream=stream)
        assert "\033[" not in output
        assert "=" in output
        assert "(unchanged)" in output

    def test_non_tty_plain_text(self) -> None:
        results = [CopyResult(path=Path("f.txt"), status=CopyStatus.NEW)]
        stream = _make_non_tty_stream()
        output = format_diff_summary(results, stream=stream)
        assert "\033[" not in output

    def test_term_dumb_plain_text(self) -> None:
        results = [CopyResult(path=Path("f.txt"), status=CopyStatus.NEW)]
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"TERM": "dumb"}, clear=True):
            output = format_diff_summary(results, stream=stream)
        assert "\033[" not in output


class TestDiffSummaryMixed:
    """Verify all three colors appear in a mixed result set."""

    def test_mixed_statuses_colored(self) -> None:
        results = [
            CopyResult(path=Path("new.md"), status=CopyStatus.NEW),
            CopyResult(path=Path("upd.md"), status=CopyStatus.UPDATED),
            CopyResult(path=Path("same.md"), status=CopyStatus.UNCHANGED),
        ]
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            output = format_diff_summary(results, stream=stream)
        assert _SUCCESS in output
        assert _WARNING_STYLE in output
        assert _MUTED in output

    def test_mixed_statuses_no_color(self) -> None:
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


# Feature: ux-visual-overhaul, Property 9: Diff summary uses
# semantic colors per status
# **Validates: Requirements 7.2-7.4, 9.4, 15.2, 15.3, 15.4**
@given(
    statuses=st.lists(_status_strategy, min_size=1, max_size=10),
    filenames=st.lists(_filename_strategy, min_size=1, max_size=10),
)
def test_property_diff_summary_semantic_colors(
    statuses: list[CopyStatus],
    filenames: list[str],
) -> None:
    """Property 9: Each status uses correct semantic color."""
    from ksm.copier import _STATUS_SYMBOLS

    color_map = {
        CopyStatus.NEW: _SUCCESS,
        CopyStatus.UPDATED: _WARNING_STYLE,
        CopyStatus.UNCHANGED: _MUTED,
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
        assert f"{_MUTED}({r.status.value}){_RESET}" in output
        assert str(r.path) in output


# Feature: ux-visual-overhaul, Property 10: Diff summary displays
# relative paths
# **Validates: Requirements 7.5, 15.1**
@given(
    statuses=st.lists(_status_strategy, min_size=1, max_size=10),
    subdirs=st.lists(
        st.from_regex(
            r"[a-z]{1,6}/[a-z]{1,6}\.[a-z]{1,3}",
            fullmatch=True,
        ),
        min_size=1,
        max_size=10,
    ),
)
def test_property_diff_summary_relative_paths(
    statuses: list[CopyStatus],
    subdirs: list[str],
) -> None:
    """Property 10: Paths displayed relative to base_path."""
    base = Path("/home/user/.kiro")
    pairs = list(zip(statuses, subdirs))
    results = [CopyResult(path=base / rel, status=s) for s, rel in pairs]
    output = format_diff_summary(results, base_path=base)
    for s, rel in pairs:
        assert rel in output
        assert str(base / rel) not in output


@given(
    statuses=st.lists(_status_strategy, min_size=1, max_size=10),
    filenames=st.lists(_filename_strategy, min_size=1, max_size=10),
)
def test_property_diff_summary_plain_no_color(
    statuses: list[CopyStatus],
    filenames: list[str],
) -> None:
    """Property 11 (PBT): plain text when NO_COLOR set."""
    pairs = list(zip(statuses, filenames))
    results = [CopyResult(path=Path(fn), status=s) for s, fn in pairs]
    stream = _make_tty_stream()
    with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
        output = format_diff_summary(results, stream=stream)
    assert "\033[" not in output
    for r in results:
        assert str(r.path) in output
        assert f"({r.status.value})" in output


# ------------------------------------------------------------------
# Additional unit tests for format_diff_summary (Task 3.1.1)
# Validates: Requirements 15.1, 15.2, 15.3, 15.4
# ------------------------------------------------------------------


class TestDiffSummarySymbolConstants:
    """Validates: Req 15.2-15.4 — symbols match color.py constants."""

    def test_status_symbols_match_color_constants(self) -> None:
        """_STATUS_SYMBOLS values match SYM_NEW/UPDATED/UNCHANGED."""
        from ksm.color import SYM_NEW, SYM_UNCHANGED, SYM_UPDATED
        from ksm.copier import _STATUS_SYMBOLS

        assert _STATUS_SYMBOLS[CopyStatus.NEW] == SYM_NEW
        assert _STATUS_SYMBOLS[CopyStatus.UPDATED] == SYM_UPDATED
        assert _STATUS_SYMBOLS[CopyStatus.UNCHANGED] == SYM_UNCHANGED

    def test_symbols_are_fixed_values(self) -> None:
        """SYM_NEW=+, SYM_UPDATED=~, SYM_UNCHANGED==."""
        from ksm.color import SYM_NEW, SYM_UNCHANGED, SYM_UPDATED

        assert SYM_NEW == "+"
        assert SYM_UPDATED == "~"
        assert SYM_UNCHANGED == "="


class TestDiffSummaryEdgeCases:
    """Edge cases for format_diff_summary."""

    def test_empty_results_returns_empty_string(self) -> None:
        output = format_diff_summary([])
        assert output == ""

    def test_base_path_fallback_when_not_relative(self) -> None:
        """When path is not under base_path, absolute path shown."""
        results = [
            CopyResult(
                path=Path("/other/place/file.md"),
                status=CopyStatus.NEW,
            )
        ]
        output = format_diff_summary(results, base_path=Path("/home/user/.kiro"))
        assert "/other/place/file.md" in output

    def test_each_line_has_two_space_indent(self) -> None:
        """Each output line starts with 2-space indent (Req 16.2)."""
        results = [
            CopyResult(path=Path("a.md"), status=CopyStatus.NEW),
            CopyResult(path=Path("b.md"), status=CopyStatus.UPDATED),
            CopyResult(path=Path("c.md"), status=CopyStatus.UNCHANGED),
        ]
        output = format_diff_summary(results)
        for line in output.splitlines():
            assert line.startswith("  ")
