"""Tests for ksm.commands.sync module."""

import argparse
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
    defaults = {
        "bundle_names": [],
        "all": False,
        "yes": False,
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

    with patch("builtins.input", return_value="n"):
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
    manifest = Manifest(
        entries=[
            _make_entry("aws", files=["skills/f.md"]),
        ]
    )
    manifest.entries[0].updated_at = old_ts

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

    with patch("builtins.input", side_effect=EOFError):
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

        with patch("builtins.input", return_value=response):
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
        manifest = Manifest(entries=[_make_entry("b", files=["skills/f.md"])])
        manifest.entries[0].updated_at = old_ts

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
