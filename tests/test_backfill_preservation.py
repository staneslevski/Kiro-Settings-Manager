"""Preservation property test for backfill safety.

Property 4: Preservation — Backfill Does Not Alter
Non-Legacy Entries.

``backfill_workspace_paths()`` must not modify entries that
already have ``workspace_path`` set, and must not modify
global entries. Only legacy local entries
(``scope="local"`` and ``workspace_path is None``) are
candidates for backfill.

**Validates: Requirements 2.5, 3.5**
"""

import copy
import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from ksm.manifest import (
    Manifest,
    ManifestEntry,
    backfill_workspace_paths,
)

WORKSPACE_A = "/tmp/project-a"
WORKSPACE_B = "/tmp/project-b"

# ── Hypothesis strategies ────────────────────────────

_bundle_name_st = st.from_regex(r"[a-z]{2,8}", fullmatch=True)

_file_path_st = st.from_regex(
    r"(skills|steering|hooks|agents)/[a-z]{2,6}\.md",
    fullmatch=True,
)

_workspace_path_st = st.sampled_from([WORKSPACE_A, WORKSPACE_B, "/home/user/proj"])


def _make_entry(
    name: str,
    scope: str,
    workspace_path: str | None,
    files: list[str] | None = None,
) -> ManifestEntry:
    """Create a ManifestEntry with defaults."""
    return ManifestEntry(
        bundle_name=name,
        source_registry="default",
        scope=scope,
        installed_files=files or ["skills/f.md"],
        installed_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        workspace_path=workspace_path,
    )


@st.composite
def _non_legacy_entry_st(
    draw: st.DrawFn,
) -> ManifestEntry:
    """Generate an entry that should NOT be modified.

    Either a global entry (any workspace_path) or a local
    entry with workspace_path already set.
    """
    name = draw(_bundle_name_st)
    files = draw(st.lists(_file_path_st, min_size=1, max_size=3))
    scope = draw(st.sampled_from(["global", "local"]))
    if scope == "global":
        wp = None
    else:
        wp = draw(_workspace_path_st)
    return _make_entry(name, scope, wp, files)


@st.composite
def _manifest_with_non_legacy_st(
    draw: st.DrawFn,
) -> list[ManifestEntry]:
    """Generate a list of non-legacy entries.

    All entries either have scope="global" or have
    workspace_path already set.
    """
    entries = draw(
        st.lists(
            _non_legacy_entry_st(),
            min_size=1,
            max_size=5,
            unique_by=lambda e: e.bundle_name,
        )
    )
    return entries


# ── Property 4: Preservation ─────────────────────────
# Backfill Does Not Alter Non-Legacy Entries
#
# Observation: ``backfill_workspace_paths()`` does not
# modify entries that already have ``workspace_path``
# set. It also does not modify global entries.
#
# Property: for all manifests, entries with existing
# ``workspace_path`` or ``scope="global"`` are unchanged
# after backfill.
#
# **Validates: Requirements 2.5, 3.5**


@given(entries=_manifest_with_non_legacy_st())
def test_property4_preservation_non_legacy_unchanged(
    entries: list[ManifestEntry],
) -> None:
    """Property 4 Preservation: backfill does not alter
    entries with existing workspace_path or global scope.

    For all manifests containing only non-legacy entries,
    every entry must be identical after calling
    ``backfill_workspace_paths()``.

    **Validates: Requirements 2.5, 3.5**
    """
    manifest = Manifest(entries=entries)
    snapshots = [copy.deepcopy(e) for e in entries]

    with tempfile.TemporaryDirectory() as td:
        ws = Path(td) / "workspace"
        kiro_dir = ws / ".kiro"
        kiro_dir.mkdir(parents=True)

        # Create files matching installed_files so
        # backfill would update IF they were legacy
        for entry in entries:
            for f in entry.installed_files:
                fp = kiro_dir / f
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.touch()

        result = backfill_workspace_paths(manifest, ws)

    # No entries should have been modified
    assert result is False, (
        "backfill returned True but no legacy entries "
        "exist — non-legacy entries were modified"
    )

    for original, current in zip(snapshots, manifest.entries):
        assert current.bundle_name == original.bundle_name
        assert current.scope == original.scope
        assert current.workspace_path == original.workspace_path
        assert current.installed_files == original.installed_files
        assert current.installed_at == original.installed_at
        assert current.updated_at == original.updated_at
        assert current.source_registry == original.source_registry
