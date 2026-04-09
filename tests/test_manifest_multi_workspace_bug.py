"""Bug condition exploration tests for multi-workspace manifest overwrite.

These tests encode the EXPECTED behavior for local-scoped manifest
entries across multiple workspaces. They are designed to FAIL on
unfixed code, confirming the bug exists.

**Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.3**
"""

from hypothesis import given
from hypothesis import strategies as st

from ksm.installer import _update_manifest
from ksm.manifest import Manifest, ManifestEntry, find_entries

# Strategy for valid bundle names: lowercase + digits + underscore
_bundle_name_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
    min_size=1,
    max_size=30,
)

# Strategy for workspace paths: distinct pair guaranteed by filter
_workspace_path_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_/",
    min_size=1,
    max_size=60,
)


@given(
    bundle_name=_bundle_name_st,
    ws_a=_workspace_path_st,
    ws_b=_workspace_path_st,
)
def test_update_manifest_preserves_both_workspace_entries(
    bundle_name: str,
    ws_a: str,
    ws_b: str,
) -> None:
    """**Validates: Requirements 2.1**

    Bug condition: scope == "local" AND two calls to
    _update_manifest() with same (bundle_name, scope) but
    different workspace_path values.

    After both calls the manifest MUST contain two separate
    entries — one per workspace — with independent data.
    """
    # Ensure workspaces are distinct
    if ws_a == ws_b:
        return

    manifest = Manifest(entries=[])
    files_a = ["steering/a.md"]
    files_b = ["hooks/b.json"]

    # First install: workspace A
    _update_manifest(
        manifest,
        bundle_name=bundle_name,
        source_registry="default",
        scope="local",
        installed_files=files_a,
        workspace_path=ws_a,
    )

    # Second install: workspace B (same bundle, different workspace)
    _update_manifest(
        manifest,
        bundle_name=bundle_name,
        source_registry="default",
        scope="local",
        installed_files=files_b,
        workspace_path=ws_b,
    )

    # --- Assertions: expected behavior ---

    # Must have two entries (one per workspace)
    assert len(manifest.entries) == 2, (
        f"Expected 2 entries (one per workspace), got " f"{len(manifest.entries)}"
    )

    # Each entry's workspace_path must match its install workspace
    ws_paths = [e.workspace_path for e in manifest.entries]
    assert ws_a in ws_paths, f"Workspace A path '{ws_a}' missing from entries"
    assert ws_b in ws_paths, f"Workspace B path '{ws_b}' missing from entries"

    # Each entry's installed_files must be independent
    entry_a = next(e for e in manifest.entries if e.workspace_path == ws_a)
    entry_b = next(e for e in manifest.entries if e.workspace_path == ws_b)
    assert entry_a.installed_files == files_a
    assert entry_b.installed_files == files_b


@given(
    bundle_name=_bundle_name_st,
    ws_a=_workspace_path_st,
    ws_b=_workspace_path_st,
)
def test_rm_lookup_returns_only_current_workspace_entry(
    bundle_name: str,
    ws_a: str,
    ws_b: str,
) -> None:
    """**Validates: Requirements 2.3**

    When two local entries exist for the same bundle in different
    workspaces, looking up from workspace A using find_entries()
    should return ONLY workspace A's entry.
    """
    if ws_a == ws_b:
        return

    # Manually create a manifest with two local entries
    # (as if _update_manifest worked correctly)
    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name=bundle_name,
                source_registry="default",
                scope="local",
                installed_files=["steering/a.md"],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                workspace_path=ws_a,
            ),
            ManifestEntry(
                bundle_name=bundle_name,
                source_registry="default",
                scope="local",
                installed_files=["hooks/b.json"],
                installed_at="2025-01-02T00:00:00Z",
                updated_at="2025-01-02T00:00:00Z",
                workspace_path=ws_b,
            ),
        ]
    )

    # Use workspace-aware lookup (fixed behavior)
    scope = "local"
    matches = find_entries(manifest, bundle_name, scope, ws_a)

    # Must return only workspace A's entry
    assert len(matches) == 1, (
        f"Expected 1 match for workspace A lookup, " f"got {len(matches)}"
    )
    assert matches[0].workspace_path == ws_a, (
        f"Expected match for workspace '{ws_a}', " f"got '{matches[0].workspace_path}'"
    )
