"""Tests for ksm.manifest module."""

from pathlib import Path

from hypothesis import HealthCheck, given, settings as h_settings
from hypothesis import strategies as st

from ksm.manifest import (
    ManifestEntry,
    Manifest,
    _entry_to_dict,
    _dict_to_entry,
    load_manifest,
    save_manifest,
    backfill_workspace_paths,
)
from ksm.persistence import write_json


def test_load_manifest_returns_empty_when_missing(
    tmp_path: Path,
) -> None:
    """load_manifest returns an empty manifest when file doesn't exist."""
    filepath = tmp_path / "manifest.json"
    manifest = load_manifest(filepath)
    assert len(manifest.entries) == 0


def test_save_load_round_trip(tmp_path: Path) -> None:
    """save_manifest then load_manifest returns equivalent data."""
    filepath = tmp_path / "manifest.json"
    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name="aws",
                source_registry="default",
                scope="global",
                installed_files=[
                    "skills/aws-cross-account/SKILL.md",
                    "steering/AWS-IAM.md",
                ],
                installed_at="2025-01-15T10:30:00Z",
                updated_at="2025-01-15T10:30:00Z",
            ),
            ManifestEntry(
                bundle_name="git_and_github",
                source_registry="default",
                scope="local",
                installed_files=["skills/github-pr/SKILL.md"],
                installed_at="2025-01-16T08:00:00Z",
                updated_at="2025-01-16T08:00:00Z",
            ),
        ]
    )

    save_manifest(manifest, filepath)
    loaded = load_manifest(filepath)

    assert len(loaded.entries) == 2
    for orig, loaded_entry in zip(manifest.entries, loaded.entries):
        assert orig.bundle_name == loaded_entry.bundle_name
        assert orig.source_registry == loaded_entry.source_registry
        assert orig.scope == loaded_entry.scope
        assert orig.installed_files == loaded_entry.installed_files
        assert orig.installed_at == loaded_entry.installed_at
        assert orig.updated_at == loaded_entry.updated_at


def test_manifest_entry_lookup_by_name_and_scope(
    tmp_path: Path,
) -> None:
    """Manifest entries can be looked up by name and scope."""
    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name="aws",
                source_registry="default",
                scope="global",
                installed_files=["steering/AWS-IAM.md"],
                installed_at="2025-01-15T10:30:00Z",
                updated_at="2025-01-15T10:30:00Z",
            ),
            ManifestEntry(
                bundle_name="aws",
                source_registry="default",
                scope="local",
                installed_files=["steering/AWS-IAM.md"],
                installed_at="2025-01-16T08:00:00Z",
                updated_at="2025-01-16T08:00:00Z",
            ),
        ]
    )

    # Lookup by name and scope
    matches = [
        e for e in manifest.entries if e.bundle_name == "aws" and e.scope == "global"
    ]
    assert len(matches) == 1
    assert matches[0].scope == "global"

    # Lookup non-existent
    missing = [e for e in manifest.entries if e.bundle_name == "nonexistent"]
    assert len(missing) == 0


def test_load_manifest_reads_existing_file(tmp_path: Path) -> None:
    """load_manifest reads an existing JSON file correctly."""
    filepath = tmp_path / "manifest.json"
    data = {
        "entries": [
            {
                "bundle_name": "test",
                "source_registry": "custom",
                "scope": "local",
                "installed_files": ["hooks/my-hook.json"],
                "installed_at": "2025-02-01T00:00:00Z",
                "updated_at": "2025-02-01T00:00:00Z",
            }
        ]
    }
    write_json(filepath, data)

    manifest = load_manifest(filepath)
    assert len(manifest.entries) == 1
    assert manifest.entries[0].bundle_name == "test"
    assert manifest.entries[0].source_registry == "custom"


# --- Property-based tests ---


# Feature: kiro-settings-manager, Property 16: Manifest JSON round-trip
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    entries=st.lists(
        st.fixed_dictionaries(
            {
                "bundle_name": st.text(min_size=1, max_size=20),
                "source_registry": st.text(min_size=1, max_size=30),
                "scope": st.sampled_from(["local", "global"]),
                "installed_files": st.lists(
                    st.text(min_size=1, max_size=40),
                    max_size=10,
                ),
                "installed_at": st.text(min_size=1, max_size=30),
                "updated_at": st.text(min_size=1, max_size=30),
            }
        ),
        max_size=5,
    )
)
def test_property_manifest_round_trip(tmp_path: Path, entries: list[dict]) -> None:
    """Property 16: Manifest round-trip via dataclasses."""
    manifest_entries = [
        ManifestEntry(
            bundle_name=e["bundle_name"],
            source_registry=e["source_registry"],
            scope=e["scope"],
            installed_files=e["installed_files"],
            installed_at=e["installed_at"],
            updated_at=e["updated_at"],
        )
        for e in entries
    ]
    manifest = Manifest(entries=manifest_entries)
    filepath = tmp_path / "prop_manifest.json"

    save_manifest(manifest, filepath)
    loaded = load_manifest(filepath)

    assert len(loaded.entries) == len(manifest.entries)
    for orig, loaded_entry in zip(manifest.entries, loaded.entries):
        assert orig.bundle_name == loaded_entry.bundle_name
        assert orig.source_registry == loaded_entry.source_registry
        assert orig.scope == loaded_entry.scope
        assert orig.installed_files == loaded_entry.installed_files
        assert orig.installed_at == loaded_entry.installed_at
        assert orig.updated_at == loaded_entry.updated_at


# --- workspace_path serialization tests ---


def test_entry_with_workspace_path_round_trip() -> None:
    """Entry with workspace_path serializes and deserializes correctly."""
    entry = ManifestEntry(
        bundle_name="python_dev",
        source_registry="default",
        scope="local",
        installed_files=["skills/python/SKILL.md"],
        installed_at="2025-01-20T12:00:00Z",
        updated_at="2025-01-20T12:00:00Z",
        workspace_path="/home/user/project-a",
    )

    d = _entry_to_dict(entry)
    assert d["workspace_path"] == "/home/user/project-a"

    restored = _dict_to_entry(d)
    assert restored.workspace_path == "/home/user/project-a"
    assert restored.bundle_name == entry.bundle_name
    assert restored.scope == entry.scope


def test_dict_without_workspace_path_deserializes_as_none() -> None:
    """Legacy dict without workspace_path deserializes with None."""
    data = {
        "bundle_name": "aws",
        "source_registry": "default",
        "scope": "local",
        "installed_files": ["steering/AWS-IAM.md"],
        "installed_at": "2025-01-15T10:30:00Z",
        "updated_at": "2025-01-15T10:30:00Z",
    }

    entry = _dict_to_entry(data)
    assert entry.workspace_path is None


def test_entry_with_none_workspace_path_omits_key() -> None:
    """Entry with workspace_path=None does not include it in dict."""
    entry = ManifestEntry(
        bundle_name="git_and_github",
        source_registry="default",
        scope="global",
        installed_files=["skills/github-pr/SKILL.md"],
        installed_at="2025-01-16T08:00:00Z",
        updated_at="2025-01-16T08:00:00Z",
        workspace_path=None,
    )

    d = _entry_to_dict(entry)
    assert "workspace_path" not in d


def test_workspace_path_full_save_load_round_trip(
    tmp_path: Path,
) -> None:
    """save/load round-trip preserves workspace_path on entries."""
    filepath = tmp_path / "manifest.json"
    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name="local_bundle",
                source_registry="default",
                scope="local",
                installed_files=["steering/test.md"],
                installed_at="2025-02-01T00:00:00Z",
                updated_at="2025-02-01T00:00:00Z",
                workspace_path="/tmp/workspace-x",
            ),
            ManifestEntry(
                bundle_name="global_bundle",
                source_registry="default",
                scope="global",
                installed_files=["steering/global.md"],
                installed_at="2025-02-01T00:00:00Z",
                updated_at="2025-02-01T00:00:00Z",
                workspace_path=None,
            ),
        ]
    )

    save_manifest(manifest, filepath)
    loaded = load_manifest(filepath)

    assert loaded.entries[0].workspace_path == "/tmp/workspace-x"
    assert loaded.entries[1].workspace_path is None


# --- backfill_workspace_paths tests ---


def test_backfill_sets_workspace_path_for_legacy_entry_with_matching_files(
    tmp_path: Path,
) -> None:
    """Legacy local entry whose installed_files exist under
    workspace/.kiro/ gets workspace_path set to resolved workspace."""
    ws = tmp_path / "project-a"
    kiro_dir = ws / ".kiro"
    kiro_dir.mkdir(parents=True)
    (kiro_dir / "steering").mkdir()
    (kiro_dir / "steering" / "AWS-IAM.md").touch()

    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name="aws",
                source_registry="default",
                scope="local",
                installed_files=["steering/AWS-IAM.md"],
                installed_at="2025-01-15T10:30:00Z",
                updated_at="2025-01-15T10:30:00Z",
                workspace_path=None,
            ),
        ]
    )

    result = backfill_workspace_paths(manifest, ws)

    assert result is True
    assert manifest.entries[0].workspace_path == str(ws.resolve())


def test_backfill_leaves_legacy_entry_unchanged_when_no_files_match(
    tmp_path: Path,
) -> None:
    """Legacy local entry whose installed_files do NOT exist under
    workspace/.kiro/ is left with workspace_path=None."""
    ws = tmp_path / "project-b"
    kiro_dir = ws / ".kiro"
    kiro_dir.mkdir(parents=True)

    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name="missing_bundle",
                source_registry="default",
                scope="local",
                installed_files=["steering/nonexistent.md"],
                installed_at="2025-01-15T10:30:00Z",
                updated_at="2025-01-15T10:30:00Z",
                workspace_path=None,
            ),
        ]
    )

    result = backfill_workspace_paths(manifest, ws)

    assert result is False
    assert manifest.entries[0].workspace_path is None


def test_backfill_skips_entry_already_having_workspace_path(
    tmp_path: Path,
) -> None:
    """Entry that already has workspace_path set is not modified,
    even if its files exist under the workspace."""
    ws = tmp_path / "project-c"
    kiro_dir = ws / ".kiro"
    kiro_dir.mkdir(parents=True)
    (kiro_dir / "skills").mkdir()
    (kiro_dir / "skills" / "SKILL.md").touch()

    original_path = "/some/other/workspace"
    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name="already_set",
                source_registry="default",
                scope="local",
                installed_files=["skills/SKILL.md"],
                installed_at="2025-01-15T10:30:00Z",
                updated_at="2025-01-15T10:30:00Z",
                workspace_path=original_path,
            ),
        ]
    )

    result = backfill_workspace_paths(manifest, ws)

    assert result is False
    assert manifest.entries[0].workspace_path == original_path


def test_backfill_does_not_touch_global_entries(
    tmp_path: Path,
) -> None:
    """Global entries are never modified by backfill, even if
    their files happen to exist under the workspace."""
    ws = tmp_path / "project-d"
    kiro_dir = ws / ".kiro"
    kiro_dir.mkdir(parents=True)
    (kiro_dir / "steering").mkdir()
    (kiro_dir / "steering" / "global.md").touch()

    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name="global_bundle",
                source_registry="default",
                scope="global",
                installed_files=["steering/global.md"],
                installed_at="2025-01-15T10:30:00Z",
                updated_at="2025-01-15T10:30:00Z",
                workspace_path=None,
            ),
        ]
    )

    result = backfill_workspace_paths(manifest, ws)

    assert result is False
    assert manifest.entries[0].workspace_path is None


def test_backfill_returns_true_when_updated_false_otherwise(
    tmp_path: Path,
) -> None:
    """Returns True when at least one entry was updated,
    False when no entries were changed."""
    ws = tmp_path / "project-e"
    kiro_dir = ws / ".kiro"
    kiro_dir.mkdir(parents=True)
    (kiro_dir / "hooks").mkdir()
    (kiro_dir / "hooks" / "my-hook.json").touch()

    manifest_with_match = Manifest(
        entries=[
            ManifestEntry(
                bundle_name="matched",
                source_registry="default",
                scope="local",
                installed_files=["hooks/my-hook.json"],
                installed_at="2025-01-15T10:30:00Z",
                updated_at="2025-01-15T10:30:00Z",
                workspace_path=None,
            ),
            ManifestEntry(
                bundle_name="global_one",
                source_registry="default",
                scope="global",
                installed_files=["steering/g.md"],
                installed_at="2025-01-15T10:30:00Z",
                updated_at="2025-01-15T10:30:00Z",
                workspace_path=None,
            ),
        ]
    )

    assert backfill_workspace_paths(manifest_with_match, ws) is True

    # Second call: entry already backfilled, nothing to update
    assert backfill_workspace_paths(manifest_with_match, ws) is False
