"""Tests for ksm.commands.add module."""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import HealthCheck
from hypothesis import given
from hypothesis import settings as h_settings
from hypothesis import strategies as st

from ksm.manifest import Manifest
from ksm.registry import RegistryEntry, RegistryIndex


def _setup_registry(
    tmp_path: Path,
    bundles: dict[str, dict[str, dict[str, bytes]]],
) -> Path:
    """Create a registry directory with bundles on disk.

    bundles maps bundle_name -> {subdir -> {filename: content}}.
    Returns the registry path.
    """
    reg = tmp_path / "registry"
    for bname, subdirs in bundles.items():
        for sd, files in subdirs.items():
            for fname, content in files.items():
                fpath = reg / bname / sd / fname
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.write_bytes(content)
    return reg


def _make_args(**kwargs: object) -> argparse.Namespace:
    """Build an argparse.Namespace with defaults for add command."""
    defaults = {
        "bundle_spec": "aws",
        "interactive": False,
        "from_url": None,
        "local": False,
        "global_": False,
        "only": None,
        "dry_run": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_run_add_plain_name_installs_to_local(tmp_path: Path) -> None:
    """run_add with plain bundle name installs to local .kiro/."""
    from ksm.commands.add import run_add

    reg = _setup_registry(
        tmp_path,
        {"aws": {"skills": {"SKILL.md": b"skill"}}},
    )
    target_local = tmp_path / "workspace" / ".kiro"
    target_global = tmp_path / "home" / ".kiro"
    ksm_dir = tmp_path / "ksm_state"
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
    manifest = Manifest(entries=[])

    args = _make_args(bundle_spec="aws")
    code = run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=target_global,
    )

    assert code == 0
    assert (target_local / "skills" / "SKILL.md").exists()
    assert len(manifest.entries) == 1
    assert manifest.entries[0].scope == "local"


def test_run_add_global_flag_installs_to_global(
    tmp_path: Path,
) -> None:
    """run_add with -g flag installs to global ~/.kiro/."""
    from ksm.commands.add import run_add

    reg = _setup_registry(
        tmp_path,
        {"aws": {"steering": {"IAM.md": b"iam"}}},
    )
    target_local = tmp_path / "workspace" / ".kiro"
    target_global = tmp_path / "home" / ".kiro"
    ksm_dir = tmp_path / "ksm_state"
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
    manifest = Manifest(entries=[])

    args = _make_args(bundle_spec="aws", global_=True)
    code = run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=target_global,
    )

    assert code == 0
    assert (target_global / "steering" / "IAM.md").exists()
    assert not (target_local / "steering").exists()
    assert manifest.entries[0].scope == "global"


def test_run_add_display_launches_selector(
    tmp_path: Path,
) -> None:
    """run_add with --display launches interactive selector."""
    from ksm.commands.add import run_add

    reg = _setup_registry(
        tmp_path,
        {"aws": {"skills": {"S.md": b"s"}}},
    )
    target_local = tmp_path / "workspace" / ".kiro"
    target_global = tmp_path / "home" / ".kiro"
    ksm_dir = tmp_path / "ksm_state"
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
    manifest = Manifest(entries=[])

    args = _make_args(bundle_spec=None, interactive=True)

    with patch("ksm.commands.add.interactive_select", return_value=["aws"]) as mock_sel:
        code = run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target_local,
            target_global=target_global,
        )

    assert code == 0
    mock_sel.assert_called_once()
    assert (target_local / "skills" / "S.md").exists()


def test_run_add_display_quit_exits_zero(
    tmp_path: Path,
) -> None:
    """run_add with --display returns 0 when user quits selector."""
    from ksm.commands.add import run_add

    reg = _setup_registry(
        tmp_path,
        {"aws": {"skills": {"S.md": b"s"}}},
    )
    target_local = tmp_path / "workspace" / ".kiro"
    target_global = tmp_path / "home" / ".kiro"
    ksm_dir = tmp_path / "ksm_state"
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
    manifest = Manifest(entries=[])

    args = _make_args(bundle_spec=None, interactive=True)

    with patch("ksm.commands.add.interactive_select", return_value=None):
        code = run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target_local,
            target_global=target_global,
        )

    assert code == 0
    assert len(manifest.entries) == 0


def test_run_add_from_clones_ephemeral_and_cleans_up(
    tmp_path: Path,
) -> None:
    """run_add with --from clones ephemeral registry and cleans up."""
    from ksm.commands.add import run_add

    # Create a fake ephemeral clone directory
    ephemeral_dir = tmp_path / "ephemeral"
    ephemeral_dir.mkdir()
    bundle_dir = ephemeral_dir / "aws" / "skills"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "S.md").write_bytes(b"skill")

    target_local = tmp_path / "workspace" / ".kiro"
    target_global = tmp_path / "home" / ".kiro"
    ksm_dir = tmp_path / "ksm_state"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(registries=[])
    manifest = Manifest(entries=[])

    args = _make_args(
        bundle_spec="aws",
        from_url="https://github.com/org/repo.git",
    )

    with patch(
        "ksm.commands.add.clone_ephemeral",
        return_value=ephemeral_dir,
    ) as mock_clone:
        with patch("ksm.commands.add.shutil.rmtree") as mock_rmtree:
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=target_local,
                target_global=target_global,
            )

    assert code == 0
    mock_clone.assert_called_once_with("https://github.com/org/repo.git")
    mock_rmtree.assert_called_once_with(ephemeral_dir, ignore_errors=True)
    assert (target_local / "skills" / "S.md").exists()


def test_run_add_from_cleans_up_on_failure(
    tmp_path: Path,
) -> None:
    """run_add with --from cleans up ephemeral dir even on error."""
    from ksm.commands.add import run_add

    # Ephemeral dir with no matching bundle
    ephemeral_dir = tmp_path / "ephemeral"
    ephemeral_dir.mkdir()

    target_local = tmp_path / "workspace" / ".kiro"
    target_global = tmp_path / "home" / ".kiro"
    ksm_dir = tmp_path / "ksm_state"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(registries=[])
    manifest = Manifest(entries=[])

    args = _make_args(
        bundle_spec="nonexistent",
        from_url="https://github.com/org/repo.git",
    )

    with patch(
        "ksm.commands.add.clone_ephemeral",
        return_value=ephemeral_dir,
    ):
        with patch("ksm.commands.add.shutil.rmtree") as mock_rmtree:
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=target_local,
                target_global=target_global,
            )

    assert code == 1
    mock_rmtree.assert_called_once_with(ephemeral_dir, ignore_errors=True)


def test_run_add_subdirectory_filter_restricts(
    tmp_path: Path,
) -> None:
    """run_add with --skills-only copies only skills."""
    from ksm.commands.add import run_add

    reg = _setup_registry(
        tmp_path,
        {
            "aws": {
                "skills": {"S.md": b"s"},
                "steering": {"ST.md": b"st"},
            }
        },
    )
    target_local = tmp_path / "workspace" / ".kiro"
    target_global = tmp_path / "home" / ".kiro"
    ksm_dir = tmp_path / "ksm_state"
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
    manifest = Manifest(entries=[])

    args = _make_args(bundle_spec="aws", only=["skills"])
    code = run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=target_global,
    )

    assert code == 0
    assert (target_local / "skills" / "S.md").exists()
    assert not (target_local / "steering").exists()


def test_run_add_dot_notation_plus_filter_raises(
    tmp_path: Path,
) -> None:
    """run_add with dot notation + subdirectory filter is error."""
    from ksm.commands.add import run_add

    target_local = tmp_path / "workspace" / ".kiro"
    target_global = tmp_path / "home" / ".kiro"
    ksm_dir = tmp_path / "ksm_state"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(registries=[])
    manifest = Manifest(entries=[])

    args = _make_args(
        bundle_spec="aws.skills.cross",
        only=["skills"],
    )
    code = run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=target_global,
    )

    assert code == 1


def test_run_add_ephemeral_not_persisted_in_registry(
    tmp_path: Path,
) -> None:
    """run_add with --from does not add URL to registry index."""
    from ksm.commands.add import run_add

    ephemeral_dir = tmp_path / "ephemeral"
    ephemeral_dir.mkdir()
    bundle_dir = ephemeral_dir / "aws" / "skills"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "S.md").write_bytes(b"skill")

    target_local = tmp_path / "workspace" / ".kiro"
    target_global = tmp_path / "home" / ".kiro"
    ksm_dir = tmp_path / "ksm_state"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(tmp_path / "empty_reg"),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(entries=[])
    registries_before = len(idx.registries)

    args = _make_args(
        bundle_spec="aws",
        from_url="https://github.com/org/repo.git",
    )

    with patch(
        "ksm.commands.add.clone_ephemeral",
        return_value=ephemeral_dir,
    ):
        with patch("ksm.commands.add.shutil.rmtree"):
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=target_local,
                target_global=target_global,
            )

    assert code == 0
    assert len(idx.registries) == registries_before


def test_run_add_ephemeral_source_recorded_as_git_url(
    tmp_path: Path,
) -> None:
    """run_add with --from records git URL as source in manifest."""
    from ksm.commands.add import run_add

    ephemeral_dir = tmp_path / "ephemeral"
    ephemeral_dir.mkdir()
    bundle_dir = ephemeral_dir / "aws" / "skills"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "S.md").write_bytes(b"skill")

    target_local = tmp_path / "workspace" / ".kiro"
    target_global = tmp_path / "home" / ".kiro"
    ksm_dir = tmp_path / "ksm_state"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(registries=[])
    manifest = Manifest(entries=[])
    git_url = "https://github.com/org/repo.git"

    args = _make_args(bundle_spec="aws", from_url=git_url)

    with patch(
        "ksm.commands.add.clone_ephemeral",
        return_value=ephemeral_dir,
    ):
        with patch("ksm.commands.add.shutil.rmtree"):
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=target_local,
                target_global=target_global,
            )

    assert code == 0
    assert manifest.entries[0].source_registry == git_url


def test_run_add_unknown_bundle_prints_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_add with unknown bundle prints error and exits 1."""
    from ksm.commands.add import run_add

    reg = _setup_registry(tmp_path, {})
    target_local = tmp_path / "workspace" / ".kiro"
    target_global = tmp_path / "home" / ".kiro"
    ksm_dir = tmp_path / "ksm_state"
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
    manifest = Manifest(entries=[])

    args = _make_args(bundle_spec="nonexistent")
    code = run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=target_global,
    )

    assert code == 1
    captured = capsys.readouterr()
    assert "nonexistent" in captured.err


def test_run_add_dot_notation_installs_item(
    tmp_path: Path,
) -> None:
    """run_add with dot notation installs only the target item."""
    from ksm.commands.add import run_add

    reg = _setup_registry(
        tmp_path,
        {
            "aws": {
                "skills": {
                    "cross/SKILL.md": b"cross",
                    "other/SKILL.md": b"other",
                },
            }
        },
    )
    target_local = tmp_path / "workspace" / ".kiro"
    target_global = tmp_path / "home" / ".kiro"
    ksm_dir = tmp_path / "ksm_state"
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
    manifest = Manifest(entries=[])

    args = _make_args(bundle_spec="aws.skills.cross")
    code = run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=target_global,
    )

    assert code == 0
    assert (target_local / "skills" / "cross" / "SKILL.md").exists()
    assert not (target_local / "skills" / "other").exists()


def test_run_add_dot_notation_missing_item_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_add with dot notation for missing item prints error."""
    from ksm.commands.add import run_add

    reg = _setup_registry(
        tmp_path,
        {"aws": {"skills": {"cross/SKILL.md": b"c"}}},
    )
    target_local = tmp_path / "workspace" / ".kiro"
    target_global = tmp_path / "home" / ".kiro"
    ksm_dir = tmp_path / "ksm_state"
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
    manifest = Manifest(entries=[])

    args = _make_args(bundle_spec="aws.skills.nonexistent")
    code = run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=target_global,
    )

    assert code == 1
    captured = capsys.readouterr()
    assert "nonexistent" in captured.err


def test_run_add_no_bundle_spec_prints_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_add with no bundle_spec and no --display prints error."""
    from ksm.commands.add import run_add

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir()
    idx = RegistryIndex(registries=[])
    manifest = Manifest(entries=[])

    args = _make_args(bundle_spec=None)  # no bundle_spec, no display
    code = run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=tmp_path / "local",
        target_global=tmp_path / "global",
    )

    assert code == 1
    captured = capsys.readouterr()
    assert "no bundle specified" in captured.err.lower()


def test_run_add_invalid_subdirectory_in_dot_notation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_add with invalid subdirectory in dot notation prints error."""
    from ksm.commands.add import run_add

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir()
    idx = RegistryIndex(registries=[])
    manifest = Manifest(entries=[])

    # "aws.badsubdir.item" — badsubdir is not a valid subdirectory
    args = _make_args(bundle_spec="aws.badsubdir.item")
    code = run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=tmp_path / "local",
        target_global=tmp_path / "global",
    )

    assert code == 1
    captured = capsys.readouterr()
    assert "error" in captured.err.lower()


def test_run_add_install_system_exit(
    tmp_path: Path,
) -> None:
    """run_add returns 1 when install_bundle raises SystemExit."""
    from ksm.commands.add import run_add

    reg_path = tmp_path / "registries" / "default"
    bundle_path = reg_path / "aws"
    (bundle_path / "skills").mkdir(parents=True)
    (bundle_path / "skills" / "f.md").write_text("x")

    target_local = tmp_path / "local"
    target_local.mkdir()

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg_path),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(entries=[])

    args = _make_args(bundle_spec="aws")
    with patch(
        "ksm.commands.add.install_bundle",
        side_effect=SystemExit(1),
    ):
        code = run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=tmp_path / "manifest.json",
            target_local=target_local,
            target_global=tmp_path / "global",
        )

    assert code == 1


def test_run_add_ephemeral_dot_notation_missing_item(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_add --from with dot notation for missing item prints error."""
    from ksm.commands.add import run_add

    clone_dir = tmp_path / "clone"
    bundle_path = clone_dir / "aws"
    (bundle_path / "skills").mkdir(parents=True)
    (bundle_path / "skills" / "existing.md").write_text("x")

    target_local = tmp_path / "local"
    target_local.mkdir()

    idx = RegistryIndex(registries=[])
    manifest = Manifest(entries=[])

    args = _make_args(
        bundle_spec="aws.skills.nonexistent",
        from_url="https://example.com/repo.git",
    )
    with patch(
        "ksm.commands.add.clone_ephemeral",
        return_value=clone_dir,
    ):
        code = run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=tmp_path / "manifest.json",
            target_local=target_local,
            target_global=tmp_path / "global",
        )

    assert code == 1
    captured = capsys.readouterr()
    assert "nonexistent" in captured.err


def test_run_add_ephemeral_install_system_exit(
    tmp_path: Path,
) -> None:
    """run_add --from returns 1 when install_bundle raises SystemExit."""
    from ksm.commands.add import run_add

    clone_dir = tmp_path / "clone"
    bundle_path = clone_dir / "aws"
    (bundle_path / "skills").mkdir(parents=True)
    (bundle_path / "skills" / "f.md").write_text("x")

    target_local = tmp_path / "local"
    target_local.mkdir()

    idx = RegistryIndex(registries=[])
    manifest = Manifest(entries=[])

    args = _make_args(
        bundle_spec="aws",
        from_url="https://example.com/repo.git",
    )
    with (
        patch(
            "ksm.commands.add.clone_ephemeral",
            return_value=clone_dir,
        ),
        patch(
            "ksm.commands.add.install_bundle",
            side_effect=SystemExit(1),
        ),
    ):
        code = run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=tmp_path / "manifest.json",
            target_local=target_local,
            target_global=tmp_path / "global",
        )

    assert code == 1


# --- Property-based tests ---


# Feature: kiro-settings-manager, Property 1: Scope flag determines target directory
@given(
    use_global=st.booleans(),
)
def test_property_scope_flag_determines_target(
    use_global: bool,
) -> None:
    """Property 1: Scope flag determines target directory."""
    import tempfile

    from ksm.commands.add import run_add

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg" / "b" / "skills"
        reg.mkdir(parents=True)
        (reg / "f.md").write_bytes(b"x")

        target_local = base / "local" / ".kiro"
        target_global = base / "global" / ".kiro"
        ksm_dir = base / "ksm"
        ksm_dir.mkdir()

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(base / "reg"),
                    is_default=True,
                )
            ]
        )
        manifest = Manifest(entries=[])

        args = _make_args(
            bundle_spec="b",
            global_=use_global,
            local=not use_global,
        )
        run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target_local,
            target_global=target_global,
        )

        if use_global:
            assert (target_global / "skills" / "f.md").exists()
            assert not target_local.exists()
            assert manifest.entries[0].scope == "global"
        else:
            assert (target_local / "skills" / "f.md").exists()
            assert not target_global.exists()
            assert manifest.entries[0].scope == "local"


# Feature: kiro-settings-manager, Property 21: Ephemeral registry is not persisted
@given(data=st.data())
def test_property_ephemeral_not_persisted(
    data: st.DataObject,
) -> None:
    """Property 21: Ephemeral registry is not persisted."""
    import tempfile

    from ksm.commands.add import run_add

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        eph = base / "eph" / "b" / "skills"
        eph.mkdir(parents=True)
        (eph / "f.md").write_bytes(b"x")

        target_local = base / "local" / ".kiro"
        target_global = base / "global" / ".kiro"
        ksm_dir = base / "ksm"
        ksm_dir.mkdir()

        idx = RegistryIndex(registries=[])
        registries_before = list(idx.registries)
        manifest = Manifest(entries=[])

        args = _make_args(
            bundle_spec="b",
            from_url="https://example.com/repo.git",
        )

        with patch(
            "ksm.commands.add.clone_ephemeral",
            return_value=base / "eph",
        ):
            with patch("ksm.commands.add.shutil.rmtree"):
                run_add(
                    args,
                    registry_index=idx,
                    manifest=manifest,
                    manifest_path=ksm_dir / "manifest.json",
                    target_local=target_local,
                    target_global=target_global,
                )

        assert idx.registries == registries_before


# Feature: kiro-settings-manager, Property 23: Ephemeral source recorded as git URL
@given(
    url=st.from_regex(
        r"https://github\.com/[a-z]{1,5}/[a-z]{1,5}\.git",
        fullmatch=True,
    ),
)
def test_property_ephemeral_source_recorded_as_url(
    url: str,
) -> None:
    """Property 23: Ephemeral source recorded as git URL."""
    import tempfile

    from ksm.commands.add import run_add

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        eph = base / "eph" / "b" / "skills"
        eph.mkdir(parents=True)
        (eph / "f.md").write_bytes(b"x")

        target_local = base / "local" / ".kiro"
        target_global = base / "global" / ".kiro"
        ksm_dir = base / "ksm"
        ksm_dir.mkdir()

        idx = RegistryIndex(registries=[])
        manifest = Manifest(entries=[])

        args = _make_args(bundle_spec="b", from_url=url)

        with patch(
            "ksm.commands.add.clone_ephemeral",
            return_value=base / "eph",
        ):
            with patch("ksm.commands.add.shutil.rmtree"):
                run_add(
                    args,
                    registry_index=idx,
                    manifest=manifest,
                    manifest_path=ksm_dir / "manifest.json",
                    target_local=target_local,
                    target_global=target_global,
                )

        assert manifest.entries[0].source_registry == url


# Feature: kiro-settings-manager, Property 29: Dot notation missing item produces error
@given(
    subdir=st.sampled_from(["skills", "steering", "hooks", "agents"]),
)
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_dot_notation_missing_item_error(
    subdir: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Property 29: Dot notation missing item produces error."""
    import tempfile

    from ksm.commands.add import run_add

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg" / "b" / subdir
        reg.mkdir(parents=True)
        (reg / "existing.md").write_bytes(b"x")

        target_local = base / "local" / ".kiro"
        target_global = base / "global" / ".kiro"
        ksm_dir = base / "ksm"
        ksm_dir.mkdir()

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(base / "reg"),
                    is_default=True,
                )
            ]
        )
        manifest = Manifest(entries=[])

        args = _make_args(
            bundle_spec=f"b.{subdir}.nonexistent",
        )
        code = run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target_local,
            target_global=target_global,
        )

        assert code == 1
        captured = capsys.readouterr()
        assert "nonexistent" in captured.err


# Feature: kiro-settings-manager, Property 30: Dot notation copies correct item type
@given(
    is_dir=st.booleans(),
)
def test_property_dot_notation_copies_correct_type(
    is_dir: bool,
) -> None:
    """Property 30: Dot notation copies correct item type."""
    import tempfile

    from ksm.commands.add import run_add

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg" / "b" / "skills"
        reg.mkdir(parents=True)

        if is_dir:
            item_dir = reg / "my-item"
            item_dir.mkdir()
            (item_dir / "SKILL.md").write_bytes(b"content")
        else:
            (reg / "my-item.md").write_bytes(b"content")

        target_local = base / "local" / ".kiro"
        target_global = base / "global" / ".kiro"
        ksm_dir = base / "ksm"
        ksm_dir.mkdir()

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="default",
                    url=None,
                    local_path=str(base / "reg"),
                    is_default=True,
                )
            ]
        )
        manifest = Manifest(entries=[])

        item_name = "my-item" if is_dir else "my-item.md"
        args = _make_args(
            bundle_spec=f"b.skills.{item_name}",
        )
        code = run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target_local,
            target_global=target_global,
        )

        assert code == 0
        if is_dir:
            assert (target_local / "skills" / "my-item" / "SKILL.md").exists()
        else:
            assert (target_local / "skills" / "my-item.md").exists()


# Feature: kiro-settings-manager
# Property 31: Dot notation and subdirectory filter
# are mutually exclusive
@given(
    filter_flag=st.sampled_from(
        ["skills_only", "agents_only", "steering_only", "hooks_only"]
    ),
)
def test_property_dot_notation_filter_mutual_exclusion(
    filter_flag: str,
) -> None:
    """Property 31: Dot notation + subdirectory filter = error."""
    import tempfile

    from ksm.commands.add import run_add

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ksm_dir = base / "ksm"
        ksm_dir.mkdir()

        idx = RegistryIndex(registries=[])
        manifest = Manifest(entries=[])

        kwargs = {filter_flag: True}
        args = _make_args(
            bundle_spec="b.skills.item",
            **kwargs,
        )
        code = run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=base / "local" / ".kiro",
            target_global=base / "global" / ".kiro",
        )

        assert code == 1


# Feature: ux-review-fixes, Property 15: Dry-run does not modify state
# (add path)
@given(
    bundle_name=st.from_regex(r"[a-z]{3,10}", fullmatch=True),
    scope=st.sampled_from(["local", "global"]),
)
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_dry_run_add_does_not_modify_state(
    bundle_name: str,
    scope: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Feature: ux-review-fixes, Property 15: Dry-run does not modify
    state (add path)."""
    import tempfile

    from ksm.commands.add import run_add

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg"
        # Create a bundle in the registry
        bdir = reg / bundle_name / "skills"
        bdir.mkdir(parents=True)
        (bdir / "SKILL.md").write_bytes(b"skill content")

        target_local = base / "workspace" / ".kiro"
        target_global = base / "home" / ".kiro"
        target = target_global if scope == "global" else target_local

        ksm_dir = base / "ksm"
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
        manifest = Manifest(entries=[])

        args = _make_args(
            bundle_spec=bundle_name,
            global_=(scope == "global"),
            local=(scope == "local"),
            dry_run=True,
        )

        code = run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target_local,
            target_global=target_global,
        )

        assert code == 0
        # No files should be installed
        assert not target.exists() or not list(target.rglob("*"))
        # Manifest must remain empty
        assert len(manifest.entries) == 0
        # Preview printed to stderr
        captured = capsys.readouterr()
        assert "would install" in captured.err.lower()
        assert bundle_name in captured.err
