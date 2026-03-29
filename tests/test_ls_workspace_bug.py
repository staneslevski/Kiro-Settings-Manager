"""Bug condition exploration tests for ksm list workspace scoping.

These tests encode the EXPECTED behavior: run_ls() should only show
local bundles belonging to the current workspace. On UNFIXED code,
these tests FAIL — confirming the bug exists.

**Validates: Requirements 1.1, 1.2, 2.1, 2.2**
"""

import argparse
from io import StringIO
from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st

from ksm.manifest import Manifest, ManifestEntry

WORKSPACE_A = "/tmp/project-a"
WORKSPACE_B = "/tmp/project-b"


def _make_entry(
    name: str,
    scope: str = "local",
    source: str = "default",
    files: list[str] | None = None,
    installed_at: str = "2025-01-01T00:00:00Z",
    updated_at: str = "2025-01-01T00:00:00Z",
    workspace_path: str | None = None,
) -> ManifestEntry:
    """Create a ManifestEntry with defaults."""
    return ManifestEntry(
        bundle_name=name,
        source_registry=source,
        scope=scope,
        installed_files=files or ["skills/f.md"],
        installed_at=installed_at,
        updated_at=updated_at,
        workspace_path=workspace_path,
    )


def _make_ls_args(**kwargs: object) -> argparse.Namespace:
    """Build argparse.Namespace with ls defaults."""
    defaults: dict[str, object] = {
        "scope": None,
        "output_format": "text",
        "verbose": False,
        "quiet": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ── Hypothesis strategies ────────────────────────────────────

_workspace_path_st = st.sampled_from([WORKSPACE_A, WORKSPACE_B, "/tmp/project-c"])

_bundle_name_st = st.from_regex(r"[a-z]{2,8}", fullmatch=True)


# ── Property 1: Bug Condition ────────────────────────────────
# Local Bundles Shown From Other Workspaces
#
# For any manifest containing local entries from multiple
# workspaces, run_ls() called from workspace-a should only
# show local entries belonging to workspace-a.
#
# On UNFIXED code this FAILS because run_ls() shows ALL
# local entries regardless of workspace.
#
# **Validates: Requirements 1.1, 1.2, 2.1, 2.2**


@given(
    ws_a_names=st.lists(_bundle_name_st, min_size=1, max_size=3, unique=True),
    ws_b_names=st.lists(_bundle_name_st, min_size=1, max_size=3, unique=True),
)
def test_property_default_list_excludes_other_workspace_locals(
    ws_a_names: list[str],
    ws_b_names: list[str],
) -> None:
    """Property 1a: default ksm list in workspace-a excludes
    workspace-b local entries.

    Bug condition: run_ls() shows local entries from ALL
    workspaces. Expected: only workspace-a locals shown.

    **Validates: Requirements 1.1, 2.1**
    """
    from ksm.commands.ls import run_ls

    # Ensure no name overlap between workspaces
    ws_b_names = [n for n in ws_b_names if n not in set(ws_a_names)]
    if not ws_b_names:
        return  # skip degenerate case

    entries = [
        _make_entry(name, "local", workspace_path=WORKSPACE_A) for name in ws_a_names
    ] + [_make_entry(name, "local", workspace_path=WORKSPACE_B) for name in ws_b_names]
    manifest = Manifest(entries=entries)
    args = _make_ls_args()

    with patch("sys.stdout", new_callable=StringIO) as out:
        run_ls(args, manifest=manifest, workspace_path=WORKSPACE_A)

    output = out.getvalue()

    # workspace-b local entries must NOT appear
    output_lines = [ln.strip() for ln in output.splitlines()]
    for name in ws_b_names:
        assert not any(
            ln.startswith(name)
            and (len(ln) == len(name) or not ln[len(name)].isalnum())
            for ln in output_lines
        ), (
            f"Bug confirmed: '{name}' from workspace-b "
            f"appears in output when listing from workspace-a"
        )


@given(
    ws_a_names=st.lists(_bundle_name_st, min_size=1, max_size=3, unique=True),
    ws_b_names=st.lists(_bundle_name_st, min_size=1, max_size=3, unique=True),
)
def test_property_scope_local_excludes_other_workspace(
    ws_a_names: list[str],
    ws_b_names: list[str],
) -> None:
    """Property 1b: ksm list --scope local in workspace-a
    excludes workspace-b local entries.

    Bug condition: --scope local shows local entries from ALL
    workspaces. Expected: only workspace-a locals shown.

    **Validates: Requirements 1.2, 2.2**
    """
    from ksm.commands.ls import run_ls

    ws_b_names = [n for n in ws_b_names if n not in set(ws_a_names)]
    if not ws_b_names:
        return

    entries = [
        _make_entry(name, "local", workspace_path=WORKSPACE_A) for name in ws_a_names
    ] + [_make_entry(name, "local", workspace_path=WORKSPACE_B) for name in ws_b_names]
    manifest = Manifest(entries=entries)
    args = _make_ls_args(scope="local")

    with patch("sys.stdout", new_callable=StringIO) as out:
        run_ls(args, manifest=manifest, workspace_path=WORKSPACE_A)

    output = out.getvalue()

    output_lines = [ln.strip() for ln in output.splitlines()]
    for name in ws_b_names:
        assert not any(
            ln.startswith(name)
            and (len(ln) == len(name) or not ln[len(name)].isalnum())
            for ln in output_lines
        ), (
            f"Bug confirmed: '{name}' from workspace-b "
            f"shown in --scope local from workspace-a"
        )
