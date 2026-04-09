"""Preservation property tests for remove_bundle().

These tests capture the CORRECT baseline behavior of remove_bundle()
on inputs where the bug condition does NOT hold. They must pass on
both unfixed and fixed code, ensuring no regressions.

Non-buggy inputs:
- Single local-scoped entry (only one workspace)
- Global-scoped entry (workspace_path is irrelevant)
- Legacy entry with workspace_path=None
- Unrelated entries are preserved during removal

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**
"""

import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from ksm.manifest import Manifest, ManifestEntry
from ksm.remover import remove_bundle

# --- Strategies ---

_bundle_name = st.from_regex(r"[a-z]{1,8}", fullmatch=True)

_rel_file = st.from_regex(r"skills/[a-z]{1,6}\.md", fullmatch=True)

_workspace_path = st.from_regex(r"/ws/[a-z]{1,8}", fullmatch=True)

_timestamp = st.just("2025-01-15T10:30:00Z")


def _create_files(target_dir: Path, rel_files: list[str]) -> None:
    """Create files on disk so remove_bundle() can delete them."""
    for rel in rel_files:
        fpath = target_dir / rel
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_bytes(b"content")


# --- Property tests ---


@given(
    bundle_name=_bundle_name,
    rel_file=_rel_file,
    ws_path=_workspace_path,
)
def test_single_local_entry_removal(
    bundle_name: str,
    rel_file: str,
    ws_path: str,
) -> None:
    """Single local-scoped entry removal deletes the entry and files.

    When only one local entry exists for a bundle (no bug condition),
    remove_bundle() should remove it and delete its files.

    **Validates: Requirements 3.1**
    """
    with tempfile.TemporaryDirectory() as td:
        target_dir = Path(td)
        _create_files(target_dir, [rel_file])

        entry = ManifestEntry(
            bundle_name=bundle_name,
            source_registry="default",
            scope="local",
            installed_files=[rel_file],
            installed_at="2025-01-15T10:30:00Z",
            updated_at="2025-01-15T10:30:00Z",
            workspace_path=ws_path,
        )
        manifest = Manifest(entries=[entry])

        result = remove_bundle(entry, target_dir, manifest)

        # Entry is removed
        assert len(manifest.entries) == 0
        # File was deleted
        assert rel_file in result.removed_files
        assert not (target_dir / rel_file).exists()
        # No skipped files
        assert len(result.skipped_files) == 0


@given(
    bundle_name=_bundle_name,
    rel_file=_rel_file,
)
def test_global_entry_removal(
    bundle_name: str,
    rel_file: str,
) -> None:
    """Global-scoped entry removal deletes the entry and files.

    Global entries match on bundle_name + scope only (no
    workspace_path). This must continue to work.

    **Validates: Requirements 3.2**
    """
    with tempfile.TemporaryDirectory() as td:
        target_dir = Path(td)
        _create_files(target_dir, [rel_file])

        entry = ManifestEntry(
            bundle_name=bundle_name,
            source_registry="default",
            scope="global",
            installed_files=[rel_file],
            installed_at="2025-01-15T10:30:00Z",
            updated_at="2025-01-15T10:30:00Z",
            workspace_path=None,
        )
        manifest = Manifest(entries=[entry])

        result = remove_bundle(entry, target_dir, manifest)

        # Entry is removed
        assert len(manifest.entries) == 0
        # File was deleted
        assert rel_file in result.removed_files
        assert not (target_dir / rel_file).exists()


@given(
    bundle_name=_bundle_name,
    rel_file=_rel_file,
)
def test_legacy_none_workspace_path_removal(
    bundle_name: str,
    rel_file: str,
) -> None:
    """Legacy entry with workspace_path=None is removed correctly.

    Older local entries may have workspace_path=None. Removal
    should still work by matching on bundle_name + scope.

    **Validates: Requirements 3.1, 3.2**
    """
    with tempfile.TemporaryDirectory() as td:
        target_dir = Path(td)
        _create_files(target_dir, [rel_file])

        entry = ManifestEntry(
            bundle_name=bundle_name,
            source_registry="default",
            scope="local",
            installed_files=[rel_file],
            installed_at="2025-01-15T10:30:00Z",
            updated_at="2025-01-15T10:30:00Z",
            workspace_path=None,
        )
        manifest = Manifest(entries=[entry])

        result = remove_bundle(entry, target_dir, manifest)

        # Entry is removed
        assert len(manifest.entries) == 0
        # File was deleted
        assert rel_file in result.removed_files
        assert not (target_dir / rel_file).exists()


@given(
    target_name=_bundle_name,
    other_name=_bundle_name.filter(lambda n: len(n) >= 2),
    target_file=_rel_file,
    other_file=st.from_regex(r"steering/[a-z]{1,6}\.md", fullmatch=True),
    scope=st.sampled_from(["local", "global"]),
    ws_path=st.one_of(st.none(), _workspace_path),
)
def test_removal_preserves_unrelated_entries(
    target_name: str,
    other_name: str,
    target_file: str,
    other_file: str,
    scope: str,
    ws_path: str | None,
) -> None:
    """Removal of one bundle preserves other unrelated entries.

    When removing a bundle, entries for different bundle names
    must remain untouched in the manifest.

    **Validates: Requirements 3.4**
    """
    # Ensure names differ to avoid collision
    if target_name == other_name:
        other_name = other_name + "x"

    with tempfile.TemporaryDirectory() as td:
        target_dir = Path(td)
        _create_files(target_dir, [target_file, other_file])

        target_entry = ManifestEntry(
            bundle_name=target_name,
            source_registry="default",
            scope=scope,
            installed_files=[target_file],
            installed_at="2025-01-15T10:30:00Z",
            updated_at="2025-01-15T10:30:00Z",
            workspace_path=ws_path if scope == "local" else None,
        )
        other_entry = ManifestEntry(
            bundle_name=other_name,
            source_registry="default",
            scope=scope,
            installed_files=[other_file],
            installed_at="2025-01-15T10:30:00Z",
            updated_at="2025-01-15T10:30:00Z",
            workspace_path=ws_path if scope == "local" else None,
        )
        manifest = Manifest(entries=[target_entry, other_entry])

        result = remove_bundle(target_entry, target_dir, manifest)

        # Target entry removed
        remaining_names = [e.bundle_name for e in manifest.entries]
        assert target_name not in remaining_names
        # Other entry preserved
        assert other_entry in manifest.entries
        assert len(manifest.entries) == 1
        # Target file deleted
        assert target_file in result.removed_files
        # Other file still on disk
        assert (target_dir / other_file).exists()


@given(
    bundle_name=_bundle_name,
    rel_file=_rel_file,
    scope=st.sampled_from(["local", "global"]),
    ws_path=st.one_of(st.none(), _workspace_path),
)
def test_removal_result_correctness(
    bundle_name: str,
    rel_file: str,
    scope: str,
    ws_path: str | None,
) -> None:
    """RemovalResult contains correct removed_files and skipped_files.

    For non-buggy inputs, verify the result object accurately
    reflects what happened on disk.

    **Validates: Requirements 3.3**
    """
    with tempfile.TemporaryDirectory() as td:
        target_dir = Path(td)
        _create_files(target_dir, [rel_file])

        entry = ManifestEntry(
            bundle_name=bundle_name,
            source_registry="default",
            scope=scope,
            installed_files=[rel_file],
            installed_at="2025-01-15T10:30:00Z",
            updated_at="2025-01-15T10:30:00Z",
            workspace_path=ws_path if scope == "local" else None,
        )
        manifest = Manifest(entries=[entry])

        result = remove_bundle(entry, target_dir, manifest)

        # File existed, so it should be in removed_files
        assert result.removed_files == [rel_file]
        assert result.skipped_files == []
        # File is gone from disk
        assert not (target_dir / rel_file).exists()
