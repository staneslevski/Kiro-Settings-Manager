"""Tests for ksm.copier module."""

from pathlib import Path

from hypothesis import HealthCheck, given, settings as h_settings
from hypothesis import strategies as st

from ksm.copier import (
    CopyResult,
    CopyStatus,
    copy_file,
    copy_tree,
    files_identical,
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
