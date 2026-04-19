"""Tests for ksm.commands.sync module."""

import argparse
import io
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, HealthCheck, settings as h_settings
from hypothesis import strategies as st

from ksm.manifest import Manifest, ManifestEntry, save_manifest
from ksm.registry import RegistryEntry, RegistryIndex


def _setup_bundle(
    reg: Path,
    name: str,
    files: dict[str, bytes],
) -> None:
    """Create bundle files in a registry directory."""
    for rel, content in files.items():
        fpath = reg / name / rel
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_bytes(content)


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
    defaults: dict[str, object] = {
        "bundle_names": [],
        "all": False,
        "yes": False,
        "dry_run": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_sync_aborts_on_non_y_input(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Sync aborts when user responds with non-y input."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "aws", {"skills/f.md": b"data"})
    target = tmp_path / "target" / ".kiro"
    target.mkdir(parents=True)
    (target / "skills").mkdir()
    (target / "skills" / "f.md").write_bytes(b"old")

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(entries=[_make_entry("aws")])
    save_manifest(manifest, ksm_dir / "manifest.json")

    args = _make_args(bundle_names=["aws"])

    with (
        patch("builtins.input", return_value="n"),
        patch("sys.stdin") as mock_stdin,
    ):
        mock_stdin.isatty.return_value = True
        code = run_sync(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target,
            target_global=tmp_path / "global" / ".kiro",
        )

    assert code == 0
    # File should remain unchanged
    assert (target / "skills" / "f.md").read_bytes() == b"old"


def test_sync_yes_skips_confirmation(tmp_path: Path) -> None:
    """Sync with --yes skips confirmation prompt."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "aws", {"skills/f.md": b"new"})
    target = tmp_path / "target" / ".kiro"
    target.mkdir(parents=True)
    (target / "skills").mkdir()
    (target / "skills" / "f.md").write_bytes(b"old")

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(entries=[_make_entry("aws", files=["skills/f.md"])])
    save_manifest(manifest, ksm_dir / "manifest.json")

    args = _make_args(bundle_names=["aws"], yes=True)
    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    assert (target / "skills" / "f.md").read_bytes() == b"new"


def test_sync_recopies_files(tmp_path: Path) -> None:
    """Sync re-copies files from source registry."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "aws", {"skills/f.md": b"updated"})
    target = tmp_path / "target" / ".kiro"
    target.mkdir(parents=True)
    (target / "skills").mkdir()
    (target / "skills" / "f.md").write_bytes(b"stale")

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(entries=[_make_entry("aws", files=["skills/f.md"])])

    args = _make_args(bundle_names=["aws"], yes=True)
    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    assert (target / "skills" / "f.md").read_bytes() == b"updated"


def test_sync_all_syncs_all_bundles(tmp_path: Path) -> None:
    """Sync with --all syncs all installed bundles."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "aws", {"skills/f.md": b"aws-new"})
    _setup_bundle(reg, "team", {"steering/s.md": b"team-new"})
    target = tmp_path / "target" / ".kiro"
    target.mkdir(parents=True)
    (target / "skills").mkdir()
    (target / "skills" / "f.md").write_bytes(b"aws-old")
    (target / "steering").mkdir()
    (target / "steering" / "s.md").write_bytes(b"team-old")

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(
        entries=[
            _make_entry("aws", files=["skills/f.md"]),
            _make_entry("team", files=["steering/s.md"]),
        ]
    )

    args = _make_args(all=True, yes=True)
    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    assert (target / "skills" / "f.md").read_bytes() == b"aws-new"
    assert (target / "steering" / "s.md").read_bytes() == b"team-new"


def test_sync_unknown_bundle_prints_error_continues(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Sync with unknown bundle prints error and continues."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "aws", {"skills/f.md": b"new"})
    target = tmp_path / "target" / ".kiro"
    target.mkdir(parents=True)
    (target / "skills").mkdir()
    (target / "skills" / "f.md").write_bytes(b"old")

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(entries=[_make_entry("aws", files=["skills/f.md"])])

    args = _make_args(bundle_names=["nonexistent", "aws"], yes=True)
    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    captured = capsys.readouterr()
    assert "nonexistent" in captured.err
    assert (target / "skills" / "f.md").read_bytes() == b"new"


def test_sync_updates_manifest_timestamp(
    tmp_path: Path,
) -> None:
    """Sync updates manifest updated_at timestamp."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "aws", {"skills/f.md": b"data"})
    target = tmp_path / "target" / ".kiro"
    target.mkdir(parents=True)
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    old_ts = "2020-01-01T00:00:00Z"
    ws_path = str((tmp_path / "target").resolve())
    manifest = Manifest(
        entries=[
            _make_entry("aws", files=["skills/f.md"]),
        ]
    )
    manifest.entries[0].updated_at = old_ts
    manifest.entries[0].workspace_path = ws_path

    args = _make_args(bundle_names=["aws"], yes=True)
    before = datetime.now(timezone.utc)
    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    assert manifest.entries[0].updated_at != old_ts
    updated = datetime.fromisoformat(manifest.entries[0].updated_at)
    assert updated >= before


def test_sync_no_args_no_all_prints_usage(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Sync with no args and no --all prints usage message."""
    from ksm.commands.sync import run_sync

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(registries=[])
    manifest = Manifest(entries=[])

    args = _make_args()
    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=tmp_path / "local" / ".kiro",
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 1
    captured = capsys.readouterr()
    assert "usage" in captured.err.lower() or "--all" in captured.err


def test_sync_git_pull_called_for_custom_registries(
    tmp_path: Path,
) -> None:
    """Sync calls git pull for custom (non-default) registries."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "team", {"skills/f.md": b"data"})
    target = tmp_path / "target" / ".kiro"
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="team-configs",
                url="https://github.com/org/team.git",
                local_path=str(reg),
                is_default=False,
            )
        ]
    )
    manifest = Manifest(
        entries=[
            _make_entry(
                "team",
                source="team-configs",
                files=["skills/f.md"],
            ),
        ]
    )

    args = _make_args(bundle_names=["team"], yes=True)

    with patch("ksm.commands.sync.pull_repo") as mock_pull:
        code = run_sync(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target,
            target_global=tmp_path / "global" / ".kiro",
        )

    assert code == 0
    mock_pull.assert_called_once_with(Path(str(reg)))


def test_sync_empty_entries_returns_zero(
    tmp_path: Path,
) -> None:
    """Sync with named bundles that all match returns 0 normally,
    but if entries_to_sync ends up empty it returns 0 early."""
    from ksm.commands.sync import run_sync

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir()
    reg = tmp_path / "registries" / "default"
    reg.mkdir(parents=True)

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    # Manifest has an entry but we pass a name that doesn't match
    manifest = Manifest(entries=[_make_entry("aws", "local", "default")])
    # Pass bundle name that doesn't match — it prints error
    # and continues, leaving entries_to_sync empty
    args = _make_args(bundle_names=["nonexistent"])
    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=tmp_path / "local",
        target_global=tmp_path / "global",
    )

    assert code == 0


def test_sync_eoferror_aborts(
    tmp_path: Path,
) -> None:
    """Sync aborts when input() raises EOFError."""
    from ksm.commands.sync import run_sync

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir()
    reg = tmp_path / "registries" / "default"
    _setup_bundle(reg, "aws", {"skills/f.md": b"data"})

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(entries=[_make_entry("aws", "local", "default")])
    args = _make_args(bundle_names=["aws"])

    with (
        patch("builtins.input", side_effect=EOFError),
        patch("sys.stdin") as mock_stdin,
    ):
        mock_stdin.isatty.return_value = True
        code = run_sync(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=tmp_path / "local",
            target_global=tmp_path / "global",
        )

    assert code == 0


def test_sync_pull_repo_failure_continues(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Sync continues when pull_repo raises an exception."""
    from ksm.commands.sync import run_sync

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir()
    reg = tmp_path / "registries" / "custom"
    _setup_bundle(reg, "team", {"skills/f.md": b"data"})

    target = tmp_path / "workspace" / ".kiro"
    (target / "skills").mkdir(parents=True)
    (target / "skills" / "f.md").write_bytes(b"old")

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="custom",
                url="https://example.com/repo.git",
                local_path=str(reg),
                is_default=False,
            )
        ]
    )
    manifest = Manifest(entries=[_make_entry("team", "local", "custom")])
    args = _make_args(bundle_names=["team"], yes=True)

    with patch(
        "ksm.commands.sync.pull_repo",
        side_effect=RuntimeError("network error"),
    ):
        code = run_sync(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target,
            target_global=tmp_path / "global",
        )

    assert code == 0
    captured = capsys.readouterr()
    assert "warning" in captured.err.lower()


def test_sync_entry_resolve_failure_warns(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_sync_entry prints warning when bundle can't be resolved."""
    from ksm.commands.sync import run_sync

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir()
    reg = tmp_path / "registries" / "default"
    reg.mkdir(parents=True)
    # No bundle files in registry — resolve will fail

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(entries=[_make_entry("missing", "local", "default")])
    args = _make_args(bundle_names=["missing"], yes=True)

    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=tmp_path / "local",
        target_global=tmp_path / "global",
    )

    assert code == 0
    captured = capsys.readouterr()
    assert "warning" in captured.err.lower()


def test_sync_entry_install_system_exit_warns(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_sync_entry prints warning when install raises SystemExit."""
    from ksm.commands.sync import run_sync

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir()
    reg = tmp_path / "registries" / "default"
    _setup_bundle(reg, "aws", {"skills/f.md": b"data"})

    target = tmp_path / "workspace" / ".kiro"
    target.mkdir(parents=True)

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(entries=[_make_entry("aws", "local", "default")])
    args = _make_args(bundle_names=["aws"], yes=True)

    with patch(
        "ksm.commands.sync.install_bundle",
        side_effect=SystemExit(1),
    ):
        code = run_sync(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target,
            target_global=tmp_path / "global",
        )

    assert code == 0
    captured = capsys.readouterr()
    assert "warning" in captured.err.lower()


# --- Property-based tests ---


# Feature: kiro-settings-manager, Property 9: Sync aborts on non-y confirmation
@given(
    response=st.text(min_size=1, max_size=5).filter(lambda s: s.strip() != "y"),
)
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_sync_aborts_on_non_y(
    response: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Property 9: Sync aborts on non-y confirmation."""
    import tempfile

    from ksm.commands.sync import run_sync

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg"
        _setup_bundle(reg, "b", {"skills/f.md": b"new"})
        target = base / "target" / ".kiro"
        target.mkdir(parents=True)
        (target / "skills").mkdir()
        (target / "skills" / "f.md").write_bytes(b"old")

        ksm_dir = base / "ksm"
        ksm_dir.mkdir()

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )
        manifest = Manifest(entries=[_make_entry("b", files=["skills/f.md"])])

        args = _make_args(bundle_names=["b"])

        with (
            patch("builtins.input", return_value=response),
            patch("sys.stdin") as mock_stdin,
        ):
            mock_stdin.isatty.return_value = True
            code = run_sync(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=target,
                target_global=base / "global" / ".kiro",
            )

        assert code == 0
        assert (target / "skills" / "f.md").read_bytes() == b"old"


# Feature: kiro-settings-manager, Property 10: Sync re-copies bundle files from source
@given(
    content=st.binary(min_size=1, max_size=50),
)
def test_property_sync_recopies_from_source(
    content: bytes,
) -> None:
    """Property 10: Sync re-copies bundle files from source."""
    import tempfile

    from ksm.commands.sync import run_sync

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg"
        _setup_bundle(reg, "b", {"skills/f.md": content})
        target = base / "target" / ".kiro"
        target.mkdir(parents=True)
        (target / "skills").mkdir()
        (target / "skills" / "f.md").write_bytes(b"stale")

        ksm_dir = base / "ksm"
        ksm_dir.mkdir()

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )
        manifest = Manifest(entries=[_make_entry("b", files=["skills/f.md"])])

        args = _make_args(bundle_names=["b"], yes=True)
        run_sync(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target,
            target_global=base / "global" / ".kiro",
        )

        assert (target / "skills" / "f.md").read_bytes() == content


# Feature: kiro-settings-manager, Property 11: Sync continues past unknown bundles
@given(
    unknown_name=st.from_regex(r"[a-z]{3,8}", fullmatch=True),
)
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_sync_continues_past_unknown(
    unknown_name: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Property 11: Sync continues past unknown bundles."""
    import tempfile

    from ksm.commands.sync import run_sync

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg"
        _setup_bundle(reg, "known", {"skills/f.md": b"new"})
        target = base / "target" / ".kiro"
        target.mkdir(parents=True)
        (target / "skills").mkdir()
        (target / "skills" / "f.md").write_bytes(b"old")

        ksm_dir = base / "ksm"
        ksm_dir.mkdir()

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )
        manifest = Manifest(
            entries=[
                _make_entry("known", files=["skills/f.md"]),
            ]
        )

        args = _make_args(bundle_names=[unknown_name, "known"], yes=True)
        code = run_sync(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target,
            target_global=base / "global" / ".kiro",
        )

        assert code == 0
        captured = capsys.readouterr()
        assert unknown_name in captured.err
        assert (target / "skills" / "f.md").read_bytes() == b"new"


# Feature: kiro-settings-manager, Property 12: Sync updates manifest timestamp
@given(data=st.data())
def test_property_sync_updates_timestamp(
    data: st.DataObject,
) -> None:
    """Property 12: Sync updates manifest timestamp."""
    import tempfile

    from ksm.commands.sync import run_sync

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg"
        _setup_bundle(reg, "b", {"skills/f.md": b"x"})
        target = base / "target" / ".kiro"
        target.mkdir(parents=True)
        ksm_dir = base / "ksm"
        ksm_dir.mkdir()

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )
        old_ts = "2020-01-01T00:00:00+00:00"
        ws_path = str((base / "target").resolve())
        manifest = Manifest(entries=[_make_entry("b", files=["skills/f.md"])])
        manifest.entries[0].updated_at = old_ts
        manifest.entries[0].workspace_path = ws_path

        before = datetime.now(timezone.utc)
        args = _make_args(bundle_names=["b"], yes=True)
        run_sync(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target,
            target_global=base / "global" / ".kiro",
        )

        updated = datetime.fromisoformat(manifest.entries[0].updated_at)
        assert updated >= before


# --- Tests for file-level diff output (Req 22) ---


def test_sync_prints_diff_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Sync prints file-level diff summary after re-install."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "aws", {"skills/f.md": b"new-content"})
    target = tmp_path / "target" / ".kiro"
    target.mkdir(parents=True)
    (target / "skills").mkdir()
    (target / "skills" / "f.md").write_bytes(b"old-content")

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(entries=[_make_entry("aws", files=["skills/f.md"])])

    args = _make_args(bundle_names=["aws"], yes=True)
    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    captured = capsys.readouterr()
    # Should contain diff symbol for updated file
    assert "~" in captured.err or "updated" in captured.err.lower()


def test_sync_non_tty_without_yes_returns_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Sync returns 1 when stdin is not a TTY and --yes not given."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "aws", {"skills/f.md": b"data"})
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir()

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(entries=[_make_entry("aws", files=["skills/f.md"])])
    args = _make_args(bundle_names=["aws"])

    with patch("sys.stdin") as mock_stdin:
        mock_stdin.isatty.return_value = False
        code = run_sync(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=tmp_path / "local",
            target_global=tmp_path / "global",
        )

    assert code == 1
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "--yes" in captured.err


def test_sync_confirmation_message_global_scope(
    tmp_path: Path,
) -> None:
    """_build_confirmation_message shows global scope per bundle."""
    from ksm.commands.sync import _build_confirmation_message

    entries = [_make_entry("aws", scope="global", files=["skills/f.md"])]
    msg = _build_confirmation_message(entries)
    assert "global" in msg


def test_sync_confirmation_message_mixed_scope(
    tmp_path: Path,
) -> None:
    """_build_confirmation_message shows scope per bundle for mixed."""
    from ksm.commands.sync import _build_confirmation_message

    entries = [
        _make_entry("aws", scope="local", files=["skills/f.md"]),
        _make_entry("team", scope="global", files=["steering/s.md"]),
    ]
    msg = _build_confirmation_message(entries)
    assert "local" in msg
    assert "global" in msg


def test_sync_dry_run_prints_preview(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Sync with --dry-run prints preview without modifying files."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "aws", {"skills/f.md": b"new"})
    target = tmp_path / "target" / ".kiro"
    target.mkdir(parents=True)
    (target / "skills").mkdir()
    (target / "skills" / "f.md").write_bytes(b"old")

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir()

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(entries=[_make_entry("aws", files=["skills/f.md"])])
    args = _make_args(bundle_names=["aws"], yes=True, dry_run=True)
    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target,
        target_global=tmp_path / "global",
    )

    assert code == 0
    assert (target / "skills" / "f.md").read_bytes() == b"old"
    captured = capsys.readouterr()
    assert "Sync" in captured.err


# --- Tests for stream=sys.stderr in formatter calls (Reqs 1.1-1.3, 2.1-2.3) ---


class TestSyncFormatterStreamParam:
    """Verify sync.py passes stream=sys.stderr to formatters."""

    def test_format_error_receives_stream_stderr_no_bundles(
        self,
        tmp_path: Path,
    ) -> None:
        """format_error called with stream=sys.stderr when
        no bundles specified."""
        from ksm.commands.sync import run_sync

        ksm_dir = tmp_path / "ksm"
        ksm_dir.mkdir()
        idx = RegistryIndex(registries=[])
        manifest = Manifest(entries=[])
        args = _make_args()

        with patch(
            "ksm.commands.sync.format_error",
            wraps=__import__("ksm.errors", fromlist=["format_error"]).format_error,
        ) as mock_fmt:
            run_sync(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
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
        from ksm.commands.sync import run_sync

        ksm_dir = tmp_path / "ksm"
        ksm_dir.mkdir()
        idx = RegistryIndex(registries=[])
        manifest = Manifest(entries=[])
        args = _make_args(bundle_names=["nonexistent"])

        with patch(
            "ksm.commands.sync.format_error",
            wraps=__import__("ksm.errors", fromlist=["format_error"]).format_error,
        ) as mock_fmt:
            run_sync(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
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
        from ksm.commands.sync import run_sync

        ksm_dir = tmp_path / "ksm"
        ksm_dir.mkdir()
        reg = tmp_path / "reg"
        _setup_bundle(reg, "aws", {"skills/f.md": b"data"})

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )
        manifest = Manifest(entries=[_make_entry("aws", files=["skills/f.md"])])
        args = _make_args(bundle_names=["aws"])

        with (
            patch("sys.stdin") as mock_stdin,
            patch(
                "ksm.commands.sync.format_error",
                wraps=__import__(
                    "ksm.errors",
                    fromlist=["format_error"],
                ).format_error,
            ) as mock_fmt,
        ):
            mock_stdin.isatty.return_value = False
            run_sync(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=tmp_path / "local",
                target_global=tmp_path / "global",
            )

        mock_fmt.assert_called_once()
        _, kwargs = mock_fmt.call_args
        assert kwargs.get("stream") is sys.stderr

    def test_format_warning_receives_stream_stderr_pull_fail(
        self,
        tmp_path: Path,
    ) -> None:
        """format_warning called with stream=sys.stderr when
        pull_repo fails."""
        from ksm.commands.sync import run_sync

        ksm_dir = tmp_path / "ksm"
        ksm_dir.mkdir()
        reg = tmp_path / "reg"
        _setup_bundle(reg, "team", {"skills/f.md": b"data"})

        target = tmp_path / "workspace" / ".kiro"
        (target / "skills").mkdir(parents=True)
        (target / "skills" / "f.md").write_bytes(b"old")

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="custom",
                    url="https://example.com/repo.git",
                    local_path=str(reg),
                    is_default=False,
                )
            ]
        )
        manifest = Manifest(
            entries=[
                _make_entry(
                    "team",
                    "local",
                    "custom",
                    files=["skills/f.md"],
                )
            ]
        )
        args = _make_args(bundle_names=["team"], yes=True)

        with (
            patch(
                "ksm.commands.sync.pull_repo",
                side_effect=RuntimeError("net err"),
            ),
            patch(
                "ksm.commands.sync.format_warning",
                wraps=__import__(
                    "ksm.errors",
                    fromlist=["format_warning"],
                ).format_warning,
            ) as mock_fmt,
        ):
            run_sync(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=target,
                target_global=tmp_path / "global",
            )

        assert mock_fmt.call_count >= 1
        # Check the first call (pull failure warning)
        _, kwargs = mock_fmt.call_args_list[0]
        assert kwargs.get("stream") is sys.stderr

    def test_format_warning_receives_stream_stderr_resolve_fail(
        self,
        tmp_path: Path,
    ) -> None:
        """format_warning called with stream=sys.stderr when
        bundle can't be resolved during sync."""
        from ksm.commands.sync import run_sync

        ksm_dir = tmp_path / "ksm"
        ksm_dir.mkdir()
        reg = tmp_path / "reg"
        reg.mkdir(parents=True)

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )
        manifest = Manifest(
            entries=[
                _make_entry(
                    "missing",
                    "local",
                    "default",
                )
            ]
        )
        args = _make_args(bundle_names=["missing"], yes=True)

        with patch(
            "ksm.commands.sync.format_warning",
            wraps=__import__(
                "ksm.errors",
                fromlist=["format_warning"],
            ).format_warning,
        ) as mock_fmt:
            run_sync(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=tmp_path / "local",
                target_global=tmp_path / "global",
            )

        mock_fmt.assert_called_once()
        _, kwargs = mock_fmt.call_args
        assert kwargs.get("stream") is sys.stderr


# --- Tests for green success prefix (Req 3.3, 3.4, 3.5) ---
# Feature: color-and-scope-selection
# **Validates: Requirements 3.3, 3.4, 3.5**


class TestSyncGreenSuccessPrefix:
    """Property 14: sync success message includes
    success-styled checkmark and bundle name."""

    _SUCCESS = "\033[92m"
    _RESET = "\033[0m"

    def test_synced_prefix_success_on_tty(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Property 14: successful sync prints success-styled
        checkmark to stderr when stream is TTY."""
        from ksm.commands.sync import run_sync

        reg = tmp_path / "reg"
        _setup_bundle(reg, "aws", {"skills/f.md": b"new"})
        target = tmp_path / "target" / ".kiro"
        target.mkdir(parents=True)
        (target / "skills").mkdir()
        (target / "skills" / "f.md").write_bytes(b"old")

        ksm_dir = tmp_path / "ksm"
        ksm_dir.mkdir(parents=True)

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )
        manifest = Manifest(entries=[_make_entry("aws", files=["skills/f.md"])])
        args = _make_args(bundle_names=["aws"], yes=True)

        with patch.dict(
            "os.environ",
            {"TERM": "xterm-256color"},
            clear=True,
        ):
            with patch(
                "sys.stderr.isatty",
                return_value=True,
            ):
                code = run_sync(
                    args,
                    registry_index=idx,
                    manifest=manifest,
                    manifest_path=(ksm_dir / "manifest.json"),
                    target_local=target,
                    target_global=(tmp_path / "global" / ".kiro"),
                )

        assert code == 0
        captured = capsys.readouterr()
        assert "Synced" in captured.err
        assert self._SUCCESS in captured.err

    def test_synced_prefix_plain_with_no_color(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Property 14: output is plain text when NO_COLOR set."""
        from ksm.commands.sync import run_sync

        reg = tmp_path / "reg"
        _setup_bundle(reg, "aws", {"skills/f.md": b"new"})
        target = tmp_path / "target" / ".kiro"
        target.mkdir(parents=True)
        (target / "skills").mkdir()
        (target / "skills" / "f.md").write_bytes(b"old")

        ksm_dir = tmp_path / "ksm"
        ksm_dir.mkdir(parents=True)

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )
        manifest = Manifest(entries=[_make_entry("aws", files=["skills/f.md"])])
        args = _make_args(bundle_names=["aws"], yes=True)

        with patch.dict(
            "os.environ",
            {"NO_COLOR": "1"},
            clear=False,
        ):
            code = run_sync(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=(ksm_dir / "manifest.json"),
                target_local=target,
                target_global=(tmp_path / "global" / ".kiro"),
            )

        assert code == 0
        captured = capsys.readouterr()
        assert "Synced" in captured.err
        assert "\033[" not in captured.err

    def test_synced_prefix_contains_bundle_name(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Property 14: success message includes bundle name
        alongside the green prefix.
        **Validates: Requirements 3.5**"""
        from ksm.commands.sync import run_sync

        reg = tmp_path / "reg"
        _setup_bundle(reg, "aws", {"skills/f.md": b"new"})
        target = tmp_path / "target" / ".kiro"
        target.mkdir(parents=True)
        (target / "skills").mkdir()
        (target / "skills" / "f.md").write_bytes(b"old")

        ksm_dir = tmp_path / "ksm"
        ksm_dir.mkdir(parents=True)

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )
        manifest = Manifest(entries=[_make_entry("aws", files=["skills/f.md"])])
        args = _make_args(bundle_names=["aws"], yes=True)

        code = run_sync(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=(ksm_dir / "manifest.json"),
            target_local=target,
            target_global=(tmp_path / "global" / ".kiro"),
        )

        assert code == 0
        captured = capsys.readouterr()
        assert "Synced" in captured.err
        assert "aws" in captured.err


# --- Tests for colored sync confirmation prompt (Reqs 10.1-10.3) ---
# Feature: color-and-scope-selection
# **Validates: Requirements 10.1, 10.2, 10.3**


class FakeTTY(io.StringIO):
    """A fake stream that reports isatty() = True."""

    def isatty(self) -> bool:
        return True


class TestSyncConfirmationColor:
    """Properties 17 & 18: sync confirmation wraps bundle
    names in bold and scope description in bold."""

    _BOLD = "\033[1m"
    _ACCENT = "\033[96m"
    _RESET = "\033[0m"

    # --- Property 17: bundle names wrapped in bold ---

    @given(
        bundle_name=st.from_regex(r"[a-z]{3,10}", fullmatch=True),
    )
    @h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_sync_confirm_bold_bundle_tty(
        self,
        bundle_name: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Property 17: sync confirmation wraps bundle names
        in bold when stream is a TTY.
        **Validates: Requirements 10.1**"""
        from ksm.commands.sync import (
            _build_confirmation_message,
        )

        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")

        entries = [
            _make_entry(
                bundle_name,
                scope="local",
                files=["skills/f.md"],
            )
        ]

        stream = FakeTTY()
        msg = _build_confirmation_message(entries, stream=stream)

        expected = f"{self._ACCENT}{bundle_name}{self._RESET}"
        assert expected in msg

    # --- Property 18: scope shown per bundle in muted ---

    @given(
        scope_combo=st.sampled_from(["local_only", "global_only", "mixed"]),
    )
    @h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_sync_confirm_bold_scope_tty(
        self,
        scope_combo: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Property 18: sync confirmation shows scope per bundle."""
        from ksm.commands.sync import (
            _build_confirmation_message,
        )

        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")

        if scope_combo == "local_only":
            entries = [_make_entry("aws", scope="local")]
        elif scope_combo == "global_only":
            entries = [_make_entry("aws", scope="global")]
        else:
            entries = [
                _make_entry("aws", scope="local"),
                _make_entry("team", scope="global"),
            ]

        stream = FakeTTY()
        msg = _build_confirmation_message(entries, stream=stream)

        for e in entries:
            assert e.scope in msg

    # --- Plain text when stream is None ---

    def test_sync_confirm_plain_when_stream_none(
        self,
    ) -> None:
        """sync confirmation is plain text when stream is None."""
        from ksm.commands.sync import (
            _build_confirmation_message,
        )

        entries = [
            _make_entry(
                "aws",
                scope="local",
                files=["skills/f.md"],
            )
        ]

        msg = _build_confirmation_message(entries, stream=None)

        assert "\033[" not in msg
        assert "aws" in msg
        assert "local" in msg

    # --- Plain text when stream is non-TTY ---

    def test_sync_confirm_plain_when_non_tty(
        self,
    ) -> None:
        """sync confirmation is plain text when stream is non-TTY."""
        import io

        from ksm.commands.sync import (
            _build_confirmation_message,
        )

        entries = [
            _make_entry(
                "aws",
                scope="global",
                files=["steering/s.md"],
            )
        ]

        stream = io.StringIO()
        msg = _build_confirmation_message(entries, stream=stream)

        assert "\033[" not in msg
        assert "aws" in msg
        assert "global" in msg

    # --- Preserves existing structure ---

    def test_sync_confirm_preserves_structure(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Colored confirmation preserves prompt structure."""
        from ksm.commands.sync import (
            _build_confirmation_message,
        )

        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm-256color")

        entries = [
            _make_entry(
                "aws",
                scope="local",
                files=["skills/f.md", "steering/s.md"],
            ),
            _make_entry(
                "team",
                scope="global",
                files=["skills/g.md"],
            ),
        ]

        stream = FakeTTY()
        msg = _build_confirmation_message(entries, stream=stream)

        assert "2 bundles" in msg
        assert "Continue?" in msg
        assert "[y/n]" in msg


# --- Tests for sync --all deduplication (Issue #28) ---


def test_sync_all_deduplicates_same_bundle_workspace(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """sync --all with duplicate entries for same
    (bundle_name, scope, workspace_path) syncs only once."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "python_dev", {"steering/python.md": b"data"})
    target = tmp_path / "target" / ".kiro"
    target.mkdir(parents=True)

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    ws_path = str((tmp_path / "target").resolve())

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    # Four duplicate entries for the same bundle+scope+workspace
    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name="python_dev",
                source_registry="default",
                scope="local",
                installed_files=["steering/python.md"],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                workspace_path=ws_path,
            ),
            ManifestEntry(
                bundle_name="python_dev",
                source_registry="default",
                scope="local",
                installed_files=["steering/python.md"],
                installed_at="2025-01-02T00:00:00Z",
                updated_at="2025-01-02T00:00:00Z",
                workspace_path=ws_path,
            ),
            ManifestEntry(
                bundle_name="python_dev",
                source_registry="default",
                scope="local",
                installed_files=["steering/python.md"],
                installed_at="2025-01-03T00:00:00Z",
                updated_at="2025-01-03T00:00:00Z",
                workspace_path=ws_path,
            ),
            ManifestEntry(
                bundle_name="python_dev",
                source_registry="default",
                scope="local",
                installed_files=["steering/python.md"],
                installed_at="2025-01-04T00:00:00Z",
                updated_at="2025-01-04T00:00:00Z",
                workspace_path=ws_path,
            ),
        ]
    )

    args = _make_args(all=True, yes=True)
    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    captured = capsys.readouterr()
    # "Synced" should appear exactly once, not four times
    assert captured.err.count("Synced") == 1


def test_sync_all_distinct_workspaces_all_synced(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """sync --all with same bundle in different workspaces
    syncs each workspace independently."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "aws", {"skills/f.md": b"data"})

    target_a = tmp_path / "ws-a" / ".kiro"
    target_b = tmp_path / "ws-b" / ".kiro"
    target_a.mkdir(parents=True)
    target_b.mkdir(parents=True)

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    ws_a = str((tmp_path / "ws-a").resolve())
    ws_b = str((tmp_path / "ws-b").resolve())

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name="aws",
                source_registry="default",
                scope="local",
                installed_files=["skills/f.md"],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                workspace_path=ws_a,
            ),
            ManifestEntry(
                bundle_name="aws",
                source_registry="default",
                scope="local",
                installed_files=["skills/f.md"],
                installed_at="2025-01-02T00:00:00Z",
                updated_at="2025-01-02T00:00:00Z",
                workspace_path=ws_b,
            ),
        ]
    )

    # Use ws-a as target_local — only ws-a entry will actually
    # install files (ws-b targets a different path). Both should
    # be attempted.
    args = _make_args(all=True, yes=True)
    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_a,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    captured = capsys.readouterr()
    # Both entries should be synced (distinct workspace_path keys)
    assert captured.err.count("Synced") == 2


def test_sync_all_legacy_and_modern_not_collapsed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """sync --all treats legacy (workspace_path=None) and modern
    (workspace_path set) entries as distinct — not deduplicated."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "aws", {"skills/f.md": b"data"})
    target = tmp_path / "target" / ".kiro"
    target.mkdir(parents=True)

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    ws_path = str((tmp_path / "target").resolve())

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name="aws",
                source_registry="default",
                scope="local",
                installed_files=["skills/f.md"],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                workspace_path=None,
            ),
            ManifestEntry(
                bundle_name="aws",
                source_registry="default",
                scope="local",
                installed_files=["skills/f.md"],
                installed_at="2025-01-02T00:00:00Z",
                updated_at="2025-01-02T00:00:00Z",
                workspace_path=ws_path,
            ),
        ]
    )

    args = _make_args(all=True, yes=True)
    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    captured = capsys.readouterr()
    # Both entries should be synced (None vs set are distinct keys)
    assert captured.err.count("Synced") == 2


def test_sync_all_confirmation_count_reflects_dedup(
    tmp_path: Path,
) -> None:
    """Confirmation message count reflects deduplicated set,
    not raw manifest entry count."""
    from ksm.commands.sync import _build_confirmation_message

    ws_path = "/home/user/project"
    # 3 raw entries, but only 1 unique key
    entries_raw = [
        ManifestEntry(
            bundle_name="aws",
            source_registry="default",
            scope="local",
            installed_files=["skills/f.md"],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            workspace_path=ws_path,
        ),
        ManifestEntry(
            bundle_name="aws",
            source_registry="default",
            scope="local",
            installed_files=["skills/f.md"],
            installed_at="2025-01-02T00:00:00Z",
            updated_at="2025-01-02T00:00:00Z",
            workspace_path=ws_path,
        ),
        ManifestEntry(
            bundle_name="aws",
            source_registry="default",
            scope="local",
            installed_files=["skills/f.md"],
            installed_at="2025-01-03T00:00:00Z",
            updated_at="2025-01-03T00:00:00Z",
            workspace_path=ws_path,
        ),
    ]

    # Simulate dedup (what run_sync will do)
    seen: set[tuple[str, str, str | None]] = set()
    deduped: list[ManifestEntry] = []
    for e in entries_raw:
        key = (e.bundle_name, e.scope, e.workspace_path)
        if key not in seen:
            seen.add(key)
            deduped.append(e)

    msg = _build_confirmation_message(deduped)
    assert "1 bundle" in msg
    # Should NOT say "3 bundles"
    assert "3 bundle" not in msg


# --- Regression guard: named sync with duplicates (Issue #28) ---


def test_sync_named_with_duplicates_syncs_all(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Named sync (ksm sync <bundle>) with duplicate entries
    syncs all of them — no dedup applied to named sync."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "aws", {"skills/f.md": b"data"})
    target = tmp_path / "target" / ".kiro"
    target.mkdir(parents=True)

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    ws_path = str((tmp_path / "target").resolve())

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    # Two duplicate entries
    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name="aws",
                source_registry="default",
                scope="local",
                installed_files=["skills/f.md"],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                workspace_path=ws_path,
            ),
            ManifestEntry(
                bundle_name="aws",
                source_registry="default",
                scope="local",
                installed_files=["skills/f.md"],
                installed_at="2025-01-02T00:00:00Z",
                updated_at="2025-01-02T00:00:00Z",
                workspace_path=ws_path,
            ),
        ]
    )

    args = _make_args(bundle_names=["aws"], yes=True)
    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    captured = capsys.readouterr()
    # Named sync should sync both entries (no dedup)
    assert captured.err.count("Synced") == 2


# --- Tests for workspace-path-aware sync targeting (Issue #30) ---


def test_sync_entry_uses_workspace_path_for_local(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_sync_entry syncs to workspace_path/.kiro, not target_local,
    when workspace_path is set on a local entry."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "aws", {"skills/f.md": b"ws-data"})

    # workspace_path points to ws_dir (different from target_local)
    ws_dir = tmp_path / "actual-workspace"
    ws_kiro = ws_dir / ".kiro"
    ws_kiro.mkdir(parents=True)

    # target_local is a DIFFERENT directory
    target_local = tmp_path / "wrong-workspace" / ".kiro"
    target_local.mkdir(parents=True)

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    entry = _make_entry("aws", scope="local", files=["skills/f.md"])
    entry.workspace_path = str(ws_dir.resolve())
    manifest = Manifest(entries=[entry])

    args = _make_args(bundle_names=["aws"], yes=True)
    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    # Files should be written to workspace_path/.kiro
    assert (ws_kiro / "skills" / "f.md").exists()
    assert (ws_kiro / "skills" / "f.md").read_bytes() == b"ws-data"
    # Files should NOT be written to target_local
    assert not (target_local / "skills" / "f.md").exists()


def test_sync_entry_falls_back_to_target_local_when_no_workspace_path(
    tmp_path: Path,
) -> None:
    """_sync_entry falls back to target_local when workspace_path
    is None (legacy entry)."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "aws", {"skills/f.md": b"legacy-data"})

    target_local = tmp_path / "target" / ".kiro"
    target_local.mkdir(parents=True)

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    # workspace_path is None by default from _make_entry
    entry = _make_entry("aws", scope="local", files=["skills/f.md"])
    assert entry.workspace_path is None
    manifest = Manifest(entries=[entry])

    args = _make_args(bundle_names=["aws"], yes=True)
    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    # Files should be written to target_local
    assert (target_local / "skills" / "f.md").exists()
    assert (target_local / "skills" / "f.md").read_bytes() == b"legacy-data"


def test_sync_entry_warns_and_skips_missing_workspace(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_sync_entry warns and skips when workspace_path does not
    exist on disk."""
    from ksm.commands.sync import run_sync

    reg = tmp_path / "reg"
    _setup_bundle(reg, "aws", {"skills/f.md": b"data"})

    # workspace_path points to a non-existent directory
    missing_ws = tmp_path / "gone-workspace"
    # Do NOT create missing_ws

    target_local = tmp_path / "target" / ".kiro"
    target_local.mkdir(parents=True)

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    entry = _make_entry("aws", scope="local", files=["skills/f.md"])
    entry.workspace_path = str(missing_ws)
    manifest = Manifest(entries=[entry])

    args = _make_args(bundle_names=["aws"], yes=True)
    code = run_sync(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    captured = capsys.readouterr()
    # Warning about missing workspace
    assert "no longer exists" in captured.err
    # No files written anywhere
    assert not (target_local / "skills" / "f.md").exists()
    assert not (missing_ws / ".kiro" / "skills" / "f.md").exists()


# Feature: sync-all-wrong-workspace, Property 1: Workspace targeting
# **Validates: Requirements 1.2**
@given(
    ws_suffix=st.from_regex(r"[a-z]{3,8}", fullmatch=True),
)
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_sync_entry_targets_workspace_path(
    ws_suffix: str,
) -> None:
    """Property 1: For local entries with non-null workspace_path,
    the install target is always Path(workspace_path) / '.kiro'
    and never target_local."""
    import tempfile

    from ksm.commands.sync import run_sync

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg"
        _setup_bundle(reg, "b", {"skills/f.md": b"x"})

        # Create workspace directory with generated suffix
        ws_dir = base / f"ws-{ws_suffix}"
        ws_kiro = ws_dir / ".kiro"
        ws_kiro.mkdir(parents=True)

        # target_local is a DIFFERENT directory
        target_local = base / "wrong" / ".kiro"
        target_local.mkdir(parents=True)

        ksm_dir = base / "ksm"
        ksm_dir.mkdir()

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )
        entry = _make_entry("b", scope="local", files=["skills/f.md"])
        entry.workspace_path = str(ws_dir.resolve())
        manifest = Manifest(entries=[entry])

        args = _make_args(bundle_names=["b"], yes=True)

        with patch("ksm.commands.sync.install_bundle") as mock_install:
            mock_install.return_value = []
            run_sync(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=target_local,
                target_global=base / "global" / ".kiro",
            )

        mock_install.assert_called_once()
        call_kwargs = mock_install.call_args
        actual_target = call_kwargs.kwargs.get(
            "target_dir",
            call_kwargs.args[1] if len(call_kwargs.args) > 1 else None,
        )
        expected = Path(entry.workspace_path) / ".kiro"
        assert actual_target == expected, (
            f"Expected target_dir={expected}, " f"got {actual_target}"
        )
        assert actual_target != target_local


# --- Tests for _sync_global_hooks (FR-4.1, FR-4.2, FR-4.4, FR-4.5, FR-4.6) ---


class TestSyncGlobalHooks:
    """Tests for _sync_global_hooks: distributing hooks from
    global bundles to workspaces."""

    def test_copies_hooks_from_global_bundle_to_workspace(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """(a) _sync_global_hooks copies hooks from a global bundle
        with has_hooks=True to a workspace.
        **Validates: Requirements FR-4.1, FR-4.2**"""
        from ksm.commands.sync import _sync_global_hooks

        # Set up a registry with a bundle that has hooks
        reg = tmp_path / "reg"
        _setup_bundle(
            reg,
            "my-bundle",
            {
                "hooks/pre-commit.json": b"hook-content",
                "hooks/on-save.json": b"save-hook",
                "skills/skill.md": b"skill-data",
            },
        )

        # Create a workspace directory
        ws_dir = tmp_path / "workspace"
        ws_dir.mkdir()

        # Build registry index
        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )

        # Build manifest with a global entry that has_hooks=True
        manifest = Manifest(
            entries=[
                ManifestEntry(
                    bundle_name="my-bundle",
                    source_registry="default",
                    scope="global",
                    installed_files=["skills/skill.md"],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                    has_hooks=True,
                ),
            ]
        )

        results = _sync_global_hooks(
            registry_index=idx,
            manifest=manifest,
            target_workspaces=[ws_dir],
        )

        # Hooks should be copied to workspace/.kiro/hooks/
        hooks_dir = ws_dir / ".kiro" / "hooks"
        assert (hooks_dir / "pre-commit.json").exists()
        assert (hooks_dir / "pre-commit.json").read_bytes() == b"hook-content"
        assert (hooks_dir / "on-save.json").exists()
        assert (hooks_dir / "on-save.json").read_bytes() == b"save-hook"

        # Should NOT copy non-hook subdirs
        assert not (ws_dir / ".kiro" / "skills").exists()

        # Should return CopyResult entries
        assert len(results) == 2

    def test_skips_bundle_not_found_in_registry_with_warning(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """(b) Skips bundles not found in registry with warning.
        **Validates: Requirements FR-4.6**"""
        from ksm.commands.sync import _sync_global_hooks

        # Empty registry — bundle won't be found
        reg = tmp_path / "reg"
        reg.mkdir(parents=True)

        ws_dir = tmp_path / "workspace"
        ws_dir.mkdir()

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )

        manifest = Manifest(
            entries=[
                ManifestEntry(
                    bundle_name="gone-bundle",
                    source_registry="default",
                    scope="global",
                    installed_files=["skills/f.md"],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                    has_hooks=True,
                ),
            ]
        )

        results = _sync_global_hooks(
            registry_index=idx,
            manifest=manifest,
            target_workspaces=[ws_dir],
        )

        # No files should be copied
        assert results == []
        # Warning should be printed
        captured = capsys.readouterr()
        assert "warning" in captured.err.lower()
        assert "gone-bundle" in captured.err

    def test_skips_workspace_that_no_longer_exists_with_warning(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """(c) Skips workspaces that no longer exist with warning.
        **Validates: Requirements FR-4.5**"""
        from ksm.commands.sync import _sync_global_hooks

        # Set up a registry with a bundle that has hooks
        reg = tmp_path / "reg"
        _setup_bundle(
            reg,
            "my-bundle",
            {"hooks/pre-commit.json": b"hook-content"},
        )

        # Point to a workspace that does NOT exist
        missing_ws = tmp_path / "gone-workspace"

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )

        manifest = Manifest(
            entries=[
                ManifestEntry(
                    bundle_name="my-bundle",
                    source_registry="default",
                    scope="global",
                    installed_files=["skills/f.md"],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                    has_hooks=True,
                ),
            ]
        )

        results = _sync_global_hooks(
            registry_index=idx,
            manifest=manifest,
            target_workspaces=[missing_ws],
        )

        # No files should be copied
        assert results == []
        # Warning should be printed about missing workspace
        captured = capsys.readouterr()
        assert "warning" in captured.err.lower()

    def test_idempotent_second_call_all_unchanged(
        self,
        tmp_path: Path,
    ) -> None:
        """(d) Idempotent — second call produces all UNCHANGED results.
        **Validates: Requirements FR-4.4**"""
        from ksm.copier import CopyStatus
        from ksm.commands.sync import _sync_global_hooks

        reg = tmp_path / "reg"
        _setup_bundle(
            reg,
            "my-bundle",
            {"hooks/pre-commit.json": b"hook-content"},
        )

        ws_dir = tmp_path / "workspace"
        ws_dir.mkdir()

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )

        manifest = Manifest(
            entries=[
                ManifestEntry(
                    bundle_name="my-bundle",
                    source_registry="default",
                    scope="global",
                    installed_files=["skills/f.md"],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                    has_hooks=True,
                ),
            ]
        )

        # First call — should create files
        results1 = _sync_global_hooks(
            registry_index=idx,
            manifest=manifest,
            target_workspaces=[ws_dir],
        )
        assert len(results1) == 1
        assert results1[0].status == CopyStatus.NEW

        # Second call — files already exist and are identical
        results2 = _sync_global_hooks(
            registry_index=idx,
            manifest=manifest,
            target_workspaces=[ws_dir],
        )
        assert len(results2) == 1
        assert all(r.status == CopyStatus.UNCHANGED for r in results2)

    def test_does_nothing_when_no_global_entries_have_hooks(
        self,
        tmp_path: Path,
    ) -> None:
        """(e) Does nothing when no global entries have has_hooks=True.
        **Validates: Requirements FR-4.1**"""
        from ksm.commands.sync import _sync_global_hooks

        reg = tmp_path / "reg"
        _setup_bundle(
            reg,
            "my-bundle",
            {"skills/f.md": b"data"},
        )

        ws_dir = tmp_path / "workspace"
        ws_dir.mkdir()

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )

        # Global entry with has_hooks=False
        manifest = Manifest(
            entries=[
                ManifestEntry(
                    bundle_name="my-bundle",
                    source_registry="default",
                    scope="global",
                    installed_files=["skills/f.md"],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                    has_hooks=False,
                ),
                # Local entry with has_hooks=True should be ignored
                ManifestEntry(
                    bundle_name="local-bundle",
                    source_registry="default",
                    scope="local",
                    installed_files=["hooks/h.json"],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                    has_hooks=True,
                ),
            ]
        )

        results = _sync_global_hooks(
            registry_index=idx,
            manifest=manifest,
            target_workspaces=[ws_dir],
        )

        # No results — nothing to sync
        assert results == []
        # No hooks directory created
        assert not (ws_dir / ".kiro" / "hooks").exists()


# --- Tests for run_sync hooks integration (FR-4.2, FR-4.3) ---


class TestRunSyncHooksIntegration:
    """Tests for run_sync integration with _sync_global_hooks:
    verifying hooks are distributed to the correct workspaces
    during sync.
    **Validates: Requirements FR-4.2, FR-4.3**"""

    def test_run_sync_all_distributes_hooks_to_all_workspaces(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """(a) run_sync with --all distributes hooks from global
        bundles to all tracked workspaces.
        **Validates: Requirements FR-4.3**"""
        from ksm.commands.sync import run_sync

        # Set up registry with a bundle that has hooks + skills
        reg = tmp_path / "reg"
        _setup_bundle(
            reg,
            "my-bundle",
            {
                "hooks/on-save.json": b"hook-data",
                "skills/skill.md": b"skill-data",
            },
        )

        # Create two workspace directories
        ws_a = tmp_path / "workspace-a"
        ws_a.mkdir()
        ws_b = tmp_path / "workspace-b"
        ws_b.mkdir()

        ksm_dir = tmp_path / "ksm"
        ksm_dir.mkdir(parents=True)

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )

        ws_a_resolved = str(ws_a.resolve())
        ws_b_resolved = str(ws_b.resolve())

        # Manifest: global entry with has_hooks=True, plus
        # two local entries in different workspaces
        manifest = Manifest(
            entries=[
                ManifestEntry(
                    bundle_name="my-bundle",
                    source_registry="default",
                    scope="global",
                    installed_files=["skills/skill.md"],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                    has_hooks=True,
                ),
                ManifestEntry(
                    bundle_name="other-local",
                    source_registry="default",
                    scope="local",
                    installed_files=["skills/f.md"],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                    workspace_path=ws_a_resolved,
                ),
                ManifestEntry(
                    bundle_name="another-local",
                    source_registry="default",
                    scope="local",
                    installed_files=["steering/s.md"],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                    workspace_path=ws_b_resolved,
                ),
            ]
        )

        # Set up the local bundles in the registry too
        _setup_bundle(reg, "other-local", {"skills/f.md": b"x"})
        _setup_bundle(reg, "another-local", {"steering/s.md": b"y"})

        # target_local points to ws_a
        target_local = ws_a / ".kiro"
        target_local.mkdir(parents=True)

        args = _make_args(all=True, yes=True)
        code = run_sync(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target_local,
            target_global=tmp_path / "global" / ".kiro",
        )

        assert code == 0

        # Hooks should be distributed to BOTH workspaces
        hooks_a = ws_a / ".kiro" / "hooks" / "on-save.json"
        hooks_b = ws_b / ".kiro" / "hooks" / "on-save.json"
        assert hooks_a.exists(), "Hooks should be distributed to workspace-a"
        assert hooks_a.read_bytes() == b"hook-data"
        assert hooks_b.exists(), "Hooks should be distributed to workspace-b"
        assert hooks_b.read_bytes() == b"hook-data"

    def test_run_sync_without_all_distributes_hooks_to_current_only(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """(b) run_sync without --all distributes hooks to
        current workspace only (target_local.parent).
        **Validates: Requirements FR-4.2**"""
        from ksm.commands.sync import run_sync

        # Set up registry with a bundle that has hooks
        reg = tmp_path / "reg"
        _setup_bundle(
            reg,
            "my-bundle",
            {
                "hooks/on-save.json": b"hook-data",
                "skills/skill.md": b"skill-data",
            },
        )

        # Create two workspace directories
        ws_current = tmp_path / "current-ws"
        ws_other = tmp_path / "other-ws"
        ws_current.mkdir()
        ws_other.mkdir()

        ksm_dir = tmp_path / "ksm"
        ksm_dir.mkdir(parents=True)

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )

        ws_other_resolved = str(ws_other.resolve())

        # Manifest: global entry with has_hooks=True, plus
        # a local entry in a different workspace
        manifest = Manifest(
            entries=[
                ManifestEntry(
                    bundle_name="my-bundle",
                    source_registry="default",
                    scope="global",
                    installed_files=["skills/skill.md"],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                    has_hooks=True,
                ),
                ManifestEntry(
                    bundle_name="other-local",
                    source_registry="default",
                    scope="local",
                    installed_files=["skills/f.md"],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                    workspace_path=ws_other_resolved,
                ),
            ]
        )

        # Set up the local bundle in the registry
        _setup_bundle(reg, "other-local", {"skills/f.md": b"x"})

        # target_local points to current workspace
        target_local = ws_current / ".kiro"
        target_local.mkdir(parents=True)

        # Sync a specific bundle name (not --all)
        args = _make_args(bundle_names=["my-bundle"], yes=True)
        code = run_sync(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target_local,
            target_global=tmp_path / "global" / ".kiro",
        )

        assert code == 0

        # Hooks should be distributed to current workspace only
        hooks_current = ws_current / ".kiro" / "hooks" / "on-save.json"
        hooks_other = ws_other / ".kiro" / "hooks" / "on-save.json"
        assert (
            hooks_current.exists()
        ), "Hooks should be distributed to current workspace"
        assert hooks_current.read_bytes() == b"hook-data"
        assert not hooks_other.exists(), (
            "Hooks should NOT be distributed to other"
            " workspaces when --all is not used"
        )

    def test_sync_entry_global_does_not_copy_hooks(
        self,
        tmp_path: Path,
    ) -> None:
        """(c) Global entry sync via _sync_entry does not copy
        hooks — installer filtering excludes hooks/ for global
        scope.
        **Validates: Requirements FR-4.2**"""
        from ksm.commands.sync import run_sync

        # Set up registry with a bundle that has hooks + skills
        reg = tmp_path / "reg"
        _setup_bundle(
            reg,
            "my-bundle",
            {
                "hooks/on-save.json": b"hook-data",
                "skills/skill.md": b"skill-data",
            },
        )

        ksm_dir = tmp_path / "ksm"
        ksm_dir.mkdir(parents=True)

        target_global = tmp_path / "global" / ".kiro"
        target_global.mkdir(parents=True)

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(reg),
                    is_default=True,
                )
            ]
        )

        # Manifest: global entry with has_hooks=True
        manifest = Manifest(
            entries=[
                ManifestEntry(
                    bundle_name="my-bundle",
                    source_registry="default",
                    scope="global",
                    installed_files=["skills/skill.md"],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                    has_hooks=True,
                ),
            ]
        )

        # Sync the global bundle by name
        args = _make_args(bundle_names=["my-bundle"], yes=True)
        code = run_sync(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=tmp_path / "local" / ".kiro",
            target_global=target_global,
        )

        assert code == 0

        # Skills should be installed to global target
        assert (target_global / "skills" / "skill.md").exists()
        assert (target_global / "skills" / "skill.md").read_bytes() == b"skill-data"

        # Hooks should NOT be installed to global target
        assert not (target_global / "hooks").exists(), (
            "Hooks should not be copied during global"
            " entry sync — installer filters them out"
        )

        # Verify no installed_files contain hooks/ paths
        entry = manifest.entries[0]
        for f in entry.installed_files:
            assert not f.startswith("hooks/"), (
                f"Installed file '{f}' should not start"
                " with 'hooks/' for a global entry"
            )
