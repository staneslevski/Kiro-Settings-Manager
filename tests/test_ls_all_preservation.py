"""Preservation property test for --all text output formatting.

Property 3: Preservation — ``--all`` Text Output Retains
Existing Formatting.

When ``show_all=False`` (the default), text output from
``run_ls()`` does NOT contain workspace path annotations on
local entry rows. This confirms that non-``--all`` output is
unchanged by the workspace path annotation feature.

**Validates: Requirements 3.6**
"""

import argparse
from io import StringIO
from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st

from ksm.manifest import Manifest, ManifestEntry

WORKSPACE_A = "/tmp/project-a"
WORKSPACE_B = "/tmp/project-b"

UNKNOWN_WS = "(unknown workspace)"


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


# ── Hypothesis strategies ────────────────────────────

_workspace_path_st = st.sampled_from([WORKSPACE_A, WORKSPACE_B, None])

_bundle_name_st = st.from_regex(r"[a-z]{2,8}", fullmatch=True)


# ── Property 3: Preservation ─────────────────────────
# Non-``--all`` text output does NOT contain workspace
# path annotations on local entry rows.
#
# Observation: ``_format_grouped()`` with the default
# call path (``show_all=False``) does NOT include
# workspace path annotations. Column alignment, scope
# headers, and relative timestamps are unchanged.
#
# **Validates: Requirements 3.6**


@given(
    local_entries=st.lists(
        st.tuples(_bundle_name_st, _workspace_path_st),
        min_size=1,
        max_size=4,
        unique_by=lambda t: t[0],
    ),
)
def test_property3_preservation_no_workspace_annotations(
    local_entries: list[tuple[str, str | None]],
) -> None:
    """Property 3 Preservation: show_all=False text output
    does NOT contain workspace path annotations on local
    entry rows.

    For all manifests with show_all=False, the text output
    must not include workspace path strings or
    '(unknown workspace)' on local entry rows.

    **Validates: Requirements 3.6**
    """
    from ksm.commands.ls import run_ls

    # Build entries — all local, matching workspace_path
    # so they pass the workspace filter
    entries = [
        _make_entry(
            name,
            "local",
            workspace_path=WORKSPACE_A,
        )
        for name, _ in local_entries
    ]
    manifest = Manifest(entries=entries)
    args = _make_ls_args(show_all=False)

    with patch("sys.stdout", new_callable=StringIO) as out:
        run_ls(
            args,
            manifest=manifest,
            workspace_path=WORKSPACE_A,
        )

    output = out.getvalue()

    # Each local entry row must NOT contain workspace
    # path annotations
    for name, _ in local_entries:
        matching = [ln for ln in output.splitlines() if name in ln]
        assert matching, f"Entry '{name}' not found in output"
        entry_line = matching[0]
        assert WORKSPACE_A not in entry_line, (
            f"Preservation violated: local entry "
            f"'{name}' has workspace annotation "
            f"'{WORKSPACE_A}' in non-all output. "
            f"Line: {entry_line!r}"
        )
        assert WORKSPACE_B not in entry_line, (
            f"Preservation violated: local entry "
            f"'{name}' has workspace annotation "
            f"'{WORKSPACE_B}' in non-all output. "
            f"Line: {entry_line!r}"
        )
        assert UNKNOWN_WS not in entry_line, (
            f"Preservation violated: local entry "
            f"'{name}' has '{UNKNOWN_WS}' in "
            f"non-all output. "
            f"Line: {entry_line!r}"
        )
