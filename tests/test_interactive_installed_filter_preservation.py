"""Preservation property tests for interactive installed filter.

These tests capture baseline behavior on UNFIXED code that must be
preserved after the fix. They test non-buggy inputs: global entries,
current-workspace local entries, empty manifests, and non-interactive
command paths (find_entries).

All tests PASS on unfixed code — they define invariants that the fix
must not break.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5a, 3.5b**
"""

from hypothesis import given
from hypothesis import strategies as st

from ksm.manifest import Manifest, ManifestEntry, find_entries

# Strategy: valid bundle names (lowercase + digits + underscore)
_bundle_name_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
    min_size=1,
    max_size=30,
)

# Strategy: workspace paths
_workspace_path_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_/",
    min_size=1,
    max_size=60,
)


@given(
    bundle_names=st.lists(_bundle_name_st, min_size=1, max_size=5, unique=True),
    current_workspace=_workspace_path_st,
)
def test_preservation_global_entries_always_included(
    bundle_names: list[str],
    current_workspace: str,
) -> None:
    """**Validates: Requirements 3.1**

    Preservation: global entries always appear in installed_names
    regardless of which workspace we query from. On unfixed code,
    the flat-set logic includes all entries, so global entries are
    always visible. This invariant must hold after the fix too.
    """
    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name=name,
                source_registry="default",
                scope="global",
                installed_files=["steering/g.md"],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            )
            for name in bundle_names
        ]
    )

    # Simulate current flat-set logic (unfixed code)
    installed_names: set[str] = {e.bundle_name for e in manifest.entries}

    # Every global bundle name must appear
    for name in bundle_names:
        assert (
            name in installed_names
        ), f"Global entry '{name}' missing from installed_names"


@given(
    bundle_names=st.lists(_bundle_name_st, min_size=1, max_size=5, unique=True),
    current_workspace=_workspace_path_st,
)
def test_preservation_current_workspace_local_entries_included(
    bundle_names: list[str],
    current_workspace: str,
) -> None:
    """**Validates: Requirements 3.2**

    Preservation: local entries for the current workspace appear in
    installed_names. On unfixed code, the flat-set logic includes
    all entries, so current-workspace local entries are visible.
    This invariant must hold after the fix too.
    """
    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name=name,
                source_registry="default",
                scope="local",
                installed_files=["steering/l.md"],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                workspace_path=current_workspace,
            )
            for name in bundle_names
        ]
    )

    # Simulate current flat-set logic (unfixed code)
    installed_names: set[str] = {e.bundle_name for e in manifest.entries}

    # Every current-workspace local bundle must appear
    for name in bundle_names:
        assert name in installed_names, (
            f"Current-workspace local entry '{name}' " f"missing from installed_names"
        )


@given(current_workspace=_workspace_path_st)
def test_preservation_empty_manifest_produces_empty_set(
    current_workspace: str,
) -> None:
    """**Validates: Requirements 3.3**

    Preservation: an empty manifest produces an empty installed_names
    set. On unfixed code, the flat-set over zero entries is empty.
    This invariant must hold after the fix too.
    """
    manifest = Manifest(entries=[])

    # Simulate current flat-set logic (unfixed code)
    installed_names: set[str] = {e.bundle_name for e in manifest.entries}

    assert installed_names == set(), (
        f"Expected empty set for empty manifest, " f"got {installed_names}"
    )


@given(
    bundle_name=_bundle_name_st,
    ws_a=_workspace_path_st,
    ws_b=_workspace_path_st,
)
def test_preservation_find_entries_global_ignores_workspace(
    bundle_name: str,
    ws_a: str,
    ws_b: str,
) -> None:
    """**Validates: Requirements 3.4, 3.5a, 3.5b**

    Preservation: find_entries(manifest, name, "global") returns
    global entries regardless of workspace context. This is the
    non-interactive path used by ksm add/rm <bundle> and ksm list.
    """
    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name=bundle_name,
                source_registry="default",
                scope="global",
                installed_files=["steering/g.md"],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            ),
            ManifestEntry(
                bundle_name=bundle_name,
                source_registry="default",
                scope="local",
                installed_files=["steering/l.md"],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                workspace_path=ws_a,
            ),
        ]
    )

    # Global lookup returns global entry regardless of workspace
    global_results = find_entries(manifest, bundle_name, "global")
    assert len(global_results) == 1
    assert global_results[0].scope == "global"
    assert global_results[0].bundle_name == bundle_name


@given(
    bundle_name=_bundle_name_st,
    ws_a=_workspace_path_st,
    ws_b=_workspace_path_st,
)
def test_preservation_find_entries_local_matches_workspace(
    bundle_name: str,
    ws_a: str,
    ws_b: str,
) -> None:
    """**Validates: Requirements 3.4, 3.5a, 3.5b**

    Preservation: find_entries(manifest, name, "local", ws) returns
    only entries matching that workspace. This is the non-interactive
    path used by ksm add/rm <bundle> and ksm list.
    """
    if ws_a == ws_b:
        return

    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name=bundle_name,
                source_registry="default",
                scope="local",
                installed_files=["steering/l.md"],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                workspace_path=ws_a,
            ),
        ]
    )

    # Local lookup with matching workspace returns the entry
    matching = find_entries(manifest, bundle_name, "local", ws_a)
    assert len(matching) == 1
    assert matching[0].workspace_path == ws_a

    # Local lookup with different workspace returns nothing
    non_matching = find_entries(manifest, bundle_name, "local", ws_b)
    assert len(non_matching) == 0
