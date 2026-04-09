"""Bug condition exploration test for multi-workspace local removal.

This test encodes the EXPECTED behavior: when a local-scoped bundle
is installed in multiple workspaces and removed from one, only that
workspace's manifest entry should be removed. Other entries must remain.

On UNFIXED code this test is expected to FAIL, confirming the bug exists.
After the fix, this test validates correct behavior.

**Validates: Requirements 1.1, 1.2, 2.1, 2.2**
"""

import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from ksm.manifest import Manifest, ManifestEntry
from ksm.remover import remove_bundle

# Strategy: generate 2-5 distinct workspace paths
_workspace_paths = st.lists(
    st.from_regex(r"/ws/[a-z]{1,8}", fullmatch=True),
    min_size=2,
    max_size=5,
    unique=True,
)

_bundle_name = st.from_regex(r"[a-z]{1,8}", fullmatch=True)


def _make_local_entries(
    bundle_name: str,
    workspace_paths: list[str],
    target_dir: Path,
) -> list[ManifestEntry]:
    """Create local-scoped manifest entries with files on disk."""
    entries: list[ManifestEntry] = []
    for ws in workspace_paths:
        rel_file = f"skills/{bundle_name}-skill.md"
        fpath = target_dir / rel_file
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_bytes(b"content")
        entry = ManifestEntry(
            bundle_name=bundle_name,
            source_registry="default",
            scope="local",
            installed_files=[rel_file],
            installed_at="2025-01-15T10:30:00Z",
            updated_at="2025-01-15T10:30:00Z",
            workspace_path=ws,
        )
        entries.append(entry)
    return entries


@given(
    bundle_name=_bundle_name,
    workspace_paths=_workspace_paths,
)
def test_bug_condition_multi_workspace_local_removal(
    bundle_name: str,
    workspace_paths: list[str],
) -> None:
    """Property 1: Bug Condition — Multi-workspace local removal
    removes all entries.

    Given a manifest with 2+ local-scoped entries sharing the same
    bundle_name but different workspace_path values, removing one
    entry should leave all other entries intact.

    On UNFIXED code this FAILS because the filter matches on
    bundle_name + scope only, removing ALL entries.

    **Validates: Requirements 1.1, 1.2, 2.1, 2.2**
    """
    with tempfile.TemporaryDirectory() as td:
        target_dir = Path(td)
        entries = _make_local_entries(bundle_name, workspace_paths, target_dir)
        manifest = Manifest(entries=list(entries))

        # Remove the first entry only
        entry_to_remove = entries[0]
        other_entries = entries[1:]

        remove_bundle(entry_to_remove, target_dir, manifest)

        # The removed entry must be gone
        remaining_ws = [e.workspace_path for e in manifest.entries]
        assert entry_to_remove.workspace_path not in remaining_ws, (
            f"Entry for {entry_to_remove.workspace_path} " f"should have been removed"
        )

        # All other entries must still be present
        for other in other_entries:
            assert other in manifest.entries, (
                f"Entry for workspace_path="
                f"{other.workspace_path} was incorrectly "
                f"removed. Remaining entries: "
                f"{remaining_ws}"
            )
