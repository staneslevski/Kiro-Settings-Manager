"""Preservation property tests for ksm list workspace scoping.

These tests capture EXISTING behavior BEFORE implementing the fix.
They MUST PASS on the current unfixed code, confirming the baseline
behavior that must be preserved after the fix is applied.

Properties tested:
- 2a: Global-only manifests show all global bundles with header
- 2b: --scope global shows only global entries, no local names
- 2c: --format json produces valid JSON with all required fields
- 2d: -v (verbose) shows every installed_files path in output
- 2e: Mixed-scope manifests show scope headers for present scopes

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
"""

import argparse
import json
from io import StringIO
from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st

from ksm.manifest import Manifest, ManifestEntry

# ── Helpers ──────────────────────────────────────────────────


def _make_entry(
    name: str,
    scope: str = "local",
    source: str = "default",
    files: list[str] | None = None,
    installed_at: str = "2025-01-01T00:00:00Z",
    updated_at: str = "2025-01-01T00:00:00Z",
) -> ManifestEntry:
    """Create a ManifestEntry with defaults."""
    return ManifestEntry(
        bundle_name=name,
        source_registry=source,
        scope=scope,
        installed_files=files or ["skills/f.md"],
        installed_at=installed_at,
        updated_at=updated_at,
    )


def _make_ls_args(**kwargs: object) -> argparse.Namespace:
    """Build argparse.Namespace with ls defaults."""
    defaults: dict[str, object] = {
        "scope": None,
        "output_format": "text",
        "verbose": False,
        "quiet": False,
        "show_all": True,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ── Hypothesis strategies ────────────────────────────────────

_bundle_name_st = st.from_regex(r"[a-z]{2,8}", fullmatch=True)

_file_path_st = st.from_regex(r"[a-z]{1,5}/[a-z]{1,5}\.md", fullmatch=True)

_global_entry_st = st.builds(
    ManifestEntry,
    bundle_name=_bundle_name_st,
    source_registry=st.from_regex(r"[a-z]{1,8}", fullmatch=True),
    scope=st.just("global"),
    installed_files=st.lists(_file_path_st, min_size=1, max_size=3),
    installed_at=st.just("2025-01-01T00:00:00Z"),
    updated_at=st.just("2025-06-15T12:00:00Z"),
)

_local_entry_st = st.builds(
    ManifestEntry,
    bundle_name=_bundle_name_st,
    source_registry=st.from_regex(r"[a-z]{1,8}", fullmatch=True),
    scope=st.just("local"),
    installed_files=st.lists(_file_path_st, min_size=1, max_size=3),
    installed_at=st.just("2025-01-01T00:00:00Z"),
    updated_at=st.just("2025-06-15T12:00:00Z"),
)

_mixed_entry_st = st.builds(
    ManifestEntry,
    bundle_name=_bundle_name_st,
    source_registry=st.from_regex(r"[a-z]{1,8}", fullmatch=True),
    scope=st.sampled_from(["local", "global"]),
    installed_files=st.lists(_file_path_st, min_size=1, max_size=3),
    installed_at=st.just("2025-01-01T00:00:00Z"),
    updated_at=st.just("2025-06-15T12:00:00Z"),
)


# ── Property 2a ──────────────────────────────────────────────
# For all global-only manifests (no local entries), run_ls()
# output contains every global bundle name and "Global bundles:"
# header.
#
# **Validates: Requirements 3.1**


@given(
    entries=st.lists(_global_entry_st, min_size=1, max_size=5),
)
def test_property_2a_global_only_shows_all_globals(
    entries: list[ManifestEntry],
) -> None:
    """Property 2a: global-only manifests show all global
    bundle names and 'Global bundles:' header.

    **Validates: Requirements 3.1**
    """
    from ksm.commands.ls import run_ls

    manifest = Manifest(entries=entries)
    args = _make_ls_args()

    with patch("sys.stdout", new_callable=StringIO) as out:
        code = run_ls(args, manifest=manifest)

    assert code == 0
    output = out.getvalue()

    # Header must be present
    assert "Global bundles:" in output

    # Every global bundle name must appear
    for entry in entries:
        assert entry.bundle_name in output


# ── Property 2b ──────────────────────────────────────────────
# For all manifests with --scope global, output contains only
# global entries and no local entry names (where names are
# unique across scopes).
#
# **Validates: Requirements 3.2**


@given(
    global_entries=st.lists(
        _global_entry_st,
        min_size=1,
        max_size=3,
        unique_by=lambda e: e.bundle_name,
    ),
    local_entries=st.lists(
        _local_entry_st,
        min_size=1,
        max_size=3,
        unique_by=lambda e: e.bundle_name,
    ),
)
def test_property_2b_scope_global_excludes_local(
    global_entries: list[ManifestEntry],
    local_entries: list[ManifestEntry],
) -> None:
    """Property 2b: --scope global shows only global entries,
    no local entry names appear.

    **Validates: Requirements 3.2**
    """
    from ksm.commands.ls import run_ls

    # Ensure unique names across scopes
    global_names = {e.bundle_name for e in global_entries}
    local_entries = [e for e in local_entries if e.bundle_name not in global_names]
    if not local_entries:
        return  # skip degenerate case

    manifest = Manifest(entries=global_entries + local_entries)
    args = _make_ls_args(scope="global")

    with patch("sys.stdout", new_callable=StringIO) as out:
        code = run_ls(args, manifest=manifest)

    assert code == 0
    output = out.getvalue()

    # All global names must appear
    for entry in global_entries:
        assert entry.bundle_name in output

    # No local-only names should appear
    output_lines = [ln.strip() for ln in output.splitlines()]
    for entry in local_entries:
        name = entry.bundle_name
        assert not any(
            ln.startswith(name)
            and (len(ln) == len(name) or not ln[len(name)].isalnum())
            for ln in output_lines
        ), (f"Local entry '{name}' found in " f"--scope global output")


# ── Property 2c ──────────────────────────────────────────────
# For all manifests with --format json, output is valid JSON
# array where each item has all required fields.
#
# **Validates: Requirements 3.3**


@given(
    entries=st.lists(_mixed_entry_st, min_size=0, max_size=5),
)
def test_property_2c_json_valid_with_required_fields(
    entries: list[ManifestEntry],
) -> None:
    """Property 2c: --format json produces valid JSON array
    with all required fields on each item.

    **Validates: Requirements 3.3**
    """
    from ksm.commands.ls import run_ls

    manifest = Manifest(entries=entries)
    args = _make_ls_args(output_format="json")

    with patch("sys.stdout", new_callable=StringIO) as out:
        code = run_ls(args, manifest=manifest)

    assert code == 0
    data = json.loads(out.getvalue())

    assert isinstance(data, list)
    assert len(data) == len(entries)

    required_fields = {
        "bundle_name",
        "scope",
        "source_registry",
        "installed_files",
        "installed_at",
        "updated_at",
    }
    for item in data:
        assert required_fields.issubset(item.keys()), (
            f"Missing fields: " f"{required_fields - set(item.keys())}"
        )


# ── Property 2d ──────────────────────────────────────────────
# For all manifests with -v, every installed_files path appears
# in output.
#
# **Validates: Requirements 3.4**


@given(
    entries=st.lists(_mixed_entry_st, min_size=1, max_size=3),
)
def test_property_2d_verbose_shows_all_file_paths(
    entries: list[ManifestEntry],
) -> None:
    """Property 2d: verbose mode shows every installed_files
    path in the output.

    **Validates: Requirements 3.4**
    """
    from ksm.commands.ls import run_ls

    manifest = Manifest(entries=entries)
    args = _make_ls_args(verbose=True)

    with patch("sys.stdout", new_callable=StringIO) as out:
        code = run_ls(args, manifest=manifest)

    assert code == 0
    output = out.getvalue()

    for entry in entries:
        for fpath in entry.installed_files:
            assert fpath in output, (
                f"File path '{fpath}' from bundle "
                f"'{entry.bundle_name}' not in verbose output"
            )


# ── Property 2e ──────────────────────────────────────────────
# For all manifests with mixed scopes, text output contains
# scope headers for present scopes.
#
# **Validates: Requirements 3.5, 3.6**


@given(
    local_entries=st.lists(_local_entry_st, min_size=1, max_size=3),
    global_entries=st.lists(_global_entry_st, min_size=1, max_size=3),
)
def test_property_2e_mixed_scopes_have_scope_headers(
    local_entries: list[ManifestEntry],
    global_entries: list[ManifestEntry],
) -> None:
    """Property 2e: mixed-scope manifests show scope headers
    for each present scope.

    **Validates: Requirements 3.5, 3.6**
    """
    from ksm.commands.ls import run_ls

    manifest = Manifest(entries=local_entries + global_entries)
    args = _make_ls_args()

    with patch("sys.stdout", new_callable=StringIO) as out:
        code = run_ls(args, manifest=manifest)

    assert code == 0
    output = out.getvalue()

    # Both scope headers must be present
    assert "Local bundles:" in output, "Missing 'Local bundles:' header"
    assert "Global bundles:" in output, "Missing 'Global bundles:' header"

    # Local header appears before Global header
    local_pos = output.index("Local bundles:")
    global_pos = output.index("Global bundles:")
    assert local_pos < global_pos, "Local header should appear before Global header"
