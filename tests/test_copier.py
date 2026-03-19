"""Tests for ksm.copier module."""

from pathlib import Path

from hypothesis import HealthCheck, given, settings as h_settings
from hypothesis import strategies as st

from ksm.copier import copy_file, copy_tree, files_identical


def test_copy_file_copies_content(tmp_path: Path) -> None:
    """copy_file copies content byte-for-byte."""
    src = tmp_path / "src" / "file.txt"
    dst = tmp_path / "dst" / "file.txt"
    src.parent.mkdir(parents=True)
    src.write_bytes(b"hello world\n")

    result = copy_file(src, dst)

    assert result is True
    assert dst.read_bytes() == b"hello world\n"


def test_copy_file_skips_identical(tmp_path: Path) -> None:
    """copy_file skips when destination has identical content."""
    src = tmp_path / "src" / "file.txt"
    dst = tmp_path / "dst" / "file.txt"
    src.parent.mkdir(parents=True)
    dst.parent.mkdir(parents=True)
    content = b"same content"
    src.write_bytes(content)
    dst.write_bytes(content)

    result = copy_file(src, dst)

    assert result is False


def test_copy_file_overwrites_different(tmp_path: Path) -> None:
    """copy_file overwrites when destination has different content."""
    src = tmp_path / "src" / "file.txt"
    dst = tmp_path / "dst" / "file.txt"
    src.parent.mkdir(parents=True)
    dst.parent.mkdir(parents=True)
    src.write_bytes(b"new content")
    dst.write_bytes(b"old content")

    result = copy_file(src, dst)

    assert result is True
    assert dst.read_bytes() == b"new content"


def test_copy_tree_preserves_structure(tmp_path: Path) -> None:
    """copy_tree preserves directory structure."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    # Create nested structure
    (src / "subdir").mkdir(parents=True)
    (src / "file1.txt").write_bytes(b"one")
    (src / "subdir" / "file2.txt").write_bytes(b"two")

    copied = copy_tree(src, dst)

    assert (dst / "file1.txt").read_bytes() == b"one"
    assert (dst / "subdir" / "file2.txt").read_bytes() == b"two"
    assert len(copied) == 2


def test_copy_tree_returns_copied_paths(tmp_path: Path) -> None:
    """copy_tree returns list of destination paths that were copied."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "a").mkdir(parents=True)
    (src / "a" / "b.txt").write_bytes(b"data")

    copied = copy_tree(src, dst)

    assert dst / "a" / "b.txt" in copied


def test_copy_tree_skips_identical_files(tmp_path: Path) -> None:
    """copy_tree skips files that already exist with identical content."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    src_file = src / "same.txt"
    dst_file = dst / "same.txt"
    content = b"identical"
    src_file.write_bytes(content)
    dst_file.write_bytes(content)

    copied = copy_tree(src, dst)

    assert len(copied) == 0


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

    assert result is False
    assert dst.read_bytes() == content
