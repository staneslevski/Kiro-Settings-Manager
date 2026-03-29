"""Unit tests for workspace filtering in run_ls().

Validates that run_ls() correctly filters local entries by
workspace_path, respects --all and --scope flags, and includes
workspace_path in JSON output.

**Validates: Requirements 2.1, 2.2, 2.4, 2.6, 3.1, 3.3**
"""

import argparse
import json
from io import StringIO
from unittest.mock import patch

from ksm.commands.ls import run_ls
from ksm.manifest import Manifest, ManifestEntry

WORKSPACE_A = "/tmp/project-a"
WORKSPACE_B = "/tmp/project-b"


def _make_entry(
    name: str,
    scope: str = "local",
    source: str = "default",
    files: list[str] | None = None,
    workspace_path: str | None = None,
) -> ManifestEntry:
    return ManifestEntry(
        bundle_name=name,
        source_registry=source,
        scope=scope,
        installed_files=files or ["skills/f.md"],
        installed_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        workspace_path=workspace_path,
    )


def _make_ls_args(**kwargs: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "scope": None,
        "output_format": "text",
        "verbose": False,
        "show_all": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ── Default list excludes other workspaces ───────────────


def test_default_list_excludes_local_from_other_workspace() -> None:
    """Default ksm list in workspace-a excludes workspace-b locals.

    **Validates: Requirements 2.1**
    """
    manifest = Manifest(
        entries=[
            _make_entry("alpha", workspace_path=WORKSPACE_A),
            _make_entry("beta", workspace_path=WORKSPACE_B),
        ]
    )
    args = _make_ls_args()

    with patch("sys.stdout", new_callable=StringIO) as out:
        rc = run_ls(
            args,
            manifest=manifest,
            workspace_path=WORKSPACE_A,
        )

    output = out.getvalue()
    assert rc == 0
    assert "alpha" in output
    assert "beta" not in output


# ── Default list includes matching workspace ─────────────


def test_default_list_includes_local_matching_workspace() -> None:
    """Default ksm list shows local entries for current workspace.

    **Validates: Requirements 2.1**
    """
    manifest = Manifest(
        entries=[
            _make_entry("alpha", workspace_path=WORKSPACE_A),
            _make_entry("gamma", workspace_path=WORKSPACE_A),
        ]
    )
    args = _make_ls_args()

    with patch("sys.stdout", new_callable=StringIO) as out:
        rc = run_ls(
            args,
            manifest=manifest,
            workspace_path=WORKSPACE_A,
        )

    output = out.getvalue()
    assert rc == 0
    assert "alpha" in output
    assert "gamma" in output


# ── --scope local only shows current workspace ───────────


def test_scope_local_only_shows_current_workspace() -> None:
    """--scope local restricts to current workspace's locals.

    **Validates: Requirements 2.2**
    """
    manifest = Manifest(
        entries=[
            _make_entry("mine", workspace_path=WORKSPACE_A),
            _make_entry("theirs", workspace_path=WORKSPACE_B),
            _make_entry("shared", scope="global", workspace_path=None),
        ]
    )
    args = _make_ls_args(scope="local")

    with patch("sys.stdout", new_callable=StringIO) as out:
        rc = run_ls(
            args,
            manifest=manifest,
            workspace_path=WORKSPACE_A,
        )

    output = out.getvalue()
    assert rc == 0
    assert "mine" in output
    assert "theirs" not in output
    assert "shared" not in output


# ── --all shows local entries from all workspaces ────────


def test_all_flag_shows_locals_from_all_workspaces() -> None:
    """--all bypasses workspace filtering for local entries.

    **Validates: Requirements 2.4**
    """
    manifest = Manifest(
        entries=[
            _make_entry("alpha", workspace_path=WORKSPACE_A),
            _make_entry("beta", workspace_path=WORKSPACE_B),
        ]
    )
    args = _make_ls_args(show_all=True)

    with patch("sys.stdout", new_callable=StringIO) as out:
        rc = run_ls(
            args,
            manifest=manifest,
            workspace_path=WORKSPACE_A,
        )

    output = out.getvalue()
    assert rc == 0
    assert "alpha" in output
    assert "beta" in output


# ── Global entries always shown ──────────────────────────


def test_global_entries_always_shown() -> None:
    """Global entries appear regardless of workspace context.

    **Validates: Requirements 3.1**
    """
    manifest = Manifest(
        entries=[
            _make_entry("aws", scope="global", workspace_path=None),
            _make_entry("local_b", workspace_path=WORKSPACE_B),
        ]
    )
    args = _make_ls_args()

    with patch("sys.stdout", new_callable=StringIO) as out:
        rc = run_ls(
            args,
            manifest=manifest,
            workspace_path=WORKSPACE_A,
        )

    output = out.getvalue()
    assert rc == 0
    assert "aws" in output
    assert "local_b" not in output


# ── Entries with workspace_path=None excluded ────────────


def test_local_with_none_workspace_excluded_from_default() -> None:
    """Local entries with workspace_path=None are excluded from
    default list (they can't match any workspace).

    **Validates: Requirements 2.6**
    """
    manifest = Manifest(
        entries=[
            _make_entry("legacy", workspace_path=None),
            _make_entry("current", workspace_path=WORKSPACE_A),
        ]
    )
    args = _make_ls_args()

    with patch("sys.stdout", new_callable=StringIO) as out:
        rc = run_ls(
            args,
            manifest=manifest,
            workspace_path=WORKSPACE_A,
        )

    output = out.getvalue()
    assert rc == 0
    assert "current" in output
    assert "legacy" not in output


# ── JSON output includes workspace_path ──────────────────


def test_json_output_includes_workspace_path() -> None:
    """JSON output includes workspace_path for local entries.

    **Validates: Requirements 3.3**
    """
    manifest = Manifest(
        entries=[
            _make_entry("alpha", workspace_path=WORKSPACE_A),
            _make_entry("glob", scope="global", workspace_path=None),
        ]
    )
    args = _make_ls_args(output_format="json")

    with patch("sys.stdout", new_callable=StringIO) as out:
        rc = run_ls(
            args,
            manifest=manifest,
            workspace_path=WORKSPACE_A,
        )

    assert rc == 0
    data = json.loads(out.getvalue())
    assert isinstance(data, list)

    local_entry = next(e for e in data if e["bundle_name"] == "alpha")
    assert local_entry["workspace_path"] == WORKSPACE_A

    global_entry = next(e for e in data if e["bundle_name"] == "glob")
    assert "workspace_path" not in global_entry
