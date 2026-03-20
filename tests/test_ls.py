"""Tests for ksm.commands.ls module."""

import argparse

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ksm.manifest import Manifest, ManifestEntry


def _make_entry(
    name: str = "aws",
    scope: str = "local",
    source: str = "default",
) -> ManifestEntry:
    """Create a ManifestEntry with defaults."""
    return ManifestEntry(
        bundle_name=name,
        source_registry=source,
        scope=scope,
        installed_files=["skills/f.md"],
        installed_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
    )


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

    args = argparse.Namespace()
    code = run_ls(args, manifest=manifest)

    assert code == 0
    captured = capsys.readouterr()
    assert "aws" in captured.out
    assert "global" in captured.out
    assert "default" in captured.out
    assert "team" in captured.out
    assert "local" in captured.out
    assert "team-configs" in captured.out


def test_ls_empty_manifest_prints_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """ls with empty manifest prints 'no bundles installed' to stderr."""
    from ksm.commands.ls import run_ls

    manifest = Manifest(entries=[])
    args = argparse.Namespace()
    code = run_ls(args, manifest=manifest)

    assert code == 0
    captured = capsys.readouterr()
    assert "no bundles" in captured.err.lower()
    assert captured.out == ""


# --- Property-based tests ---

_entry_strategy = st.builds(
    ManifestEntry,
    bundle_name=st.from_regex(r"[a-z]{1,8}", fullmatch=True),
    source_registry=st.from_regex(r"[a-z]{1,8}", fullmatch=True),
    scope=st.sampled_from(["local", "global"]),
    installed_files=st.just(["f.md"]),
    installed_at=st.just("2025-01-01T00:00:00Z"),
    updated_at=st.just("2025-01-01T00:00:00Z"),
)


# Feature: kiro-settings-manager
# Property 8: ls displays all manifest entries with required fields
@given(
    entries=st.lists(_entry_strategy, min_size=1, max_size=5),
)
def test_property_ls_displays_all_entries(
    entries: list[ManifestEntry],
) -> None:
    """Property 8: ls displays all manifest entries with required fields."""
    from io import StringIO
    from unittest.mock import patch

    from ksm.commands.ls import run_ls

    manifest = Manifest(entries=entries)
    args = argparse.Namespace()

    with patch("sys.stdout", new_callable=StringIO) as mock_out:
        code = run_ls(args, manifest=manifest)

    assert code == 0
    output = mock_out.getvalue()
    for entry in entries:
        assert entry.bundle_name in output
        assert entry.scope in output
        assert entry.source_registry in output


# Feature: ux-review-fixes, Property 37: Informational messages go to
# stderr not stdout
@given(
    entries=st.lists(_entry_strategy, min_size=0, max_size=0),
)
def test_property_ls_empty_message_goes_to_stderr(
    entries: list[ManifestEntry],
) -> None:
    """Feature: ux-review-fixes, Property 37: ls empty-list message
    goes to stderr, not stdout."""
    from io import StringIO
    from unittest.mock import patch

    from ksm.commands.ls import run_ls

    manifest = Manifest(entries=entries)
    args = argparse.Namespace()

    stdout = StringIO()
    stderr = StringIO()

    with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
        code = run_ls(args, manifest=manifest)

    assert code == 0
    # stdout must be empty — no data output
    assert stdout.getvalue() == ""
    # stderr must contain the informational message
    assert "no bundles" in stderr.getvalue().lower()
