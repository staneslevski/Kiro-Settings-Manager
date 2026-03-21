"""Tests for ksm.commands.rm module."""

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, HealthCheck, settings as h_settings
from hypothesis import strategies as st

from ksm.manifest import Manifest, ManifestEntry


def _make_entry(
    name: str = "aws",
    scope: str = "local",
    source: str = "default",
    files: list[str] | None = None,
) -> ManifestEntry:
    return ManifestEntry(
        bundle_name=name,
        source_registry=source,
        scope=scope,
        installed_files=files or ["skills/f.md"],
        installed_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
    )


def _make_args(**kwargs: object) -> argparse.Namespace:
    defaults = {
        "bundle_name": "aws",
        "interactive": False,
        "local": False,
        "global_": False,
        "yes": True,
        "dry_run": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_run_rm_removes_files_and_updates_manifest(
    tmp_path: Path,
) -> None:
    """run_rm removes files and updates manifest."""
    from ksm.commands.rm import run_rm

    target = tmp_path / "workspace" / ".kiro"
    (target / "skills").mkdir(parents=True)
    (target / "skills" / "f.md").write_bytes(b"data")

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    manifest = Manifest(entries=[_make_entry("aws", files=["skills/f.md"])])

    args = _make_args()
    code = run_rm(
        args,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target,
        target_global=tmp_path / "home" / ".kiro",
    )

    assert code == 0
    assert not (target / "skills" / "f.md").exists()
    assert len(manifest.entries) == 0


def test_run_rm_local_scope(tmp_path: Path) -> None:
    """run_rm with -l removes from local .kiro/."""
    from ksm.commands.rm import run_rm

    target_local = tmp_path / "workspace" / ".kiro"
    (target_local / "skills").mkdir(parents=True)
    (target_local / "skills" / "f.md").write_bytes(b"data")

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    manifest = Manifest(
        entries=[_make_entry("aws", scope="local", files=["skills/f.md"])]
    )

    args = _make_args(local=True)
    code = run_rm(
        args,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=tmp_path / "home" / ".kiro",
    )

    assert code == 0
    assert not (target_local / "skills" / "f.md").exists()


def test_run_rm_global_scope(tmp_path: Path) -> None:
    """run_rm with -g removes from global ~/.kiro/."""
    from ksm.commands.rm import run_rm

    target_global = tmp_path / "home" / ".kiro"
    (target_global / "skills").mkdir(parents=True)
    (target_global / "skills" / "f.md").write_bytes(b"data")

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    manifest = Manifest(
        entries=[_make_entry("aws", scope="global", files=["skills/f.md"])]
    )

    args = _make_args(global_=True)
    code = run_rm(
        args,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=tmp_path / "workspace" / ".kiro",
        target_global=target_global,
    )

    assert code == 0
    assert not (target_global / "skills" / "f.md").exists()


def test_run_rm_display_launches_removal_selector(
    tmp_path: Path,
) -> None:
    """run_rm with --display launches removal selector."""
    from ksm.commands.rm import run_rm

    target = tmp_path / "workspace" / ".kiro"
    (target / "skills").mkdir(parents=True)
    (target / "skills" / "f.md").write_bytes(b"data")

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    entry = _make_entry("aws", files=["skills/f.md"])
    manifest = Manifest(entries=[entry])

    args = _make_args(bundle_name=None, interactive=True)

    with patch(
        "ksm.commands.rm.interactive_removal_select",
        return_value=[entry],
    ) as mock_sel:
        code = run_rm(
            args,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target,
            target_global=tmp_path / "home" / ".kiro",
        )

    assert code == 0
    mock_sel.assert_called_once()
    assert not (target / "skills" / "f.md").exists()


def test_run_rm_unknown_bundle_prints_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_rm with unknown bundle prints error and exits 1."""
    from ksm.commands.rm import run_rm

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    manifest = Manifest(entries=[])

    args = _make_args(bundle_name="nonexistent")
    code = run_rm(
        args,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=tmp_path / "workspace" / ".kiro",
        target_global=tmp_path / "home" / ".kiro",
    )

    assert code == 1
    captured = capsys.readouterr()
    assert "nonexistent" in captured.err


def test_run_rm_display_no_bundles_prints_message(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_rm --display with no bundles prints message and exits 0."""
    from ksm.commands.rm import run_rm

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    manifest = Manifest(entries=[])

    args = _make_args(bundle_name=None, interactive=True)
    code = run_rm(
        args,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=tmp_path / "workspace" / ".kiro",
        target_global=tmp_path / "home" / ".kiro",
    )

    assert code == 0
    captured = capsys.readouterr()
    assert "no bundles" in captured.out.lower()


def test_run_rm_display_quit_exits_zero(
    tmp_path: Path,
) -> None:
    """run_rm --display returns 0 when user quits selector."""
    from ksm.commands.rm import run_rm

    manifest = Manifest(entries=[_make_entry("aws", "local", "default")])
    args = _make_args(interactive=True)

    with patch(
        "ksm.commands.rm.interactive_removal_select",
        return_value=None,
    ):
        code = run_rm(
            args,
            manifest=manifest,
            manifest_path=tmp_path / "manifest.json",
            target_local=tmp_path / "local",
            target_global=tmp_path / "global",
        )

    assert code == 0


def test_run_rm_no_bundle_name_prints_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_rm with no bundle_name and no --display prints error."""
    from ksm.commands.rm import run_rm

    manifest = Manifest(entries=[])
    args = _make_args(bundle_name=None)

    code = run_rm(
        args,
        manifest=manifest,
        manifest_path=tmp_path / "manifest.json",
        target_local=tmp_path / "local",
        target_global=tmp_path / "global",
    )

    assert code == 1
    captured = capsys.readouterr()
    assert "no bundle specified" in captured.err.lower()


# --- Property-based tests ---


# Feature: kiro-settings-manager, Property 34: Unknown bundle in rm produces error
@given(
    name=st.from_regex(r"[a-z]{3,8}", fullmatch=True),
)
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_unknown_bundle_rm_error(
    name: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Property 34: Unknown bundle in rm produces error."""
    import tempfile

    from ksm.commands.rm import run_rm

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ksm_dir = base / "ksm"
        ksm_dir.mkdir()

        manifest = Manifest(entries=[])
        args = _make_args(bundle_name=name)
        code = run_rm(
            args,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=base / "local" / ".kiro",
            target_global=base / "global" / ".kiro",
        )

        assert code == 1
        captured = capsys.readouterr()
        assert name in captured.err


# Feature: kiro-settings-manager, Property 35: Rm scope flag determines target directory
@given(
    use_global=st.booleans(),
)
def test_property_rm_scope_flag_determines_target(
    use_global: bool,
) -> None:
    """Property 35: Rm scope flag determines target directory."""
    import tempfile

    from ksm.commands.rm import run_rm

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        target_local = base / "local" / ".kiro"
        target_global = base / "global" / ".kiro"
        ksm_dir = base / "ksm"
        ksm_dir.mkdir()

        scope = "global" if use_global else "local"
        target = target_global if use_global else target_local

        (target / "skills").mkdir(parents=True)
        (target / "skills" / "f.md").write_bytes(b"data")

        manifest = Manifest(
            entries=[_make_entry("b", scope=scope, files=["skills/f.md"])]
        )

        args = _make_args(
            bundle_name="b",
            global_=use_global,
            local=not use_global,
        )
        code = run_rm(
            args,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target_local,
            target_global=target_global,
        )

        assert code == 0
        assert not (target / "skills" / "f.md").exists()
        assert len(manifest.entries) == 0


# Feature: ux-review-fixes, Property 1: Confirmation prompt contains all required
# information (bundle name, scope, file count, all file paths)
@given(
    bundle_name=st.from_regex(r"[a-z]{3,10}", fullmatch=True),
    scope=st.sampled_from(["local", "global"]),
    files=st.lists(
        st.from_regex(r"[a-z]+/[a-z]+\.md", fullmatch=True),
        min_size=1,
        max_size=5,
        unique=True,
    ),
)
def test_property_confirmation_prompt_contains_required_info(
    bundle_name: str,
    scope: str,
    files: list[str],
) -> None:
    """Property 1: Confirmation prompt contains bundle name, scope, file count,
    and all file paths."""
    from ksm.commands.rm import _format_confirmation

    entry = ManifestEntry(
        bundle_name=bundle_name,
        source_registry="default",
        scope=scope,
        installed_files=files,
        installed_at="2025-01-01T00:00:00Z",
        updated_at="2025-01-01T00:00:00Z",
    )

    prompt = _format_confirmation(entry)

    # Must contain bundle name
    assert bundle_name in prompt
    # Must contain scope
    assert scope in prompt
    # Must contain file count
    assert str(len(files)) in prompt
    # Must contain all file paths
    for f in files:
        assert f in prompt


# Feature: ux-review-fixes, Property 2: Non-"y" input aborts removal
# (manifest unchanged)
@given(
    response=st.text(min_size=0, max_size=10).filter(lambda s: s.strip() != "y"),
)
def test_property_non_y_input_aborts_removal(
    response: str,
) -> None:
    """Property 2: Non-"y" input aborts removal, manifest unchanged."""
    import tempfile

    from ksm.commands.rm import run_rm

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        target = base / "workspace" / ".kiro"
        (target / "skills").mkdir(parents=True)
        (target / "skills" / "f.md").write_bytes(b"data")

        ksm_dir = base / "ksm"
        ksm_dir.mkdir(parents=True)

        entry = _make_entry("bundle", scope="local", files=["skills/f.md"])
        manifest = Manifest(entries=[entry])
        original_count = len(manifest.entries)

        args = _make_args(bundle_name="bundle", yes=False)

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("builtins.input", return_value=response),
        ):
            code = run_rm(
                args,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=target,
                target_global=base / "home" / ".kiro",
            )

        assert code == 0
        assert len(manifest.entries) == original_count
        assert (target / "skills" / "f.md").exists()


# Feature: ux-review-fixes, Property 3: Removal result formatting
# (correct counts in output)
@given(
    bundle_name=st.from_regex(r"[a-z]{3,10}", fullmatch=True),
    scope=st.sampled_from(["local", "global"]),
    removed=st.lists(
        st.from_regex(r"[a-z]+/[a-z]+\.md", fullmatch=True),
        min_size=0,
        max_size=5,
        unique=True,
    ),
    skipped=st.lists(
        st.from_regex(r"[a-z]+/[a-z]+\.md", fullmatch=True),
        min_size=0,
        max_size=5,
        unique=True,
    ),
)
def test_property_removal_result_formatting(
    bundle_name: str,
    scope: str,
    removed: list[str],
    skipped: list[str],
) -> None:
    """Property 3: Removal result formatting shows correct counts."""
    from ksm.commands.rm import _format_result
    from ksm.remover import RemovalResult

    result = RemovalResult(removed_files=removed, skipped_files=skipped)
    output = _format_result(bundle_name, scope, result)

    # Must contain bundle name and scope
    assert bundle_name in output
    assert scope in output

    # Must contain correct counts
    if len(removed) > 0:
        assert str(len(removed)) in output
    if len(skipped) > 0:
        assert str(len(skipped)) in output or "missing" in output.lower()


# Feature: ux-review-fixes, Property 36: TTY check blocks prompt when stdin
# is not TTY (rm path)
@given(
    bundle_name=st.from_regex(r"[a-z]{3,10}", fullmatch=True),
)
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_tty_check_blocks_prompt_rm(
    bundle_name: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Property 36: TTY check blocks prompt when stdin is not TTY (rm path)."""
    import tempfile

    from ksm.commands.rm import run_rm

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        target = base / "workspace" / ".kiro"
        (target / "skills").mkdir(parents=True)
        (target / "skills" / "f.md").write_bytes(b"data")

        ksm_dir = base / "ksm"
        ksm_dir.mkdir(parents=True)

        entry = _make_entry(bundle_name, scope="local", files=["skills/f.md"])
        manifest = Manifest(entries=[entry])
        original_count = len(manifest.entries)

        args = _make_args(bundle_name=bundle_name, yes=False)

        with patch("sys.stdin.isatty", return_value=False):
            code = run_rm(
                args,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=target,
                target_global=base / "home" / ".kiro",
            )

        assert code == 1
        assert len(manifest.entries) == original_count
        assert (target / "skills" / "f.md").exists()
        captured = capsys.readouterr()
        assert "terminal" in captured.err.lower()
        assert "--yes" in captured.err


# Feature: ux-review-fixes, Property 15: Dry-run does not modify state (rm path)
@given(
    bundle_name=st.from_regex(r"[a-z]{3,10}", fullmatch=True),
    scope=st.sampled_from(["local", "global"]),
)
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_dry_run_rm_does_not_modify_state(
    bundle_name: str,
    scope: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Feature: ux-review-fixes, Property 15: Dry-run does not modify
    state (rm path)."""
    import tempfile

    from ksm.commands.rm import run_rm

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        target_local = base / "workspace" / ".kiro"
        target_global = base / "home" / ".kiro"
        target = target_global if scope == "global" else target_local

        (target / "skills").mkdir(parents=True)
        (target / "skills" / "f.md").write_bytes(b"data")

        ksm_dir = base / "ksm"
        ksm_dir.mkdir(parents=True)

        entry = _make_entry(bundle_name, scope=scope, files=["skills/f.md"])
        manifest = Manifest(entries=[entry])
        original_count = len(manifest.entries)

        args = _make_args(
            bundle_name=bundle_name,
            global_=(scope == "global"),
            local=(scope == "local"),
            yes=True,
            dry_run=True,
        )

        code = run_rm(
            args,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target_local,
            target_global=target_global,
        )

        assert code == 0
        # File must still exist
        assert (target / "skills" / "f.md").exists()
        # Manifest must be unchanged
        assert len(manifest.entries) == original_count
        # Preview printed to stderr
        captured = capsys.readouterr()
        assert "would remove" in captured.err.lower()
        assert bundle_name in captured.err


def test_run_rm_interactive_confirmation_y(
    tmp_path: Path,
) -> None:
    """run_rm --interactive without --yes prompts and accepts y."""
    from ksm.commands.rm import run_rm

    target = tmp_path / "workspace" / ".kiro"
    (target / "skills").mkdir(parents=True)
    (target / "skills" / "f.md").write_bytes(b"data")

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    entry = _make_entry("aws", files=["skills/f.md"])
    manifest = Manifest(entries=[entry])

    args = _make_args(bundle_name=None, interactive=True, yes=False)

    with (
        patch(
            "ksm.commands.rm.interactive_removal_select",
            return_value=[entry],
        ),
        patch("sys.stdin.isatty", return_value=True),
        patch("builtins.input", return_value="y"),
    ):
        code = run_rm(
            args,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target,
            target_global=tmp_path / "home" / ".kiro",
        )

    assert code == 0
    assert not (target / "skills" / "f.md").exists()


def test_run_rm_interactive_confirmation_n(
    tmp_path: Path,
) -> None:
    """run_rm --interactive without --yes aborts on n."""
    from ksm.commands.rm import run_rm

    target = tmp_path / "workspace" / ".kiro"
    (target / "skills").mkdir(parents=True)
    (target / "skills" / "f.md").write_bytes(b"data")

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    entry = _make_entry("aws", files=["skills/f.md"])
    manifest = Manifest(entries=[entry])

    args = _make_args(bundle_name=None, interactive=True, yes=False)

    with (
        patch(
            "ksm.commands.rm.interactive_removal_select",
            return_value=[entry],
        ),
        patch("sys.stdin.isatty", return_value=True),
        patch("builtins.input", return_value="n"),
    ):
        code = run_rm(
            args,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target,
            target_global=tmp_path / "home" / ".kiro",
        )

    assert code == 0
    assert (target / "skills" / "f.md").exists()


def test_run_rm_interactive_confirmation_eof(
    tmp_path: Path,
) -> None:
    """run_rm --interactive without --yes handles EOFError."""
    from ksm.commands.rm import run_rm

    entry = _make_entry("aws", files=["skills/f.md"])
    manifest = Manifest(entries=[entry])

    args = _make_args(bundle_name=None, interactive=True, yes=False)

    with (
        patch(
            "ksm.commands.rm.interactive_removal_select",
            return_value=[entry],
        ),
        patch("sys.stdin.isatty", return_value=True),
        patch("builtins.input", side_effect=EOFError),
    ):
        code = run_rm(
            args,
            manifest=manifest,
            manifest_path=tmp_path / "manifest.json",
            target_local=tmp_path / "local",
            target_global=tmp_path / "global",
        )

    assert code == 0


def test_run_rm_interactive_tty_check_blocks(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_rm --interactive blocks when stdin is not TTY."""
    from ksm.commands.rm import run_rm

    entry = _make_entry("aws", files=["skills/f.md"])
    manifest = Manifest(entries=[entry])

    args = _make_args(bundle_name=None, interactive=True, yes=False)

    with (
        patch(
            "ksm.commands.rm.interactive_removal_select",
            return_value=[entry],
        ),
        patch("sys.stdin.isatty", return_value=False),
    ):
        code = run_rm(
            args,
            manifest=manifest,
            manifest_path=tmp_path / "manifest.json",
            target_local=tmp_path / "local",
            target_global=tmp_path / "global",
        )

    assert code == 1
    captured = capsys.readouterr()
    assert "--yes" in captured.err


def test_run_rm_interactive_dry_run(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_rm --interactive --dry-run previews without modifying."""
    from ksm.commands.rm import run_rm

    target = tmp_path / "workspace" / ".kiro"
    (target / "skills").mkdir(parents=True)
    (target / "skills" / "f.md").write_bytes(b"data")

    entry = _make_entry("aws", files=["skills/f.md"])
    manifest = Manifest(entries=[entry])

    args = _make_args(bundle_name=None, interactive=True, yes=True, dry_run=True)

    with patch(
        "ksm.commands.rm.interactive_removal_select",
        return_value=[entry],
    ):
        code = run_rm(
            args,
            manifest=manifest,
            manifest_path=tmp_path / "manifest.json",
            target_local=target,
            target_global=tmp_path / "home" / ".kiro",
        )

    assert code == 0
    assert (target / "skills" / "f.md").exists()
    captured = capsys.readouterr()
    assert "would remove" in captured.err.lower()


class TestRmDisplayDeprecation:
    """Tests for --display deprecation and -i handling (Req 5)."""

    def test_display_flag_prints_deprecation_warning(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """--display prints deprecation warning to stderr (Req 5.6)."""
        from ksm.commands.rm import run_rm

        entry = _make_entry("aws", files=["skills/f.md"])
        manifest = Manifest(entries=[entry])

        target = tmp_path / "workspace" / ".kiro"
        (target / "skills").mkdir(parents=True)
        (target / "skills" / "f.md").write_bytes(b"data")

        args = _make_args(
            bundle_name=None,
            interactive=False,
            display=True,
        )

        with patch(
            "ksm.commands.rm.interactive_removal_select",
            return_value=[entry],
        ):
            code = run_rm(
                args,
                manifest=manifest,
                manifest_path=tmp_path / "manifest.json",
                target_local=target,
                target_global=tmp_path / "home" / ".kiro",
            )

        assert code == 0
        captured = capsys.readouterr()
        assert "Deprecated" in captured.err
        assert "--display" in captured.err
        assert "-i/--interactive" in captured.err

    def test_display_flag_treated_as_interactive(
        self,
        tmp_path: Path,
    ) -> None:
        """--display behaves as -i, launching selector (Req 5.2)."""
        from ksm.commands.rm import run_rm

        entry = _make_entry("aws", files=["skills/f.md"])
        manifest = Manifest(entries=[entry])

        target = tmp_path / "workspace" / ".kiro"
        (target / "skills").mkdir(parents=True)
        (target / "skills" / "f.md").write_bytes(b"data")

        args = _make_args(
            bundle_name=None,
            interactive=False,
            display=True,
        )

        with patch(
            "ksm.commands.rm.interactive_removal_select",
            return_value=[entry],
        ) as mock_sel:
            code = run_rm(
                args,
                manifest=manifest,
                manifest_path=tmp_path / "manifest.json",
                target_local=target,
                target_global=tmp_path / "home" / ".kiro",
            )

        assert code == 0
        mock_sel.assert_called_once()

    def test_interactive_launches_selector(
        self,
        tmp_path: Path,
    ) -> None:
        """rm -i launches interactive selector (Req 5.8)."""
        from ksm.commands.rm import run_rm

        entry = _make_entry("aws", files=["skills/f.md"])
        manifest = Manifest(entries=[entry])

        target = tmp_path / "workspace" / ".kiro"
        (target / "skills").mkdir(parents=True)
        (target / "skills" / "f.md").write_bytes(b"data")

        args = _make_args(
            bundle_name=None,
            interactive=True,
        )

        with patch(
            "ksm.commands.rm.interactive_removal_select",
            return_value=[entry],
        ) as mock_sel:
            code = run_rm(
                args,
                manifest=manifest,
                manifest_path=tmp_path / "manifest.json",
                target_local=target,
                target_global=tmp_path / "home" / ".kiro",
            )

        assert code == 0
        mock_sel.assert_called_once()

    def test_interactive_ignored_when_bundle_name_provided(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """-i ignored when bundle_name provided, stderr msg (Req 5.10)."""
        from ksm.commands.rm import run_rm

        entry = _make_entry("aws", files=["skills/f.md"])
        manifest = Manifest(entries=[entry])

        target = tmp_path / "workspace" / ".kiro"
        (target / "skills").mkdir(parents=True)
        (target / "skills" / "f.md").write_bytes(b"data")

        args = _make_args(
            bundle_name="aws",
            interactive=True,
        )

        code = run_rm(
            args,
            manifest=manifest,
            manifest_path=tmp_path / "manifest.json",
            target_local=target,
            target_global=tmp_path / "home" / ".kiro",
        )

        assert code == 0
        captured = capsys.readouterr()
        assert "-i ignored" in captured.err.lower() or (
            "-i" in captured.err and "ignored" in captured.err.lower()
        )

    def test_display_deprecation_includes_versions(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """--display deprecation warning includes version numbers."""
        from ksm.commands.rm import run_rm

        entry = _make_entry("aws", files=["skills/f.md"])
        manifest = Manifest(entries=[entry])

        target = tmp_path / "workspace" / ".kiro"
        (target / "skills").mkdir(parents=True)
        (target / "skills" / "f.md").write_bytes(b"data")

        args = _make_args(
            bundle_name=None,
            interactive=False,
            display=True,
        )

        with patch(
            "ksm.commands.rm.interactive_removal_select",
            return_value=[entry],
        ):
            run_rm(
                args,
                manifest=manifest,
                manifest_path=tmp_path / "manifest.json",
                target_local=target,
                target_global=tmp_path / "home" / ".kiro",
            )

        captured = capsys.readouterr()
        assert "v0.2.0" in captured.err
        assert "v1.0.0" in captured.err


def test_run_rm_eof_aborts(tmp_path: Path) -> None:
    """run_rm non-interactive path handles EOFError."""
    from ksm.commands.rm import run_rm

    target = tmp_path / "workspace" / ".kiro"
    (target / "skills").mkdir(parents=True)
    (target / "skills" / "f.md").write_bytes(b"data")

    entry = _make_entry("aws", files=["skills/f.md"])
    manifest = Manifest(entries=[entry])

    args = _make_args(bundle_name="aws", yes=False)

    with (
        patch("sys.stdin.isatty", return_value=True),
        patch("builtins.input", side_effect=EOFError),
    ):
        code = run_rm(
            args,
            manifest=manifest,
            manifest_path=tmp_path / "manifest.json",
            target_local=target,
            target_global=tmp_path / "home" / ".kiro",
        )

    assert code == 0
    assert (target / "skills" / "f.md").exists()


# --- Tests for stream=sys.stderr in formatter calls (Reqs 1.1-1.3, 2.1-2.3) ---


class TestRmFormatterStreamParam:
    """Verify rm.py passes stream=sys.stderr to formatters."""

    def test_format_error_receives_stream_stderr_no_bundle(
        self,
        tmp_path: Path,
    ) -> None:
        """format_error called with stream=sys.stderr when
        no bundle specified."""
        from ksm.commands.rm import run_rm

        manifest = Manifest(entries=[])
        args = _make_args(bundle_name=None)

        with patch(
            "ksm.commands.rm.format_error",
            wraps=__import__(
                "ksm.errors", fromlist=["format_error"]
            ).format_error,
        ) as mock_fmt:
            run_rm(
                args,
                manifest=manifest,
                manifest_path=tmp_path / "manifest.json",
                target_local=tmp_path / "local",
                target_global=tmp_path / "global",
            )

        mock_fmt.assert_called_once()
        _, kwargs = mock_fmt.call_args
        assert kwargs.get("stream") is sys.stderr

    def test_format_error_receives_stream_stderr_not_installed(
        self,
        tmp_path: Path,
    ) -> None:
        """format_error called with stream=sys.stderr when
        bundle not installed."""
        from ksm.commands.rm import run_rm

        manifest = Manifest(entries=[])
        args = _make_args(bundle_name="nonexistent")

        with patch(
            "ksm.commands.rm.format_error",
            wraps=__import__(
                "ksm.errors", fromlist=["format_error"]
            ).format_error,
        ) as mock_fmt:
            run_rm(
                args,
                manifest=manifest,
                manifest_path=tmp_path / "manifest.json",
                target_local=tmp_path / "local",
                target_global=tmp_path / "global",
            )

        mock_fmt.assert_called_once()
        _, kwargs = mock_fmt.call_args
        assert kwargs.get("stream") is sys.stderr

    def test_format_error_receives_stream_stderr_tty_check(
        self,
        tmp_path: Path,
    ) -> None:
        """format_error called with stream=sys.stderr when
        stdin is not a TTY (confirmation blocked)."""
        from ksm.commands.rm import run_rm

        entry = _make_entry(
            "aws", scope="local", files=["skills/f.md"]
        )
        manifest = Manifest(entries=[entry])
        args = _make_args(
            bundle_name="aws", yes=False
        )

        with (
            patch(
                "sys.stdin.isatty", return_value=False
            ),
            patch(
                "ksm.commands.rm.format_error",
                wraps=__import__(
                    "ksm.errors",
                    fromlist=["format_error"],
                ).format_error,
            ) as mock_fmt,
        ):
            run_rm(
                args,
                manifest=manifest,
                manifest_path=tmp_path / "manifest.json",
                target_local=tmp_path / "local",
                target_global=tmp_path / "global",
            )

        mock_fmt.assert_called_once()
        _, kwargs = mock_fmt.call_args
        assert kwargs.get("stream") is sys.stderr

    def test_format_warning_receives_stream_stderr(
        self,
        tmp_path: Path,
    ) -> None:
        """format_warning called with stream=sys.stderr when
        -i ignored because bundle specified."""
        from ksm.commands.rm import run_rm

        entry = _make_entry(
            "aws", scope="local", files=["skills/f.md"]
        )
        manifest = Manifest(entries=[entry])

        target = tmp_path / "workspace" / ".kiro"
        (target / "skills").mkdir(parents=True)
        (target / "skills" / "f.md").write_bytes(b"data")

        args = _make_args(
            bundle_name="aws", interactive=True
        )

        with patch(
            "ksm.commands.rm.format_warning",
            wraps=__import__(
                "ksm.errors",
                fromlist=["format_warning"],
            ).format_warning,
        ) as mock_fmt:
            run_rm(
                args,
                manifest=manifest,
                manifest_path=tmp_path / "manifest.json",
                target_local=target,
                target_global=tmp_path / "global",
            )

        mock_fmt.assert_called_once()
        _, kwargs = mock_fmt.call_args
        assert kwargs.get("stream") is sys.stderr

    def test_format_deprecation_receives_stream_stderr(
        self,
        tmp_path: Path,
    ) -> None:
        """format_deprecation called with stream=sys.stderr
        for --display deprecation."""
        from ksm.commands.rm import run_rm

        entry = _make_entry(
            "aws", scope="local", files=["skills/f.md"]
        )
        manifest = Manifest(entries=[entry])

        target = tmp_path / "workspace" / ".kiro"
        (target / "skills").mkdir(parents=True)
        (target / "skills" / "f.md").write_bytes(b"data")

        args = _make_args(
            bundle_name=None,
            interactive=False,
            display=True,
        )

        with (
            patch(
                "ksm.commands.rm."
                "interactive_removal_select",
                return_value=[entry],
            ),
            patch(
                "ksm.commands.rm.format_deprecation",
                wraps=__import__(
                    "ksm.errors",
                    fromlist=["format_deprecation"],
                ).format_deprecation,
            ) as mock_fmt,
        ):
            run_rm(
                args,
                manifest=manifest,
                manifest_path=tmp_path / "manifest.json",
                target_local=target,
                target_global=tmp_path / "global",
            )

        assert mock_fmt.call_count >= 1
        _, kwargs = mock_fmt.call_args
        assert kwargs.get("stream") is sys.stderr


# --- Tests for green success prefix in _format_result (Req 3.2, 3.4, 3.5) ---
# Feature: color-and-scope-selection
# **Validates: Requirements 3.2, 3.4, 3.5**


class TestRmGreenSuccessPrefix:
    """Property 13: rm _format_result wraps "Removed" prefix
    in green."""

    _GREEN = "\033[32m"
    _RESET = "\033[0m"

    def test_removed_prefix_green_on_tty(self) -> None:
        """Property 13: _format_result wraps 'Removed' in
        green when stream is a TTY.
        **Validates: Requirements 3.2**"""
        from io import StringIO
        from unittest.mock import MagicMock

        from ksm.commands.rm import _format_result
        from ksm.remover import RemovalResult

        stream = MagicMock(spec=StringIO)
        stream.isatty.return_value = True

        result = RemovalResult(
            removed_files=["skills/f.md"],
            skipped_files=[],
        )

        with patch.dict(
            "os.environ",
            {"TERM": "xterm-256color"},
            clear=True,
        ):
            output = _format_result(
                "aws", "local", result, stream=stream
            )

        assert self._GREEN in output
        assert "Removed" in output
        assert (
            f"{self._GREEN}Removed{self._RESET}"
            in output
        )

    def test_removed_prefix_plain_with_no_color(
        self,
    ) -> None:
        """Property 13: 'Removed' is plain text when
        NO_COLOR is set.
        **Validates: Requirements 3.4**"""
        from io import StringIO
        from unittest.mock import MagicMock

        from ksm.commands.rm import _format_result
        from ksm.remover import RemovalResult

        stream = MagicMock(spec=StringIO)
        stream.isatty.return_value = True

        result = RemovalResult(
            removed_files=["skills/f.md"],
            skipped_files=[],
        )

        with patch.dict(
            "os.environ",
            {"NO_COLOR": "1"},
            clear=False,
        ):
            output = _format_result(
                "aws", "local", result, stream=stream
            )

        assert "\033[" not in output
        assert "Removed" in output

    def test_removed_prefix_plain_non_tty(self) -> None:
        """Property 13: 'Removed' is plain text when stream
        is not a TTY.
        **Validates: Requirements 3.4**"""
        from io import StringIO

        from ksm.commands.rm import _format_result
        from ksm.remover import RemovalResult

        stream = StringIO()

        result = RemovalResult(
            removed_files=["skills/f.md"],
            skipped_files=[],
        )

        output = _format_result(
            "aws", "local", result, stream=stream
        )

        assert "\033[" not in output
        assert "Removed" in output

    def test_removed_prefix_text_always_present(
        self,
    ) -> None:
        """Property 13: 'Removed' text is always present
        regardless of color.
        **Validates: Requirements 3.5**"""
        from ksm.commands.rm import _format_result
        from ksm.remover import RemovalResult

        result = RemovalResult(
            removed_files=["skills/f.md"],
            skipped_files=[],
        )

        output = _format_result("aws", "local", result)
        assert "Removed" in output
        assert "aws" in output
