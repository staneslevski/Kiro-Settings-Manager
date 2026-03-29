"""Bug condition exploration test for legacy entry handling.

Property 4: Bug Condition — Legacy Entries Not Properly
Excluded/Included.

Legacy local entries (``workspace_path=None``, not backfillable)
should be excluded from default ``ksm list`` output but included
in ``--all`` output.

**Validates: Requirements 2.5, 2.6**
"""

import argparse
import re
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
        "show_all": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ── Hypothesis strategies ────────────────────────────────────

_bundle_name_st = st.from_regex(r"[a-z]{2,8}", fullmatch=True)

_valid_workspace_st = st.sampled_from([WORKSPACE_A, WORKSPACE_B])


@st.composite
def _mixed_manifest_st(
    draw: st.DrawFn,
) -> tuple[
    list[ManifestEntry],
    list[str],
    list[str],
]:
    """Generate a manifest with a mix of entries.

    Returns (all_entries, legacy_names, workspace_a_names).
    - legacy entries: local, workspace_path=None
    - workspace_a entries: local, workspace_path=WORKSPACE_A
    """
    legacy_names_list: list[str] = []
    ws_a_names_list: list[str] = []
    all_entries: list[ManifestEntry] = []
    used: set[str] = set()

    # At least 1 legacy entry
    n_legacy = draw(st.integers(min_value=1, max_value=3))
    for _ in range(n_legacy):
        name = draw(_bundle_name_st.filter(lambda n: n not in used))
        used.add(name)
        legacy_names_list.append(name)
        all_entries.append(_make_entry(name, "local", workspace_path=None))

    # At least 1 workspace-A entry
    n_ws_a = draw(st.integers(min_value=1, max_value=3))
    for _ in range(n_ws_a):
        name = draw(_bundle_name_st.filter(lambda n: n not in used))
        used.add(name)
        ws_a_names_list.append(name)
        all_entries.append(_make_entry(name, "local", workspace_path=WORKSPACE_A))

    return all_entries, legacy_names_list, ws_a_names_list


# ── Property 4: Bug Condition ────────────────────────────────
# Legacy Entries Not Properly Excluded/Included
#
# For any manifest with a mix of local entries (some with
# workspace_path=None, some with valid workspace_path),
# run_ls() without --all should EXCLUDE legacy entries
# (workspace_path=None) and run_ls() with --all should
# INCLUDE them.
#
# **Validates: Requirements 2.5, 2.6**


@given(data=_mixed_manifest_st())
def test_property4_legacy_excluded_from_default(
    data: tuple[list[ManifestEntry], list[str], list[str]],
) -> None:
    """Property 4: default list excludes legacy entries.

    Legacy local entries (workspace_path=None) must NOT
    appear in default run_ls() output when called from
    a specific workspace.

    **Validates: Requirements 2.5, 2.6**
    """
    from ksm.commands.ls import run_ls

    all_entries, legacy_names, ws_a_names = data
    manifest = Manifest(entries=all_entries)
    args = _make_ls_args()

    with patch("sys.stdout", new_callable=StringIO) as out:
        run_ls(
            args,
            manifest=manifest,
            workspace_path=WORKSPACE_A,
        )

    output = out.getvalue()

    # Legacy entries must NOT appear in default output
    for name in legacy_names:
        pattern = rf"(?<!\w){re.escape(name)}(?!\w)"
        assert not re.search(pattern, output), (
            f"Bug: legacy entry '{name}' "
            f"(workspace_path=None) leaked into "
            f"default output. Output:\n{output}"
        )

    # Workspace-A entries MUST appear
    for name in ws_a_names:
        pattern = rf"(?<!\w){re.escape(name)}(?!\w)"
        assert re.search(pattern, output), (
            f"Workspace-A entry '{name}' missing "
            f"from default output. Output:\n{output}"
        )


@given(data=_mixed_manifest_st())
def test_property4_legacy_included_in_all(
    data: tuple[list[ManifestEntry], list[str], list[str]],
) -> None:
    """Property 4: --all includes legacy entries.

    Legacy local entries (workspace_path=None) MUST appear
    in run_ls() output when --all flag is set.

    **Validates: Requirements 2.5, 2.6**
    """
    from ksm.commands.ls import run_ls

    all_entries, legacy_names, ws_a_names = data
    manifest = Manifest(entries=all_entries)
    args = _make_ls_args(show_all=True)

    with patch("sys.stdout", new_callable=StringIO) as out:
        run_ls(
            args,
            manifest=manifest,
            workspace_path=WORKSPACE_A,
        )

    output = out.getvalue()

    # ALL entries must appear in --all output
    for name in legacy_names:
        pattern = rf"(?<!\w){re.escape(name)}(?!\w)"
        assert re.search(pattern, output), (
            f"Legacy entry '{name}' missing from " f"--all output. Output:\n{output}"
        )

    for name in ws_a_names:
        pattern = rf"(?<!\w){re.escape(name)}(?!\w)"
        assert re.search(pattern, output), (
            f"Workspace-A entry '{name}' missing "
            f"from --all output. Output:\n{output}"
        )
