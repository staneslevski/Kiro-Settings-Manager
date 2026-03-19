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
        # No line should start with this bundle name
        assert not any(ln.startswith(entry.bundle_name) for ln in output_lines)


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
