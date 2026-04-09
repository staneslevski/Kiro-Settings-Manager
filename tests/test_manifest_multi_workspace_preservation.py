"""Preservation property tests for multi-workspace manifest behavior.

These tests capture EXISTING CORRECT behavior that must not regress
after the multi-workspace bugfix. They are expected to PASS on
unfixed code.

Property 2: Preservation — Global and Same-Workspace Behavior Unchanged

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**
"""

from hypothesis import given
from hypothesis import strategies as st

from ksm.installer import _update_manifest
from ksm.manifest import Manifest, ManifestEntry

# Strategy for valid bundle names: lowercase + digits + underscore
_bundle_name_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
    min_size=1,
    max_size=30,
)

# Strategy for source registries
_source_registry_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
    min_size=1,
    max_size=30,
)

# Strategy for workspace paths
_workspace_path_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_/",
    min_size=1,
    max_size=60,
)


@given(
    bundle_name=_bundle_name_st,
    registry_a=_source_registry_st,
    registry_b=_source_registry_st,
)
def test_global_reinstall_updates_in_place(
    bundle_name: str,
    registry_a: str,
    registry_b: str,
) -> None:
    """**Validates: Requirements 3.1**

    For all global-scoped installs, re-installing the same bundle
    updates the existing entry in place. After two calls with the
    same (bundle_name, "global"), there is exactly 1 entry.
    """
    manifest = Manifest(entries=[])
    files_a = ["steering/a.md"]
    files_b = ["hooks/b.json"]

    # First global install
    _update_manifest(
        manifest,
        bundle_name=bundle_name,
        source_registry=registry_a,
        scope="global",
        installed_files=files_a,
    )
    assert len(manifest.entries) == 1

    # Second global install (same bundle, different registry)
    _update_manifest(
        manifest,
        bundle_name=bundle_name,
        source_registry=registry_b,
        scope="global",
        installed_files=files_b,
    )

    # Must still be exactly 1 entry (updated in place)
    assert len(manifest.entries) == 1, (
        f"Expected 1 entry after global re-install, " f"got {len(manifest.entries)}"
    )

    entry = manifest.entries[0]
    assert entry.bundle_name == bundle_name
    assert entry.scope == "global"
    # Updated to second install's values
    assert entry.source_registry == registry_b
    assert entry.installed_files == files_b


@given(
    bundle_name=_bundle_name_st,
    workspace_path=_workspace_path_st,
)
def test_same_workspace_local_reinstall_updates_in_place(
    bundle_name: str,
    workspace_path: str,
) -> None:
    """**Validates: Requirements 3.2**

    For all same-workspace local re-installs, calling
    _update_manifest() twice with the same (bundle_name,
    "local", workspace_path) updates the existing entry
    in place — exactly 1 entry, not duplicated.
    """
    manifest = Manifest(entries=[])
    files_a = ["steering/a.md"]
    files_b = ["hooks/b.json"]

    # First local install
    _update_manifest(
        manifest,
        bundle_name=bundle_name,
        source_registry="default",
        scope="local",
        installed_files=files_a,
        workspace_path=workspace_path,
    )
    assert len(manifest.entries) == 1

    # Second local install (same bundle, same workspace)
    _update_manifest(
        manifest,
        bundle_name=bundle_name,
        source_registry="updated",
        scope="local",
        installed_files=files_b,
        workspace_path=workspace_path,
    )

    # Must still be exactly 1 entry (updated in place)
    assert len(manifest.entries) == 1, (
        f"Expected 1 entry after same-workspace re-install, "
        f"got {len(manifest.entries)}"
    )

    entry = manifest.entries[0]
    assert entry.bundle_name == bundle_name
    assert entry.scope == "local"
    assert entry.workspace_path == workspace_path
    # Updated to second install's values
    assert entry.source_registry == "updated"
    assert entry.installed_files == files_b


@given(
    bundle_name=_bundle_name_st,
    ws_a=_workspace_path_st,
    ws_b=_workspace_path_st,
)
def test_global_rm_lookup_ignores_workspace_path(
    bundle_name: str,
    ws_a: str,
    ws_b: str,
) -> None:
    """**Validates: Requirements 3.4**

    For all global entries, lookup by (bundle_name, "global")
    returns the correct entry regardless of any workspace_path
    values present on other entries in the manifest.

    The run_rm() lookup for global scope matches by
    (bundle_name, "global") without workspace_path.
    """
    # Build a manifest with a global entry and local entries
    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name=bundle_name,
                source_registry="default",
                scope="global",
                installed_files=["steering/global.md"],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            ),
            ManifestEntry(
                bundle_name=bundle_name,
                source_registry="default",
                scope="local",
                installed_files=["steering/local_a.md"],
                installed_at="2025-01-02T00:00:00Z",
                updated_at="2025-01-02T00:00:00Z",
                workspace_path=ws_a,
            ),
            ManifestEntry(
                bundle_name="other_bundle",
                source_registry="default",
                scope="local",
                installed_files=["hooks/other.json"],
                installed_at="2025-01-03T00:00:00Z",
                updated_at="2025-01-03T00:00:00Z",
                workspace_path=ws_b,
            ),
        ]
    )

    # Simulate run_rm() global lookup
    scope = "global"
    matches = [
        e for e in manifest.entries if e.bundle_name == bundle_name and e.scope == scope
    ]

    # Must find exactly the global entry
    assert len(matches) == 1, f"Expected 1 global match, got {len(matches)}"
    assert matches[0].scope == "global"
    assert matches[0].bundle_name == bundle_name
    assert matches[0].installed_files == ["steering/global.md"]
