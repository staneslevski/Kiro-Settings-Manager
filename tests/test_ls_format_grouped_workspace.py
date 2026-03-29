"""Tests for workspace path annotations in _format_grouped().

Validates that ``show_all=True`` annotates local entries with
their workspace path, ``show_all=False`` preserves existing
behaviour, and column alignment is maintained.

**Validates: Requirements 2.4, 2.6, 3.6**
"""

from unittest.mock import patch

from ksm.color import _strip_ansi
from ksm.commands.ls import _format_grouped
from ksm.manifest import ManifestEntry

WS_A = "/tmp/project-a"
WS_B = "/tmp/project-b"
UNKNOWN = "(unknown workspace)"


def _entry(
    name: str,
    scope: str = "local",
    source: str = "built-in",
    workspace_path: str | None = WS_A,
) -> ManifestEntry:
    return ManifestEntry(
        bundle_name=name,
        source_registry=source,
        scope=scope,
        installed_files=["skills/f.md"],
        installed_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
        workspace_path=workspace_path,
    )


# ── 5.3.4  show_all=True with local entries ─────────────


def test_show_all_local_entries_have_workspace_annotation() -> None:
    """show_all=True: each local entry row contains its
    workspace path.

    **Validates: Requirements 2.4**
    """
    entries = [
        _entry("alpha", workspace_path=WS_A),
        _entry("beta", workspace_path=WS_B),
    ]
    output = _format_grouped(entries, verbose=False, show_all=True)
    for name, ws in [("alpha", WS_A), ("beta", WS_B)]:
        line = next(ln for ln in output.splitlines() if name in ln)
        assert ws in line, f"Expected '{ws}' on line for '{name}': " f"{line!r}"


# ── 5.3.4  show_all=True with workspace_path=None ───────


def test_show_all_none_workspace_shows_unknown() -> None:
    """show_all=True: entries with workspace_path=None show
    '(unknown workspace)'.

    **Validates: Requirements 2.4, 2.6**
    """
    entries = [_entry("legacy", workspace_path=None)]
    output = _format_grouped(entries, verbose=False, show_all=True)
    line = next(ln for ln in output.splitlines() if "legacy" in ln)
    assert UNKNOWN in line


# ── 5.3.4  show_all=True with global entries ────────────


def test_show_all_global_entries_no_workspace_annotation() -> None:
    """show_all=True: global entries do NOT show workspace
    path annotation.

    **Validates: Requirements 2.4**
    """
    entries = [
        _entry("shared", scope="global", workspace_path=None),
    ]
    output = _format_grouped(entries, verbose=False, show_all=True)
    line = next(ln for ln in output.splitlines() if "shared" in ln)
    assert WS_A not in line
    assert WS_B not in line
    assert UNKNOWN not in line


# ── 5.3.4  show_all=False preservation ──────────────────


def test_show_all_false_no_workspace_annotations() -> None:
    """show_all=False: output does NOT contain workspace
    path annotations (preservation).

    **Validates: Requirements 3.6**
    """
    entries = [
        _entry("alpha", workspace_path=WS_A),
        _entry("beta", workspace_path=WS_B),
        _entry("legacy", workspace_path=None),
    ]
    output = _format_grouped(entries, verbose=False, show_all=False)
    for ln in output.splitlines():
        if "bundles:" in ln:
            continue
        assert WS_A not in ln
        assert WS_B not in ln
        assert UNKNOWN not in ln


# ── 5.3.4  column alignment with workspace column ───────


def test_column_alignment_with_workspace_column() -> None:
    """Column alignment is maintained when workspace path
    column is added.

    **Validates: Requirements 2.4, 3.6**
    """
    entries = [
        _entry("ab", workspace_path=WS_A),
        _entry("much_longer", workspace_path=WS_B),
    ]
    output = _format_grouped(entries, verbose=False, show_all=True)
    bundle_lines = [
        ln for ln in output.splitlines() if ln.startswith("  ") and "bundles:" not in ln
    ]
    assert len(bundle_lines) == 2

    stripped = [_strip_ansi(ln) for ln in bundle_lines]
    # Second column (registry) starts at same position
    positions: list[int] = []
    for line in stripped:
        parts = line.split()
        first_end = line.index(parts[0]) + len(parts[0])
        rest = line[first_end:]
        pos = first_end + len(rest) - len(rest.lstrip())
        positions.append(pos)
    assert positions[0] == positions[1]


# ── 5.3.4  workspace annotation uses muted styling ──────


def test_workspace_annotation_uses_muted_styling() -> None:
    """Workspace path annotation uses muted (dim) ANSI code.

    **Validates: Requirements 2.4**
    """
    entries = [_entry("alpha", workspace_path=WS_A)]
    with patch("ksm.color._color_level", return_value=2):
        output = _format_grouped(entries, verbose=False, show_all=True)
    line = next(ln for ln in output.splitlines() if "alpha" in ln)
    # workspace path wrapped in muted ANSI code \033[2m
    assert f"\033[2m{WS_A}\033[0m" in line


# ── 5.3.4  mixed scopes: only local gets annotation ─────


def test_mixed_scopes_only_local_annotated() -> None:
    """show_all=True with mixed scopes: only local entries
    get workspace annotation, global entries do not.

    **Validates: Requirements 2.4**
    """
    entries = [
        _entry("local_one", scope="local", workspace_path=WS_A),
        _entry(
            "global_one",
            scope="global",
            workspace_path=None,
        ),
    ]
    output = _format_grouped(entries, verbose=False, show_all=True)
    local_line = next(ln for ln in output.splitlines() if "local_one" in ln)
    global_line = next(ln for ln in output.splitlines() if "global_one" in ln)
    assert WS_A in local_line
    assert WS_A not in global_line
    assert UNKNOWN not in global_line
