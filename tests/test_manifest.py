"""Tests for ksm.manifest module."""

from pathlib import Path

from hypothesis import HealthCheck, given, settings as h_settings
from hypothesis import strategies as st

from ksm.manifest import (
    ManifestEntry,
    Manifest,
    load_manifest,
    save_manifest,
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
