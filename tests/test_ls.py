"""Tests for ksm.commands.ls module."""

import argparse
import json
from io import StringIO
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ksm.manifest import Manifest, ManifestEntry


def _make_entry(
    name: str = "aws",
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


# --- Unit tests ---


def test_ls_output_contains_required_fields(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """ls output contains bundle name, scope, and source registry."""
    from ksm.commands.ls import run_ls

    manifest = Manifest(
        entries=[
            _make_entry("aws", "global", "default"),
            _make_entry("team", "local", "team-configs"),
        ]
    )

    args = _make_ls_args()
    code = run_ls(args, manifest=manifest)

    assert code == 0
    captured = capsys.readouterr()
    assert "aws" in captured.out
    assert "global" in captured.out.lower()
    assert "team" in captured.out
    assert "local" in captured.out.lower()


def test_ls_empty_manifest_prints_to_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """ls with empty manifest prints message to stderr."""
    from ksm.commands.ls import run_ls

    manifest = Manifest(entries=[])
    args = _make_ls_args()
    code = run_ls(args, manifest=manifest)

    assert code == 0
    captured = capsys.readouterr()
    assert "no bundles" in captured.err.lower()
    assert captured.out == ""


def test_ls_scope_filter_local(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """ls --scope local shows only local bundles."""
    from ksm.commands.ls import run_ls

    manifest = Manifest(
        entries=[
            _make_entry("aws", "global"),
            _make_entry("team", "local"),
        ]
    )
    args = _make_ls_args(scope="local")
    code = run_ls(args, manifest=manifest)

    assert code == 0
    captured = capsys.readouterr()
    assert "team" in captured.out
    assert "aws" not in captured.out


def test_ls_scope_filter_global(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """ls --scope global shows only global bundles."""
    from ksm.commands.ls import run_ls

    manifest = Manifest(
        entries=[
            _make_entry("aws", "global"),
            _make_entry("team", "local"),
        ]
    )
    args = _make_ls_args(scope="global")
    code = run_ls(args, manifest=manifest)

    assert code == 0
    captured = capsys.readouterr()
    assert "aws" in captured.out
    assert "team" not in captured.out


def test_ls_verbose_shows_files(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """ls --verbose shows installed file paths."""
    from ksm.commands.ls import run_ls

    manifest = Manifest(
        entries=[
            _make_entry(
                "aws",
                files=["skills/cross.md", "steering/iam.md"],
            ),
        ]
    )
    args = _make_ls_args(verbose=True)
    code = run_ls(args, manifest=manifest)

    assert code == 0
    captured = capsys.readouterr()
    assert "skills/cross.md" in captured.out
    assert "steering/iam.md" in captured.out


def test_ls_json_format(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """ls --format json outputs valid JSON to stdout."""
    from ksm.commands.ls import run_ls

    manifest = Manifest(
        entries=[
            _make_entry("aws", "local", "default"),
        ]
    )
    args = _make_ls_args(output_format="json")
    code = run_ls(args, manifest=manifest)

    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["bundle_name"] == "aws"
    assert data[0]["scope"] == "local"
    assert data[0]["source_registry"] == "default"


def test_ls_json_empty_manifest(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """ls --format json with empty manifest outputs empty list."""
    from ksm.commands.ls import run_ls

    manifest = Manifest(entries=[])
    args = _make_ls_args(output_format="json")
    code = run_ls(args, manifest=manifest)

    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data == []


def test_ls_grouped_by_scope(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """ls groups bundles by scope with headers."""
    from ksm.commands.ls import run_ls

    manifest = Manifest(
        entries=[
            _make_entry("aws", "global"),
            _make_entry("team", "local"),
            _make_entry("infra", "global"),
        ]
    )
    args = _make_ls_args()
    code = run_ls(args, manifest=manifest)

    assert code == 0
    captured = capsys.readouterr()
    assert "local" in captured.out.lower()
    assert "global" in captured.out.lower()


# --- Property-based tests ---

_entry_strategy = st.builds(
    ManifestEntry,
    bundle_name=st.from_regex(r"[a-z]{1,8}", fullmatch=True),
    source_registry=st.from_regex(r"[a-z]{1,8}", fullmatch=True),
    scope=st.sampled_from(["local", "global"]),
    installed_files=st.lists(
        st.from_regex(r"[a-z]{1,5}/[a-z]{1,5}\.md", fullmatch=True),
        min_size=1,
        max_size=3,
    ),
    installed_at=st.just("2025-01-01T00:00:00Z"),
    updated_at=st.just("2025-06-15T12:00:00Z"),
)


# Property 7: ls groups by scope and includes metadata
@given(
    entries=st.lists(_entry_strategy, min_size=1, max_size=5),
)
def test_property_ls_groups_by_scope_with_metadata(
    entries: list[ManifestEntry],
) -> None:
    """Property 7: ls groups by scope and includes metadata."""
    from ksm.commands.ls import run_ls

    manifest = Manifest(entries=entries)
    args = _make_ls_args()

    with patch("sys.stdout", new_callable=StringIO) as mock_out:
        code = run_ls(args, manifest=manifest)

    assert code == 0
    output = mock_out.getvalue()

    # Every entry's bundle name must appear in output
    for entry in entries:
        assert entry.bundle_name in output

    # Scope headers must appear for present scopes
    scopes = {e.scope for e in entries}
    for scope in scopes:
        assert scope in output.lower()


# Property 8: ls verbose includes all installed files
@given(
    entries=st.lists(_entry_strategy, min_size=1, max_size=3),
)
def test_property_ls_verbose_includes_files(
    entries: list[ManifestEntry],
) -> None:
    """Property 8: ls verbose includes all installed files."""
    from ksm.commands.ls import run_ls

    manifest = Manifest(entries=entries)
    args = _make_ls_args(verbose=True)

    with patch("sys.stdout", new_callable=StringIO) as mock_out:
        code = run_ls(args, manifest=manifest)

    assert code == 0
    output = mock_out.getvalue()

    for entry in entries:
        for f in entry.installed_files:
            assert f in output


# Property 9: ls scope filter shows only matching scope
@given(
    entries=st.lists(_entry_strategy, min_size=1, max_size=5),
    scope=st.sampled_from(["local", "global"]),
)
def test_property_ls_scope_filter(
    entries: list[ManifestEntry],
    scope: str,
) -> None:
    """Property 9: ls scope filter shows only matching scope."""
    from ksm.commands.ls import run_ls

    manifest = Manifest(entries=entries)
    args = _make_ls_args(scope=scope)

    with patch("sys.stdout", new_callable=StringIO) as mock_out:
        code = run_ls(args, manifest=manifest)

    assert code == 0
    output = mock_out.getvalue()

    # Entries matching scope must appear
    matching = [e for e in entries if e.scope == scope]
    for entry in matching:
        assert entry.bundle_name in output

    # Entries NOT matching scope must NOT appear as bundle
    # line starts. We check that no line starts with the
    # bundle name (after indentation) to avoid substring
    # false positives.
    matching_names = {m.bundle_name for m in matching}
    non_matching = [
        e for e in entries if e.scope != scope and e.bundle_name not in matching_names
    ]
    output_lines = [ln.strip() for ln in output.splitlines()]
    for entry in non_matching:
        # No line should start with this exact bundle name
        # followed by a non-alphanumeric char (space, etc.)
        # to avoid substring false positives like "a" matching "aa"
        name = entry.bundle_name
        assert not any(
            ln.startswith(name)
            and (len(ln) == len(name) or not ln[len(name)].isalnum())
            for ln in output_lines
        )


# Property 10: ls JSON output round-trips
@given(
    entries=st.lists(_entry_strategy, min_size=0, max_size=5),
)
def test_property_ls_json_roundtrip(
    entries: list[ManifestEntry],
) -> None:
    """Property 10: ls JSON output round-trips."""
    from ksm.commands.ls import run_ls

    manifest = Manifest(entries=entries)
    args = _make_ls_args(output_format="json")

    with patch("sys.stdout", new_callable=StringIO) as mock_out:
        code = run_ls(args, manifest=manifest)

    assert code == 0
    data = json.loads(mock_out.getvalue())
    assert isinstance(data, list)
    assert len(data) == len(entries)

    # Each entry must have required fields
    for item in data:
        assert "bundle_name" in item
        assert "scope" in item
        assert "source_registry" in item
        assert "installed_files" in item
        assert "installed_at" in item
        assert "updated_at" in item

    # Names must match
    output_names = sorted(d["bundle_name"] for d in data)
    input_names = sorted(e.bundle_name for e in entries)
    assert output_names == input_names


# --- Unit tests for _format_relative_time ---


def test_format_relative_time_just_now() -> None:
    """Timestamps within 60 seconds show 'just now'."""
    from datetime import datetime, timezone

    from ksm.commands.ls import _format_relative_time

    now = datetime.now(timezone.utc).isoformat()
    result = _format_relative_time(now)
    assert result == "just now"


def test_format_relative_time_minutes() -> None:
    """Timestamps 1-59 minutes ago show minutes."""
    from datetime import datetime, timedelta, timezone

    from ksm.commands.ls import _format_relative_time

    ts = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    result = _format_relative_time(ts)
    assert "minute" in result


def test_format_relative_time_hours() -> None:
    """Timestamps 1-23 hours ago show hours."""
    from datetime import datetime, timedelta, timezone

    from ksm.commands.ls import _format_relative_time

    ts = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    result = _format_relative_time(ts)
    assert "hour" in result


def test_format_relative_time_days() -> None:
    """Timestamps 1-29 days ago show days."""
    from datetime import datetime, timedelta, timezone

    from ksm.commands.ls import _format_relative_time

    ts = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    result = _format_relative_time(ts)
    assert "day" in result


def test_format_relative_time_months() -> None:
    """Timestamps 30-364 days ago show months."""
    from datetime import datetime, timedelta, timezone

    from ksm.commands.ls import _format_relative_time

    ts = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    result = _format_relative_time(ts)
    assert "month" in result


def test_format_relative_time_years() -> None:
    """Timestamps 365+ days ago show years."""
    from datetime import datetime, timedelta, timezone

    from ksm.commands.ls import _format_relative_time

    ts = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
    result = _format_relative_time(ts)
    assert "year" in result


def test_format_relative_time_invalid() -> None:
    """Invalid timestamp returns the original string."""
    from ksm.commands.ls import _format_relative_time

    assert _format_relative_time("not-a-date") == "not-a-date"


def test_format_relative_time_singular_minute() -> None:
    """1 minute ago uses singular form."""
    from datetime import datetime, timedelta, timezone

    from ksm.commands.ls import _format_relative_time

    ts = (datetime.now(timezone.utc) - timedelta(seconds=65)).isoformat()
    result = _format_relative_time(ts)
    assert "1 minute ago" == result


# ── ls color ─────────────────────────────────────────────────


class TestLsColor:
    """Tests for color usage in ls output.

    **Validates: Requirements 5.1, 5.2, 5.3, 5.4**
    """

    def test_scope_header_uses_bold(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 5.3: scope headers use bold."""
        from ksm.commands.ls import run_ls

        manifest = Manifest(entries=[_make_entry("aws", "local")])
        args = _make_ls_args()
        with patch("ksm.color._color_level", return_value=2):
            run_ls(args, manifest=manifest)

        out = capsys.readouterr().out
        assert "\033[1mLocal bundles:\033[0m" in out

    def test_registry_name_and_timestamp_use_dim(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 6.2: registry name and timestamp use muted."""
        from ksm.commands.ls import run_ls

        manifest = Manifest(entries=[_make_entry("aws", "local", "default")])
        args = _make_ls_args()
        with patch("ksm.color._color_level", return_value=2):
            run_ls(args, manifest=manifest)

        out = capsys.readouterr().out
        # Registry name wrapped in muted (no parens)
        assert "\033[2mdefault\033[0m" in out
        # Timestamp also wrapped in muted
        muted_count = out.count("\033[2m")
        assert muted_count >= 2

    def test_no_color_suppresses_ansi(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Req 5.4: NO_COLOR suppresses ANSI in ls output."""
        from ksm.commands.ls import run_ls

        monkeypatch.setenv("NO_COLOR", "1")

        manifest = Manifest(entries=[_make_entry("aws", "local")])
        args = _make_ls_args()
        run_ls(args, manifest=manifest)

        out = capsys.readouterr().out
        assert "\033[" not in out
        assert "aws" in out
        assert "Local bundles:" in out


# ── Visual overhaul tests for _format_grouped ────────────────


class TestFormatGroupedVisualOverhaul:
    """Tests for UX visual overhaul of _format_grouped().

    **Validates: Requirements 6.1-6.7, 16.1**
    """

    def test_bundle_names_use_accent(self) -> None:
        """Req 6.1: bundle names use accent (bright cyan 96)."""
        from ksm.commands.ls import _format_grouped

        entries = [_make_entry("my-bundle", "local", "default")]
        with patch("ksm.color._color_level", return_value=2):
            output = _format_grouped(entries, verbose=False)

        assert "\033[96mmy-bundle\033[0m" in output

    def test_registry_no_parentheses(self) -> None:
        """Req 6.4: registry names have no parentheses."""
        from ksm.commands.ls import _format_grouped

        entries = [_make_entry("aws", "local", "my-registry")]
        with patch("ksm.color._color_level", return_value=2):
            output = _format_grouped(entries, verbose=False)

        assert "(my-registry)" not in output
        assert "my-registry" in output

    def test_registry_uses_muted(self) -> None:
        """Req 6.2: registry names use muted (dim code 2)."""
        from ksm.commands.ls import _format_grouped

        entries = [_make_entry("aws", "local", "default")]
        with patch("ksm.color._color_level", return_value=2):
            output = _format_grouped(entries, verbose=False)

        assert "\033[2mdefault\033[0m" in output

    def test_timestamps_use_muted(self) -> None:
        """Req 6.2: timestamps use muted (dim code 2)."""
        from ksm.commands.ls import _format_grouped

        entries = [_make_entry("aws", "local", "default")]
        with patch("ksm.color._color_level", return_value=2):
            output = _format_grouped(entries, verbose=False)

        # At least 2 muted wraps: registry + timestamp
        assert output.count("\033[2m") >= 2

    def test_column_alignment_consistent(self) -> None:
        """Req 6.3: columns aligned via _align_columns()."""
        from ksm.color import _strip_ansi
        from ksm.commands.ls import _format_grouped

        entries = [
            _make_entry("short", "local", "default"),
            _make_entry("much-longer-name", "local", "reg"),
        ]
        with patch("ksm.color._color_level", return_value=2):
            output = _format_grouped(entries, verbose=False)

        # Extract bundle lines (indented, not headers)
        bundle_lines = [
            ln
            for ln in output.splitlines()
            if ln.startswith("  ") and "bundles:" not in ln
        ]
        assert len(bundle_lines) == 2

        # Registry column should start at the same position
        stripped = [_strip_ansi(ln) for ln in bundle_lines]
        reg_positions = []
        for line in stripped:
            # After the 2-space indent, find where the second
            # column (registry) starts
            parts = line.split()
            # Find position of second token
            first_end = line.index(parts[0]) + len(parts[0])
            rest = line[first_end:]
            reg_start = first_end + len(rest) - len(rest.lstrip())
            reg_positions.append(reg_start)

        assert reg_positions[0] == reg_positions[1]

    def test_bold_scope_headers_with_blank_separator(
        self,
    ) -> None:
        """Req 6.5, 16.1: bold headers, blank line between."""
        from ksm.commands.ls import _format_grouped

        entries = [
            _make_entry("team", "local", "default"),
            _make_entry("shared", "global", "default"),
        ]
        with patch("ksm.color._color_level", return_value=2):
            output = _format_grouped(entries, verbose=False)

        lines = output.splitlines()

        # Bold headers present
        assert "\033[1mLocal bundles:\033[0m" in output
        assert "\033[1mGlobal bundles:\033[0m" in output

        # Local appears before Global
        local_idx = next(i for i, ln in enumerate(lines) if "Local" in ln)
        global_idx = next(i for i, ln in enumerate(lines) if "Global" in ln)
        assert local_idx < global_idx

        # Exactly one blank line separates the groups
        # Find the blank line between local content and global
        blank_found = False
        for i in range(local_idx + 1, global_idx):
            if lines[i] == "":
                blank_found = True
        assert blank_found

    def test_verbose_four_space_indent_muted_paths(
        self,
    ) -> None:
        """Req 6.6: verbose file paths 4-space indented, muted."""
        from ksm.commands.ls import _format_grouped

        files = ["skills/cross.md", "steering/iam.md"]
        entries = [_make_entry("aws", "local", "default", files)]
        with patch("ksm.color._color_level", return_value=2):
            output = _format_grouped(entries, verbose=True)

        lines = output.splitlines()
        file_lines = [ln for ln in lines if "skills/" in ln or "steering/" in ln]
        assert len(file_lines) == 2

        for fl in file_lines:
            # 4-space indent
            assert fl.startswith("    ")
            # Muted wrapping
            assert "\033[2m" in fl

    def test_empty_state_message_to_stderr(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 6.7: empty state prints to stderr, not stdout."""
        from ksm.commands.ls import run_ls

        manifest = Manifest(entries=[])
        args = _make_ls_args()
        code = run_ls(args, manifest=manifest)

        assert code == 0
        captured = capsys.readouterr()
        assert "No bundles currently installed." in captured.err
        assert captured.out == ""

    def test_no_trailing_blank_line(self) -> None:
        """Req 16.3: output has no trailing blank line."""
        from ksm.commands.ls import _format_grouped

        entries = [
            _make_entry("team", "local"),
            _make_entry("shared", "global"),
        ]
        with patch("ksm.color._color_level", return_value=2):
            output = _format_grouped(entries, verbose=False)

        assert not output.endswith("\n\n")
        assert output.rstrip("\n") == output.rstrip()

    def test_single_scope_no_blank_line(self) -> None:
        """Single scope group has no trailing blank line."""
        from ksm.commands.ls import _format_grouped

        entries = [_make_entry("aws", "local")]
        with patch("ksm.color._color_level", return_value=2):
            output = _format_grouped(entries, verbose=False)

        assert not output.endswith("\n")


# ── Property tests for ls visual overhaul ────────────────────


# Feature: ux-visual-overhaul, Property 11: ls output uses
# semantic colors and column alignment
# **Validates: Requirements 6.1-6.4**
@given(
    entries=st.lists(_entry_strategy, min_size=1, max_size=5),
)
def test_property_ls_semantic_colors_and_alignment(
    entries: list[ManifestEntry],
) -> None:
    """Property 11: ls output uses semantic colors and
    column alignment."""
    from ksm.color import _strip_ansi
    from ksm.commands.ls import _format_grouped

    with patch("ksm.color._color_level", return_value=2):
        output = _format_grouped(entries, verbose=False)

    for entry in entries:
        # Req 6.1: bundle names wrapped in accent (96)
        assert f"\033[96m{entry.bundle_name}\033[0m" in output
        # Req 6.2: registry wrapped in muted (2)
        assert f"\033[2m{entry.source_registry}\033[0m" in output
        # Req 6.4: no parentheses around registry
        assert f"({entry.source_registry})" not in output

    # Req 6.2: timestamps also muted — at least 2 muted
    # wraps per entry (registry + timestamp)
    muted_count = output.count("\033[2m")
    assert muted_count >= 2 * len(entries)

    # Req 6.3: columns aligned — check per-scope groups
    for scope in ["local", "global"]:
        scope_entries = [e for e in entries if e.scope == scope]
        if len(scope_entries) < 2:
            continue
        # Extract bundle lines (2-space indented, not headers)
        in_scope = False
        bundle_lines: list[str] = []
        for ln in output.splitlines():
            if f"{scope.capitalize()} bundles:" in ln:
                in_scope = True
                continue
            if in_scope and ln.startswith("  "):
                bundle_lines.append(ln)
            elif in_scope and ln == "":
                break
            elif in_scope and "bundles:" in ln:
                break
        if len(bundle_lines) < 2:
            continue
        stripped = [_strip_ansi(bl) for bl in bundle_lines]
        # Second column (registry) starts at same position
        positions: list[int] = []
        for line in stripped:
            parts = line.split()
            if len(parts) < 2:
                continue
            first_end = line.index(parts[0]) + len(parts[0])
            rest = line[first_end:]
            pos = first_end + len(rest) - len(rest.lstrip())
            positions.append(pos)
        if len(positions) >= 2:
            assert len(set(positions)) == 1


# Feature: ux-visual-overhaul, Property 12: ls output groups
# by scope with bold headers
# **Validates: Requirements 6.5, 16.1**
@given(
    local_entries=st.lists(
        _entry_strategy.filter(lambda e: e.scope == "local"),
        min_size=1,
        max_size=3,
    ),
    global_entries=st.lists(
        _entry_strategy.filter(lambda e: e.scope == "global"),
        min_size=1,
        max_size=3,
    ),
)
def test_property_ls_groups_by_scope_bold_headers(
    local_entries: list[ManifestEntry],
    global_entries: list[ManifestEntry],
) -> None:
    """Property 12: ls output groups by scope with bold
    headers."""
    from ksm.commands.ls import _format_grouped

    entries = local_entries + global_entries
    with patch("ksm.color._color_level", return_value=2):
        output = _format_grouped(entries, verbose=False)

    lines = output.splitlines()

    # Bold headers present
    assert "\033[1mLocal bundles:\033[0m" in output
    assert "\033[1mGlobal bundles:\033[0m" in output

    # Local appears before Global
    local_idx = next(i for i, ln in enumerate(lines) if "Local" in ln)
    global_idx = next(i for i, ln in enumerate(lines) if "Global" in ln)
    assert local_idx < global_idx

    # Exactly one blank line separates the groups
    between = lines[local_idx + 1 : global_idx]
    blank_count = sum(1 for ln in between if ln == "")
    assert blank_count == 1


# Feature: ux-visual-overhaul, Property 13: ls verbose mode
# shows indented muted file paths
# **Validates: Requirements 6.6**
@given(
    entries=st.lists(_entry_strategy, min_size=1, max_size=3),
)
def test_property_ls_verbose_indented_muted_paths(
    entries: list[ManifestEntry],
) -> None:
    """Property 13: ls verbose mode shows indented muted
    file paths."""
    from ksm.commands.ls import _format_grouped

    with patch("ksm.color._color_level", return_value=2):
        output = _format_grouped(entries, verbose=True)

    for entry in entries:
        for f in entry.installed_files:
            # File path must appear in output
            assert f in output
            # Find the line containing this file path
            matching = [ln for ln in output.splitlines() if f in ln]
            assert len(matching) >= 1
            for fl in matching:
                # 4-space indent
                assert fl.startswith("    ")
                # Wrapped in muted ANSI code
                assert "\033[2m" in fl
                assert "\033[0m" in fl
