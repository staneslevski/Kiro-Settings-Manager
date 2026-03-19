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


def test_empty_subdirectories_preserved(tmp_path: Path) -> None:
    """remove_bundle leaves empty subdirectories in place."""
    from ksm.remover import remove_bundle

    target = tmp_path / ".kiro"
    entry, manifest = _make_manifest_entry(target, files=["skills/only-file.md"])

    remove_bundle(entry, target, manifest)

    assert not (target / "skills" / "only-file.md").exists()
    assert (target / "skills").is_dir()


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


# Property 37: Empty subdirs preserved after removal
@given(
    subdir=st.sampled_from(["skills", "steering", "hooks", "agents"]),
)
def test_property_empty_subdirs_preserved(subdir: str) -> None:
    """Property 37: Empty subdirectories are preserved after removal."""
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
        assert (target / subdir).is_dir()
