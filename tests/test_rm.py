"""Tests for ksm.commands.rm module."""

import argparse
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
        "display": False,
        "local": False,
        "global_": False,
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

    args = _make_args(bundle_name=None, display=True)

    with patch(
        "ksm.commands.rm.interactive_removal_select",
        return_value=entry,
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

    args = _make_args(bundle_name=None, display=True)
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
    args = _make_args(display=True)

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
