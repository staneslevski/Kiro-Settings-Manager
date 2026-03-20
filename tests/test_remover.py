"""Tests for ksm.remover module."""

import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from ksm.manifest import Manifest, ManifestEntry


def _make_manifest_entry(
    target_dir: Path,
    bundle_name: str = "aws",
    scope: str = "local",
    files: list[str] | None = None,
) -> tuple[ManifestEntry, Manifest]:
    """Create files on disk and return a manifest entry + manifest."""
    if files is None:
        files = ["skills/aws-cross/SKILL.md", "steering/AWS-IAM.md"]
    for rel in files:
        fpath = target_dir / rel
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_bytes(b"content")
    entry = ManifestEntry(
        bundle_name=bundle_name,
        source_registry="default",
        scope=scope,
        installed_files=files,
        installed_at="2025-01-15T10:30:00Z",
        updated_at="2025-01-15T10:30:00Z",
    )
    manifest = Manifest(entries=[entry])
    return entry, manifest


def test_removal_deletes_all_manifest_listed_files(
    tmp_path: Path,
) -> None:
    """remove_bundle deletes all files listed in the manifest entry."""
    from ksm.remover import remove_bundle

    target = tmp_path / ".kiro"
    entry, manifest = _make_manifest_entry(target)

    result = remove_bundle(entry, target, manifest)

    for rel in entry.installed_files:
        assert not (target / rel).exists()
    assert len(result.removed_files) == 2
    assert len(result.skipped_files) == 0


def test_removal_skips_missing_files(tmp_path: Path) -> None:
    """remove_bundle skips files that no longer exist on disk."""
    from ksm.remover import remove_bundle

    target = tmp_path / ".kiro"
    files = ["skills/a.md", "steering/b.md"]
    entry, manifest = _make_manifest_entry(target, files=files)

    # Delete one file before removal
    (target / "skills" / "a.md").unlink()

    result = remove_bundle(entry, target, manifest)

    assert "skills/a.md" in result.skipped_files
    assert "steering/b.md" in result.removed_files
    assert not (target / "steering" / "b.md").exists()


def test_manifest_entry_removed_after_deletion(
    tmp_path: Path,
) -> None:
    """remove_bundle removes the entry from the manifest."""
    from ksm.remover import remove_bundle

    target = tmp_path / ".kiro"
    entry, manifest = _make_manifest_entry(target)
    assert len(manifest.entries) == 1

    remove_bundle(entry, target, manifest)

    assert len(manifest.entries) == 0


def test_empty_subdirectories_cleaned_up(tmp_path: Path) -> None:
    """remove_bundle cleans up empty subdirectories after deletion."""
    from ksm.remover import remove_bundle

    target = tmp_path / ".kiro"
    entry, manifest = _make_manifest_entry(target, files=["skills/only-file.md"])

    remove_bundle(entry, target, manifest)

    assert not (target / "skills" / "only-file.md").exists()
    assert not (target / "skills").exists()


def test_removal_with_multiple_entries_preserves_others(
    tmp_path: Path,
) -> None:
    """remove_bundle only removes the target entry, not others."""
    from ksm.remover import remove_bundle

    target = tmp_path / ".kiro"
    entry1, _ = _make_manifest_entry(target, bundle_name="aws", files=["skills/a.md"])
    entry2 = ManifestEntry(
        bundle_name="git",
        source_registry="default",
        scope="local",
        installed_files=["skills/b.md"],
        installed_at="2025-01-15T10:30:00Z",
        updated_at="2025-01-15T10:30:00Z",
    )
    (target / "skills" / "b.md").parent.mkdir(parents=True, exist_ok=True)
    (target / "skills" / "b.md").write_bytes(b"git content")
    manifest = Manifest(entries=[entry1, entry2])

    remove_bundle(entry1, target, manifest)

    assert len(manifest.entries) == 1
    assert manifest.entries[0].bundle_name == "git"
    assert (target / "skills" / "b.md").exists()


# --- Property-based tests ---


# Property 32: Removal deletes exactly manifest-listed files
@given(
    file_names=st.lists(
        st.from_regex(r"[a-z]{1,6}/[a-z]{1,8}\.[a-z]{1,3}", fullmatch=True),
        min_size=1,
        max_size=5,
        unique=True,
    ),
)
def test_property_removal_deletes_exactly_manifest_files(
    file_names: list[str],
) -> None:
    """Property 32: Removal deletes exactly the manifest-listed files."""
    from ksm.remover import remove_bundle

    with tempfile.TemporaryDirectory() as td:
        target = Path(td)
        # Create all files
        for rel in file_names:
            fpath = target / rel
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_bytes(b"data")

        # Also create an extra file NOT in the manifest
        extra = target / "extra" / "keep.md"
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_bytes(b"keep me")

        entry = ManifestEntry(
            bundle_name="b",
            source_registry="default",
            scope="local",
            installed_files=file_names,
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        manifest = Manifest(entries=[entry])

        result = remove_bundle(entry, target, manifest)

        # All manifest files deleted
        for rel in file_names:
            assert not (target / rel).exists()
        assert set(result.removed_files) == set(file_names)
        # Extra file preserved
        assert extra.exists()


# Feature: kiro-settings-manager, Property 33: Removal removes the manifest entry
@given(
    bundle_name=st.from_regex(r"[a-z]{1,10}", fullmatch=True),
)
def test_property_removal_removes_manifest_entry(
    bundle_name: str,
) -> None:
    """Property 33: Removal removes the manifest entry."""
    from ksm.remover import remove_bundle

    with tempfile.TemporaryDirectory() as td:
        target = Path(td)
        fpath = target / "skills" / "f.md"
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_bytes(b"x")

        entry = ManifestEntry(
            bundle_name=bundle_name,
            source_registry="default",
            scope="local",
            installed_files=["skills/f.md"],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        manifest = Manifest(entries=[entry])

        remove_bundle(entry, target, manifest)

        matching = [e for e in manifest.entries if e.bundle_name == bundle_name]
        assert len(matching) == 0


# Property 36: Missing files on disk are skipped gracefully
@given(
    file_names=st.lists(
        st.from_regex(r"[a-z]{1,6}/[a-z]{1,8}\.[a-z]{1,3}", fullmatch=True),
        min_size=2,
        max_size=5,
        unique=True,
    ),
)
def test_property_missing_files_skipped_gracefully(
    file_names: list[str],
) -> None:
    """Property 36: Missing files on disk are skipped gracefully."""
    from ksm.remover import remove_bundle

    with tempfile.TemporaryDirectory() as td:
        target = Path(td)
        # Create only the first file, skip the rest
        first = target / file_names[0]
        first.parent.mkdir(parents=True, exist_ok=True)
        first.write_bytes(b"data")

        entry = ManifestEntry(
            bundle_name="b",
            source_registry="default",
            scope="local",
            installed_files=file_names,
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        manifest = Manifest(entries=[entry])

        result = remove_bundle(entry, target, manifest)

        assert file_names[0] in result.removed_files
        for missing in file_names[1:]:
            assert missing in result.skipped_files
        assert len(manifest.entries) == 0


# Property 37: Empty subdirs cleaned up after removal
@given(
    subdir=st.sampled_from(["skills", "steering", "hooks", "agents"]),
)
def test_property_empty_subdirs_cleaned_up(subdir: str) -> None:
    """Property 37: Empty subdirectories are cleaned up after removal.

    **Validates: Requirements 33.1, 33.2**
    """
    from ksm.remover import remove_bundle

    with tempfile.TemporaryDirectory() as td:
        target = Path(td)
        fpath = target / subdir / "file.md"
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_bytes(b"x")

        entry = ManifestEntry(
            bundle_name="b",
            source_registry="default",
            scope="local",
            installed_files=[f"{subdir}/file.md"],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        manifest = Manifest(entries=[entry])

        remove_bundle(entry, target, manifest)

        assert not (target / subdir / "file.md").exists()
        assert not (target / subdir).exists()


# --- Tests for _cleanup_empty_dirs ---


def test_cleanup_empty_dirs_removes_nested_empty(
    tmp_path: Path,
) -> None:
    """_cleanup_empty_dirs removes nested empty dirs up to boundary."""
    from ksm.remover import _cleanup_empty_dirs

    target = tmp_path / ".kiro"
    deep = target / "skills" / "aws" / "sub"
    deep.mkdir(parents=True)

    _cleanup_empty_dirs(deep, target)

    assert not (target / "skills").exists()
    assert target.exists()


def test_cleanup_empty_dirs_stops_at_kiro_boundary(
    tmp_path: Path,
) -> None:
    """_cleanup_empty_dirs never removes the .kiro/ dir itself."""
    from ksm.remover import _cleanup_empty_dirs

    target = tmp_path / ".kiro"
    child = target / "skills"
    child.mkdir(parents=True)

    _cleanup_empty_dirs(child, target)

    assert not child.exists()
    assert target.exists()


def test_cleanup_empty_dirs_preserves_non_empty(
    tmp_path: Path,
) -> None:
    """_cleanup_empty_dirs stops at a dir that still has files."""
    from ksm.remover import _cleanup_empty_dirs

    target = tmp_path / ".kiro"
    parent = target / "skills"
    parent.mkdir(parents=True)
    (parent / "keep.md").write_bytes(b"keep")
    child = parent / "empty-sub"
    child.mkdir()

    _cleanup_empty_dirs(child, target)

    assert not child.exists()
    assert parent.exists()
    assert (parent / "keep.md").exists()


def test_cleanup_empty_dirs_preserves_sibling_dirs(
    tmp_path: Path,
) -> None:
    """_cleanup_empty_dirs does not touch sibling directories."""
    from ksm.remover import _cleanup_empty_dirs

    target = tmp_path / ".kiro"
    empty_dir = target / "skills" / "removed"
    empty_dir.mkdir(parents=True)
    sibling = target / "steering"
    sibling.mkdir(parents=True)
    (sibling / "file.md").write_bytes(b"x")

    _cleanup_empty_dirs(empty_dir, target)

    assert sibling.exists()
    assert (sibling / "file.md").exists()


def test_cleanup_empty_dirs_noop_for_nonexistent(
    tmp_path: Path,
) -> None:
    """_cleanup_empty_dirs is a no-op if start_dir doesn't exist."""
    from ksm.remover import _cleanup_empty_dirs

    target = tmp_path / ".kiro"
    target.mkdir()
    nonexistent = target / "gone"

    _cleanup_empty_dirs(nonexistent, target)

    assert target.exists()


# Strategy: generate a list of path segments for nesting depth
_dir_segment = st.from_regex(r"[a-z]{1,6}", fullmatch=True)


@given(
    empty_segments=st.lists(_dir_segment, min_size=1, max_size=5, unique=True),
    occupied_segments=st.lists(_dir_segment, min_size=1, max_size=3, unique=True),
    file_name=st.from_regex(r"[a-z]{1,6}\.md", fullmatch=True),
)
def test_property_empty_dir_cleanup_boundary(
    empty_segments: list[str],
    occupied_segments: list[str],
    file_name: str,
) -> None:
    """Property 38: Empty dir cleanup removes only empty dirs
    up to .kiro/ boundary.

    **Validates: Requirements 33.1, 33.2, 33.3**

    Generates random directory structures and verifies:
    - Empty dirs along the path are removed
    - The boundary dir (.kiro/) is never removed
    - Non-empty sibling dirs and their contents are preserved
    """
    from ksm.remover import _cleanup_empty_dirs

    with tempfile.TemporaryDirectory() as td:
        boundary = Path(td) / ".kiro"
        boundary.mkdir()

        # Build a nested empty dir chain inside boundary
        empty_chain = boundary
        for seg in empty_segments:
            empty_chain = empty_chain / seg
        empty_chain.mkdir(parents=True, exist_ok=True)

        # Build a separate occupied dir tree with a file
        occupied_dir = boundary
        for seg in occupied_segments:
            occupied_dir = occupied_dir / seg
        occupied_dir.mkdir(parents=True, exist_ok=True)
        kept_file = occupied_dir / file_name
        kept_file.write_bytes(b"keep")

        # Record all dirs that contain files (non-empty)
        dirs_before: set[Path] = set()
        for p in boundary.rglob("*"):
            if p.is_file():
                # Mark every ancestor up to boundary
                parent = p.parent
                while parent != boundary:
                    dirs_before.add(parent)
                    parent = parent.parent

        # Act
        _cleanup_empty_dirs(empty_chain, boundary)

        # 1. Boundary is never removed
        assert boundary.exists(), "Boundary dir was removed"

        # 2. The occupied file is preserved
        assert kept_file.exists(), "File in non-empty dir was deleted"

        # 3. All dirs that contained files still exist
        for d in dirs_before:
            assert d.exists(), f"Non-empty dir {d} was removed"

        # 4. No empty dirs remain along the cleaned path
        check = empty_chain
        while check != boundary and check != boundary.parent:
            if check.exists():
                # If it still exists it must be non-empty
                assert any(check.iterdir()), f"Empty dir {check} was not cleaned up"
            check = check.parent
