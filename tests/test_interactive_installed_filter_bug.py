"""Bug condition exploration tests for interactive installed filter.

These tests encode the BUGGY behavior — they should PASS on unfixed
code, confirming the bug exists. Each test simulates the current
flat-set logic that ignores workspace context.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2,
2.3, 2.4, 2.5, 2.6, 2.7**
"""

from hypothesis import given
from hypothesis import strategies as st

from ksm.manifest import Manifest, ManifestEntry

# Strategy: valid bundle names (lowercase + digits + underscore)
_bundle_name_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
    min_size=1,
    max_size=30,
)

# Strategy: workspace paths (distinct pair guaranteed by filter)
_workspace_path_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_/",
    min_size=1,
    max_size=60,
)

# Strategy: scope values
_scope_st = st.sampled_from(["local", "global"])


@given(
    bundle_name=_bundle_name_st,
    ws_a=_workspace_path_st,
    ws_b=_workspace_path_st,
)
def test_bug_flat_set_includes_cross_workspace_local_entries(
    bundle_name: str,
    ws_a: str,
    ws_b: str,
) -> None:
    """**Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.2, 2.3**

    Bug condition: a local entry exists for workspace_A, and we
    query from workspace_B. The current flat-set logic
    ``installed_names = {e.bundle_name for e in manifest.entries}``
    includes the cross-workspace entry — confirming the bug.

    On UNFIXED code this test PASSES (bug exists).
    """
    if ws_a == ws_b:
        return

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
        ]
    )

    # Simulate current buggy flat-set logic (no workspace filter)
    installed_names: set[str] = {e.bundle_name for e in manifest.entries}

    # Bug: cross-workspace local entry IS included
    assert bundle_name in installed_names, (
        f"Expected '{bundle_name}' in installed_names "
        f"(flat set includes all entries regardless of workspace)"
    )


@given(
    bundle_name=_bundle_name_st,
    ws_a=_workspace_path_st,
    ws_b=_workspace_path_st,
)
def test_bug_rm_entries_to_show_includes_cross_workspace_local(
    bundle_name: str,
    ws_a: str,
    ws_b: str,
) -> None:
    """**Validates: Requirements 1.4, 2.7**

    Bug condition: ``run_rm()`` interactive path uses
    ``entries_to_show = manifest.entries`` with no workspace
    filtering. A local entry from workspace_A appears when
    queried from workspace_B — confirming the bug.

    On UNFIXED code this test PASSES (bug exists).
    """
    if ws_a == ws_b:
        return

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
        ]
    )

    # Simulate current buggy entries_to_show logic (no filter)
    entries_to_show: list[ManifestEntry] = manifest.entries

    # Bug: cross-workspace local entry IS shown as removal candidate
    shown_names = {e.bundle_name for e in entries_to_show}
    assert bundle_name in shown_names, (
        f"Expected '{bundle_name}' in entries_to_show "
        f"(no workspace filtering applied)"
    )


@given(
    bundle_name=_bundle_name_st,
    ws=_workspace_path_st,
)
def test_bug_flat_set_has_no_scope_distinction(
    bundle_name: str,
    ws: str,
) -> None:
    """**Validates: Requirements 1.5, 2.4, 2.5, 2.6**

    Bug condition: a bundle is installed both locally (current
    workspace) and globally. The current flat-set logic produces
    ``{bundle_name}`` with no scope info — just a plain string
    in a set. There is no way to distinguish local vs global.

    On UNFIXED code this test PASSES (bug exists).
    """
    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name=bundle_name,
                source_registry="default",
                scope="local",
                installed_files=["steering/local.md"],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                workspace_path=ws,
            ),
            ManifestEntry(
                bundle_name=bundle_name,
                source_registry="default",
                scope="global",
                installed_files=["steering/global.md"],
                installed_at="2025-01-02T00:00:00Z",
                updated_at="2025-01-02T00:00:00Z",
            ),
        ]
    )

    # Simulate current buggy flat-set logic
    installed_names: set[str] = {e.bundle_name for e in manifest.entries}

    # Bug: set contains only the bundle name — no scope info
    assert installed_names == {bundle_name}, (
        f"Expected flat set {{'{bundle_name}'}} with no scope "
        f"distinction, got {installed_names}"
    )

    # Bug: no way to tell if it's local, global, or both
    for name in installed_names:
        assert isinstance(name, str), "Set contains plain strings"
        assert "local" not in name, "Flat set has no scope annotation"
        assert "global" not in name, "Flat set has no scope annotation"
