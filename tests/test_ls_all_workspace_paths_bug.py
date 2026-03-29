"""Bug condition exploration test for --all text output
missing workspace path annotations.

Property 3: Bug Condition — ``--all`` text output does not
show workspace paths for local entries.

``_format_grouped()`` does not accept a ``show_all`` flag and
has no logic to display workspace paths for local entries.
When ``--all`` is active, users cannot tell which workspace
each local bundle belongs to.

**Validates: Requirements 2.4**
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

_workspace_path_st = st.sampled_from([WORKSPACE_A, WORKSPACE_B, None])

_bundle_name_st = st.from_regex(r"[a-z]{2,8}", fullmatch=True)


# ── Property 3: Bug Condition ────────────────────────────────
# --all Text Output Missing Workspace Paths
#
# For any manifest with local entries having workspace_path
# values, run_ls() with show_all=True and output_format="text"
# should annotate each local entry row with its workspace path.
# Entries with workspace_path=None should show
# "(unknown workspace)".
#
# On UNFIXED code this FAILS because _format_grouped() has no
# show_all parameter and no workspace path annotation logic.
#
# **Validates: Requirements 2.4**


@given(
    local_entries=st.lists(
        st.tuples(_bundle_name_st, _workspace_path_st),
        min_size=1,
        max_size=4,
        unique_by=lambda t: t[0],
    ),
)
def test_property3_all_text_output_shows_workspace_paths(
    local_entries: list[tuple[str, str | None]],
) -> None:
    """Property 3: --all text output annotates each local
    entry with its workspace path.

    Bug condition: _format_grouped() does not accept show_all
    and has no logic to display workspace paths.

    Expected: each local entry row in text output contains
    the workspace path, or '(unknown workspace)' when None.

    **Validates: Requirements 2.4**
    """
    from ksm.commands.ls import run_ls

    entries = [
        _make_entry(name, "local", workspace_path=ws_path)
        for name, ws_path in local_entries
    ]
    manifest = Manifest(entries=entries)
    args = _make_ls_args(show_all=True)

    with patch("sys.stdout", new_callable=StringIO) as out:
        run_ls(
            args,
            manifest=manifest,
            workspace_path=WORKSPACE_A,
        )

    output = out.getvalue()

    for name, ws_path in local_entries:
        expected_annotation = ws_path if ws_path is not None else "(unknown workspace)"
        # Find indented entry lines where the bundle name
        # appears as a distinct token (not a substring of
        # another word like "unknown").
        matching_lines = [
            ln
            for ln in output.splitlines()
            if ln.startswith("  ") and re.search(rf"(?<!\w){re.escape(name)}(?!\w)", ln)
        ]
        assert matching_lines, f"Entry '{name}' not found in output"
        entry_line = matching_lines[0]
        assert expected_annotation in entry_line, (
            f"Bug confirmed: local entry '{name}' "
            f"missing workspace annotation "
            f"'{expected_annotation}' in --all "
            f"text output. Line: {entry_line!r}"
        )
