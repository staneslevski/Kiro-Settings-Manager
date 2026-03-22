"""Tests for ksm.commands.add module."""

import argparse
import sys
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
        "display": False,
        "from_url": None,
        "local": False,
        "global_": False,
        "skills_only": False,
        "agents_only": False,
        "steering_only": False,
        "hooks_only": False,
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

    args = _make_args(bundle_spec=None, display=True)

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

    args = _make_args(bundle_spec=None, display=True)

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

    args = _make_args(bundle_spec="aws", skills_only=True)
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
        skills_only=True,
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


# --- Tests for file-level diff output (Req 22) ---


def test_run_add_prints_diff_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_add prints file-level diff summary after install."""
    from ksm.commands.add import run_add

    reg = _setup_registry(
        tmp_path,
        {"aws": {"skills": {"S.md": b"skill"}}},
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
    captured = capsys.readouterr()
    # Should contain diff symbol for new file
    assert "+" in captured.err or "new" in captured.err.lower()


# --- Tests for auto-launch selector (Req 9) ---


def test_run_add_auto_launch_tty(
    tmp_path: Path,
) -> None:
    """run_add auto-launches selector when no bundle_spec + TTY."""
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

    args = _make_args(bundle_spec=None)

    with (
        patch("sys.stdin") as mock_stdin,
        patch(
            "ksm.commands.add.interactive_select",
            return_value=["aws"],
        ) as mock_sel,
        patch(
            "ksm.commands.add.scope_select",
            return_value="local",
        ),
    ):
        mock_stdin.isatty.return_value = True
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


def test_run_add_auto_launch_tty_quit(
    tmp_path: Path,
) -> None:
    """run_add auto-launch returns 0 when user quits."""
    from ksm.commands.add import run_add

    reg = _setup_registry(
        tmp_path,
        {"aws": {"skills": {"S.md": b"s"}}},
    )
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

    args = _make_args(bundle_spec=None)

    with (
        patch("sys.stdin") as mock_stdin,
        patch(
            "ksm.commands.add.interactive_select",
            return_value=None,
        ),
    ):
        mock_stdin.isatty.return_value = True
        code = run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=tmp_path / "local",
            target_global=tmp_path / "global",
        )

    assert code == 0
    assert len(manifest.entries) == 0


def test_run_add_non_tty_no_bundle_prints_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_add with no bundle_spec + non-TTY prints error."""
    from ksm.commands.add import run_add

    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir()
    idx = RegistryIndex(registries=[])
    manifest = Manifest(entries=[])

    args = _make_args(bundle_spec=None)

    with patch("sys.stdin") as mock_stdin:
        mock_stdin.isatty.return_value = False
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


def test_run_add_versioned_install_error_with_available(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Versioned install error shows available versions."""
    from ksm.commands.add import run_add
    from ksm.errors import GitError

    reg = _setup_registry(
        tmp_path,
        {"mybundle": {"skills": {"S.md": b"skill"}}},
    )
    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url="https://example.com",
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(entries=[])
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir()

    args = _make_args(bundle_spec="mybundle@v999")

    with patch(
        "ksm.commands.add.checkout_version",
        side_effect=GitError("not found"),
    ):
        with patch(
            "ksm.commands.add.list_versions",
            return_value=["v1.0.0", "v2.0.0"],
        ):
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=tmp_path / "local" / ".kiro",
                target_global=tmp_path / "global" / ".kiro",
            )

    assert code == 1
    captured = capsys.readouterr()
    assert "v999" in captured.err
    assert "v1.0.0" in captured.err
    assert "v2.0.0" in captured.err


def test_run_add_versioned_install_error_no_available(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Versioned install error with no available versions."""
    from ksm.commands.add import run_add
    from ksm.errors import GitError

    reg = _setup_registry(
        tmp_path,
        {"mybundle": {"skills": {"S.md": b"skill"}}},
    )
    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url="https://example.com",
                local_path=str(reg),
                is_default=True,
            )
        ]
    )
    manifest = Manifest(entries=[])
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir()

    args = _make_args(bundle_spec="mybundle@v999")

    with patch(
        "ksm.commands.add.checkout_version",
        side_effect=GitError("not found"),
    ):
        with patch(
            "ksm.commands.add.list_versions",
            return_value=[],
        ):
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=tmp_path / "local" / ".kiro",
                target_global=tmp_path / "global" / ".kiro",
            )

    assert code == 1
    captured = capsys.readouterr()
    assert "v999" in captured.err
    assert "no versions available" in captured.err.lower()


# --- 5.3 Qualified name and ambiguity tests ---


def test_run_add_qualified_name_resolves(
    tmp_path: Path,
) -> None:
    """run_add with registry/bundle syntax resolves correctly."""
    from ksm.commands.add import run_add

    reg1 = tmp_path / "reg1"
    (reg1 / "aws" / "skills").mkdir(parents=True)
    (reg1 / "aws" / "skills" / "S.md").write_bytes(b"s1")

    reg2 = tmp_path / "reg2"
    (reg2 / "aws" / "steering").mkdir(parents=True)
    (reg2 / "aws" / "steering" / "T.md").write_bytes(b"s2")

    target_local = tmp_path / "workspace" / ".kiro"
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir()

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="first",
                url=None,
                local_path=str(reg1),
                is_default=True,
            ),
            RegistryEntry(
                name="second",
                url=None,
                local_path=str(reg2),
                is_default=False,
            ),
        ]
    )
    manifest = Manifest(entries=[])

    args = _make_args(bundle_spec="first/aws")
    code = run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    # Should install from first registry (skills)
    assert (target_local / "skills" / "S.md").exists()
    # Should NOT install from second registry (steering)
    assert not (target_local / "steering").exists()


def test_run_add_ambiguous_unqualified_name_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_add with ambiguous unqualified name prints error."""
    from ksm.commands.add import run_add

    reg1 = tmp_path / "reg1"
    (reg1 / "aws" / "skills").mkdir(parents=True)
    (reg1 / "aws" / "skills" / "S.md").write_bytes(b"s1")

    reg2 = tmp_path / "reg2"
    (reg2 / "aws" / "steering").mkdir(parents=True)
    (reg2 / "aws" / "steering" / "T.md").write_bytes(b"s2")

    target_local = tmp_path / "workspace" / ".kiro"
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir()

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="first",
                url=None,
                local_path=str(reg1),
                is_default=True,
            ),
            RegistryEntry(
                name="second",
                url=None,
                local_path=str(reg2),
                is_default=False,
            ),
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
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 1
    captured = capsys.readouterr()
    assert "multiple registries" in captured.err.lower()
    assert "first" in captured.err
    assert "second" in captured.err
    assert "<registry>/aws" in captured.err


def test_run_add_interactive_ignored_when_bundle_spec(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """-i is ignored when bundle_spec is provided."""
    from ksm.commands.add import run_add

    reg = _setup_registry(
        tmp_path,
        {"aws": {"skills": {"S.md": b"s"}}},
    )
    target_local = tmp_path / "workspace" / ".kiro"
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
    manifest = Manifest(entries=[])

    args = _make_args(bundle_spec="aws", interactive=True)
    code = run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    captured = capsys.readouterr()
    assert "-i ignored" in captured.err.lower() or (
        "-i" in captured.err and "ignored" in captured.err.lower()
    )
    # Bundle should still be installed
    assert (target_local / "skills" / "S.md").exists()


def test_run_add_display_prints_deprecation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--display prints deprecation warning and behaves as -i."""
    from ksm.commands.add import run_add

    reg = _setup_registry(
        tmp_path,
        {"aws": {"skills": {"S.md": b"s"}}},
    )
    target_local = tmp_path / "workspace" / ".kiro"
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
    manifest = Manifest(entries=[])

    args = _make_args(bundle_spec=None, display=True)

    with patch(
        "ksm.commands.add.interactive_select",
        return_value=["aws"],
    ):
        code = run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=ksm_dir / "manifest.json",
            target_local=target_local,
            target_global=tmp_path / "global" / ".kiro",
        )

    assert code == 0
    captured = capsys.readouterr()
    assert "deprecated" in captured.err.lower()
    assert "--display" in captured.err
    assert (target_local / "skills" / "S.md").exists()


# ── Phase 6: --only consolidation tests ──────────────────────


def test_build_subdirectory_filter_only_comma_separated() -> None:
    """--only with comma-separated values produces correct set."""
    from ksm.commands.add import _build_subdirectory_filter

    args = _make_args(only=["skills,hooks"])
    result = _build_subdirectory_filter(args)
    assert result == {"skills", "hooks"}


def test_build_subdirectory_filter_only_repeated() -> None:
    """Repeated --only flags accumulate values."""
    from ksm.commands.add import _build_subdirectory_filter

    args = _make_args(only=["skills", "agents"])
    result = _build_subdirectory_filter(args)
    assert result == {"skills", "agents"}


def test_build_subdirectory_filter_only_comma_and_repeated() -> None:
    """Mixed comma-separated and repeated --only flags."""
    from ksm.commands.add import _build_subdirectory_filter

    args = _make_args(only=["skills,hooks", "agents"])
    result = _build_subdirectory_filter(args)
    assert result == {"skills", "hooks", "agents"}


def test_build_subdirectory_filter_only_invalid_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Invalid --only value raises SystemExit(2)."""
    from ksm.commands.add import _build_subdirectory_filter

    args = _make_args(only=["badvalue"])
    with pytest.raises(SystemExit) as exc_info:
        _build_subdirectory_filter(args)
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "badvalue" in captured.err
    assert "skills" in captured.err
    assert "agents" in captured.err
    assert "steering" in captured.err
    assert "hooks" in captured.err


def test_build_subdirectory_filter_only_mixed_valid_invalid(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Comma list with one invalid value raises SystemExit(2)."""
    from ksm.commands.add import _build_subdirectory_filter

    args = _make_args(only=["skills,nope"])
    with pytest.raises(SystemExit) as exc_info:
        _build_subdirectory_filter(args)
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "nope" in captured.err


def test_build_subdirectory_filter_deprecated_skills_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--skills-only emits deprecation warning and returns {skills}."""
    from ksm.commands.add import _build_subdirectory_filter

    args = _make_args(skills_only=True)
    result = _build_subdirectory_filter(args)
    assert result == {"skills"}
    captured = capsys.readouterr()
    assert "deprecated" in captured.err.lower()
    assert "--skills-only" in captured.err
    assert "--only skills" in captured.err


def test_build_subdirectory_filter_deprecated_agents_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--agents-only emits deprecation warning and returns {agents}."""
    from ksm.commands.add import _build_subdirectory_filter

    args = _make_args(agents_only=True)
    result = _build_subdirectory_filter(args)
    assert result == {"agents"}
    captured = capsys.readouterr()
    assert "deprecated" in captured.err.lower()
    assert "--agents-only" in captured.err
    assert "--only agents" in captured.err


def test_build_subdirectory_filter_deprecated_steering_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--steering-only emits deprecation warning."""
    from ksm.commands.add import _build_subdirectory_filter

    args = _make_args(steering_only=True)
    result = _build_subdirectory_filter(args)
    assert result == {"steering"}
    captured = capsys.readouterr()
    assert "deprecated" in captured.err.lower()
    assert "--steering-only" in captured.err
    assert "--only steering" in captured.err


def test_build_subdirectory_filter_deprecated_hooks_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--hooks-only emits deprecation warning."""
    from ksm.commands.add import _build_subdirectory_filter

    args = _make_args(hooks_only=True)
    result = _build_subdirectory_filter(args)
    assert result == {"hooks"}
    captured = capsys.readouterr()
    assert "deprecated" in captured.err.lower()
    assert "--hooks-only" in captured.err
    assert "--only hooks" in captured.err


def test_build_subdirectory_filter_deprecated_multiple(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Multiple deprecated flags combine and each emits warning."""
    from ksm.commands.add import _build_subdirectory_filter

    args = _make_args(skills_only=True, hooks_only=True)
    result = _build_subdirectory_filter(args)
    assert result == {"skills", "hooks"}
    captured = capsys.readouterr()
    assert "--skills-only" in captured.err
    assert "--hooks-only" in captured.err


def test_build_subdirectory_filter_none_when_no_flags() -> None:
    """No --only or --*-only flags returns None."""
    from ksm.commands.add import _build_subdirectory_filter

    args = _make_args()
    result = _build_subdirectory_filter(args)
    assert result is None


def test_run_add_only_with_dot_notation_mutual_exclusion(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--only + dot notation is mutually exclusive (exit 1)."""
    from ksm.commands.add import run_add

    target_local = tmp_path / "workspace" / ".kiro"
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir()

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
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 1
    captured = capsys.readouterr()
    assert "mutually exclusive" in captured.err.lower()


# ── Property 11: --only comma parsing ────────────────────────


@given(
    values=st.lists(
        st.sampled_from(["skills", "agents", "steering", "hooks"]),
        min_size=1,
        max_size=4,
    ),
)
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_only_comma_parsing_produces_correct_set(
    values: list[str],
) -> None:
    """Property 11: comma-separated --only produces correct set."""
    from ksm.commands.add import _build_subdirectory_filter

    csv_str = ",".join(values)
    args = _make_args(only=[csv_str])
    result = _build_subdirectory_filter(args)
    assert result == set(values)


# ── Property 12: --only invalid value rejection ──────────────


@given(
    bad=st.text(min_size=1, max_size=20).filter(
        lambda s: s.strip() not in {"skills", "agents", "steering", "hooks"}
        and "," not in s
    ),
)
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_only_invalid_value_exits_2(
    bad: str,
) -> None:
    """Property 12: invalid --only value raises SystemExit(2)."""
    from ksm.commands.add import _build_subdirectory_filter

    args = _make_args(only=[bad])
    with pytest.raises(SystemExit) as exc_info:
        _build_subdirectory_filter(args)
    assert exc_info.value.code == 2


# ── Property 13: deprecated --*-only equivalence ─────────────

_DEPRECATED_FLAG_MAP = {
    "skills_only": "skills",
    "agents_only": "agents",
    "steering_only": "steering",
    "hooks_only": "hooks",
}


@given(
    flags=st.lists(
        st.sampled_from(list(_DEPRECATED_FLAG_MAP.keys())),
        min_size=1,
        max_size=4,
        unique=True,
    ),
)
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_property_deprecated_only_flags_equivalence(
    flags: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Property 13: deprecated flags produce equivalent filter."""
    from ksm.commands.add import _build_subdirectory_filter

    kwargs = {f: True for f in flags}
    args = _make_args(**kwargs)
    result = _build_subdirectory_filter(args)

    expected = {_DEPRECATED_FLAG_MAP[f] for f in flags}
    assert result == expected

    captured = capsys.readouterr()
    for f in flags:
        flag_name = f"--{f.replace('_', '-')}"
        assert flag_name in captured.err
        assert "deprecated" in captured.err.lower()


def test_run_add_dry_run_prints_preview(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_add with --dry-run prints preview without installing."""
    from ksm.commands.add import run_add

    reg = tmp_path / "reg"
    (reg / "aws" / "skills").mkdir(parents=True)
    (reg / "aws" / "skills" / "S.md").write_bytes(b"data")

    target_local = tmp_path / "workspace" / ".kiro"
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
    manifest = Manifest(entries=[])

    args = _make_args(bundle_spec="aws", dry_run=True)
    code = run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    # Should NOT install anything
    assert not (target_local / "skills").exists()
    captured = capsys.readouterr()
    assert "Would install" in captured.err


def test_run_add_dry_run_with_subdirectory_filter(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_add dry-run shows subdirectory filter in preview."""
    from ksm.commands.add import run_add

    reg = tmp_path / "reg"
    (reg / "aws" / "skills").mkdir(parents=True)
    (reg / "aws" / "skills" / "S.md").write_bytes(b"data")

    target_local = tmp_path / "workspace" / ".kiro"
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
    manifest = Manifest(entries=[])

    args = _make_args(
        bundle_spec="aws",
        dry_run=True,
        only=["skills"],
    )
    code = run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 0
    captured = capsys.readouterr()
    assert "Subdirectories:" in captured.err
    assert "skills" in captured.err


def test_run_add_qualified_name_not_found_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_add with qualified name for missing bundle prints error."""
    from ksm.commands.add import run_add

    reg = tmp_path / "reg"
    (reg / "aws" / "skills").mkdir(parents=True)
    (reg / "aws" / "skills" / "S.md").write_bytes(b"data")

    target_local = tmp_path / "workspace" / ".kiro"
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
    manifest = Manifest(entries=[])

    # Use a qualified name where the registry exists but bundle doesn't
    args = _make_args(bundle_spec="default/nonexistent")
    code = run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=tmp_path / "global" / ".kiro",
    )

    assert code == 1
    captured = capsys.readouterr()
    assert "error:" in captured.err


# --- Tests for stream=sys.stderr in formatter calls (Reqs 1.1-1.3, 2.1-2.3) ---


class TestAddFormatterStreamParam:
    """Verify add.py passes stream=sys.stderr to formatters."""

    def test_format_error_receives_stream_stderr_on_invalid_only(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """format_error called with stream=sys.stderr for
        invalid --only value."""
        from ksm.commands.add import _build_subdirectory_filter

        args = _make_args(only=["badvalue"])
        with (
            patch(
                "ksm.commands.add.format_error",
                wraps=__import__("ksm.errors", fromlist=["format_error"]).format_error,
            ) as mock_fmt,
            pytest.raises(SystemExit),
        ):
            _build_subdirectory_filter(args)

        mock_fmt.assert_called_once()
        _, kwargs = mock_fmt.call_args
        assert kwargs.get("stream") is sys.stderr

    def test_format_error_receives_stream_stderr_no_bundle(
        self,
        tmp_path: Path,
    ) -> None:
        """format_error called with stream=sys.stderr when
        no bundle specified (non-TTY)."""
        from ksm.commands.add import run_add

        ksm_dir = tmp_path / "ksm"
        ksm_dir.mkdir()
        idx = RegistryIndex(registries=[])
        manifest = Manifest(entries=[])
        args = _make_args(bundle_spec=None)

        with (
            patch("sys.stdin") as mock_stdin,
            patch(
                "ksm.commands.add.format_error",
                wraps=__import__("ksm.errors", fromlist=["format_error"]).format_error,
            ) as mock_fmt,
        ):
            mock_stdin.isatty.return_value = False
            run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=tmp_path / "local",
                target_global=tmp_path / "global",
            )

        assert mock_fmt.call_count >= 1
        _, kwargs = mock_fmt.call_args
        assert kwargs.get("stream") is sys.stderr

    def test_format_warning_receives_stream_stderr(
        self,
        tmp_path: Path,
    ) -> None:
        """format_warning called with stream=sys.stderr when
        -i ignored because bundle specified."""
        from ksm.commands.add import run_add

        reg = _setup_registry(
            tmp_path,
            {"aws": {"skills": {"S.md": b"s"}}},
        )
        target_local = tmp_path / "workspace" / ".kiro"
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
        manifest = Manifest(entries=[])
        args = _make_args(bundle_spec="aws", interactive=True)

        with patch(
            "ksm.commands.add.format_warning",
            wraps=__import__("ksm.errors", fromlist=["format_warning"]).format_warning,
        ) as mock_fmt:
            run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=target_local,
                target_global=tmp_path / "global" / ".kiro",
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
        from ksm.commands.add import run_add

        reg = _setup_registry(
            tmp_path,
            {"aws": {"skills": {"S.md": b"s"}}},
        )
        target_local = tmp_path / "workspace" / ".kiro"
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
        manifest = Manifest(entries=[])
        args = _make_args(bundle_spec=None, display=True)

        with (
            patch(
                "ksm.commands.add.interactive_select",
                return_value=["aws"],
            ),
            patch(
                "ksm.commands.add.format_deprecation",
                wraps=__import__(
                    "ksm.errors",
                    fromlist=["format_deprecation"],
                ).format_deprecation,
            ) as mock_fmt,
        ):
            run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=target_local,
                target_global=tmp_path / "global" / ".kiro",
            )

        assert mock_fmt.call_count >= 1
        _, kwargs = mock_fmt.call_args
        assert kwargs.get("stream") is sys.stderr

    def test_deprecated_only_flag_passes_stream_stderr(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """format_deprecation called with stream=sys.stderr
        for deprecated --skills-only flag."""
        from ksm.commands.add import (
            _build_subdirectory_filter,
        )

        args = _make_args(skills_only=True)

        with patch(
            "ksm.commands.add.format_deprecation",
            wraps=__import__(
                "ksm.errors",
                fromlist=["format_deprecation"],
            ).format_deprecation,
        ) as mock_fmt:
            _build_subdirectory_filter(args)

        mock_fmt.assert_called_once()
        _, kwargs = mock_fmt.call_args
        assert kwargs.get("stream") is sys.stderr


# --- Tests for green success prefix (Req 3.1, 3.4, 3.5) ---
# Feature: color-and-scope-selection
# **Validates: Requirements 3.1, 3.4, 3.5**


class TestAddGreenSuccessPrefix:
    """Property 12: add success message includes
    success-styled checkmark and bundle name."""

    _SUCCESS = "\033[92m"
    _RESET = "\033[0m"

    def test_installed_prefix_success_on_tty(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Property 12: successful add prints success-styled
        checkmark to stderr when stream is TTY."""
        from ksm.commands.add import run_add

        reg = _setup_registry(
            tmp_path,
            {"aws": {"skills": {"S.md": b"skill"}}},
        )
        target_local = tmp_path / "workspace" / ".kiro"
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

        with patch.dict(
            "os.environ",
            {"TERM": "xterm-256color"},
            clear=True,
        ):
            with patch(
                "sys.stderr.isatty",
                return_value=True,
            ):
                code = run_add(
                    args,
                    registry_index=idx,
                    manifest=manifest,
                    manifest_path=(ksm_dir / "manifest.json"),
                    target_local=target_local,
                    target_global=(tmp_path / "home" / ".kiro"),
                )

        assert code == 0
        captured = capsys.readouterr()
        assert "Installed" in captured.err
        assert self._SUCCESS in captured.err

    def test_installed_prefix_plain_with_no_color(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Property 12: output is plain text when NO_COLOR set."""
        from ksm.commands.add import run_add

        reg = _setup_registry(
            tmp_path,
            {"aws": {"skills": {"S.md": b"skill"}}},
        )
        target_local = tmp_path / "workspace" / ".kiro"
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

        with patch.dict(
            "os.environ",
            {"NO_COLOR": "1"},
            clear=False,
        ):
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=(ksm_dir / "manifest.json"),
                target_local=target_local,
                target_global=(tmp_path / "home" / ".kiro"),
            )

        assert code == 0
        captured = capsys.readouterr()
        assert "Installed" in captured.err
        assert "\033[" not in captured.err

    def test_installed_prefix_contains_bundle_name(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Property 12: success message includes bundle name
        alongside the green prefix.
        **Validates: Requirements 3.5**"""
        from ksm.commands.add import run_add

        reg = _setup_registry(
            tmp_path,
            {"mybundle": {"skills": {"S.md": b"s"}}},
        )
        target_local = tmp_path / "workspace" / ".kiro"
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
        args = _make_args(bundle_spec="mybundle")

        code = run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=(ksm_dir / "manifest.json"),
            target_local=target_local,
            target_global=(tmp_path / "home" / ".kiro"),
        )

        assert code == 0
        captured = capsys.readouterr()
        assert "Installed" in captured.err
        assert "mybundle" in captured.err


# --- Tests for scope selection integration (Reqs 11, 15) ---
# Feature: color-and-scope-selection
# **Validates: Requirements 11.1, 11.5, 11.7, 15.1, 15.2, 15.3, 15.4**


class TestScopeSelectionIntegration:
    """Tests for scope_select integration in add.py.

    Property 36: interactive add calls scope_select
        when no -l/-g flag
    Property 37: interactive add skips scope_select
        when -l or -g provided
    Property 38: interactive add defaults to "local"
        when stdin not TTY
    Property 39: scope_select abort returns exit code 0
    Property 40: selected scope is passed to install_bundle
    """

    def _setup(self, tmp_path: Path) -> tuple[
        RegistryIndex,
        Manifest,
        Path,
        Path,
        Path,
        Path,
    ]:
        """Common setup for scope integration tests."""
        reg = _setup_registry(
            tmp_path,
            {"aws": {"skills": {"S.md": b"skill"}}},
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
        return (
            idx,
            manifest,
            ksm_dir,
            target_local,
            target_global,
            reg,
        )

    # -- Property 36: interactive add calls scope_select
    #    when no -l/-g flag --
    # **Validates: Requirements 11.1**

    def test_scope_select_called_in_interactive_mode(
        self,
        tmp_path: Path,
    ) -> None:
        """Property 36: scope_select is called when
        -i is used and neither -l nor -g is provided.
        **Validates: Requirements 11.1**"""
        from ksm.commands.add import run_add

        (
            idx,
            manifest,
            ksm_dir,
            target_local,
            target_global,
            _,
        ) = self._setup(tmp_path)

        args = _make_args(
            bundle_spec=None,
            display=True,
        )

        with (
            patch("sys.stdin") as mock_stdin,
            patch(
                "ksm.commands.add.interactive_select",
                return_value=["aws"],
            ),
            patch(
                "ksm.commands.add.scope_select",
                return_value="local",
            ) as mock_scope,
        ):
            mock_stdin.isatty.return_value = True
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=(ksm_dir / "manifest.json"),
                target_local=target_local,
                target_global=target_global,
            )

        assert code == 0
        mock_scope.assert_called_once()

    def test_scope_select_called_auto_launch_tty(
        self,
        tmp_path: Path,
    ) -> None:
        """Property 36: scope_select is called on
        auto-launch (no bundle_spec, TTY stdin).
        **Validates: Requirements 11.1**"""
        from ksm.commands.add import run_add

        (
            idx,
            manifest,
            ksm_dir,
            target_local,
            target_global,
            _,
        ) = self._setup(tmp_path)

        args = _make_args(bundle_spec=None)

        with (
            patch("sys.stdin") as mock_stdin,
            patch(
                "ksm.commands.add.interactive_select",
                return_value=["aws"],
            ),
            patch(
                "ksm.commands.add.scope_select",
                return_value="local",
            ) as mock_scope,
        ):
            mock_stdin.isatty.return_value = True
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=(ksm_dir / "manifest.json"),
                target_local=target_local,
                target_global=target_global,
            )

        assert code == 0
        mock_scope.assert_called_once()

    # -- Property 37: interactive add skips scope_select
    #    when -l or -g provided --
    # **Validates: Requirements 11.5, 15.3**

    def test_scope_select_skipped_when_local_flag(
        self,
        tmp_path: Path,
    ) -> None:
        """Property 37: scope_select is NOT called when
        -l flag is provided.
        **Validates: Requirements 11.5, 15.3**"""
        from ksm.commands.add import run_add

        (
            idx,
            manifest,
            ksm_dir,
            target_local,
            target_global,
            _,
        ) = self._setup(tmp_path)

        args = _make_args(
            bundle_spec=None,
            display=True,
            local=True,
        )

        with (
            patch(
                "ksm.commands.add.interactive_select",
                return_value=["aws"],
            ),
            patch(
                "ksm.commands.add.scope_select",
                return_value="local",
            ) as mock_scope,
        ):
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=(ksm_dir / "manifest.json"),
                target_local=target_local,
                target_global=target_global,
            )

        assert code == 0
        mock_scope.assert_not_called()

    def test_scope_select_skipped_when_global_flag(
        self,
        tmp_path: Path,
    ) -> None:
        """Property 37: scope_select is NOT called when
        -g flag is provided.
        **Validates: Requirements 11.5, 15.3**"""
        from ksm.commands.add import run_add

        (
            idx,
            manifest,
            ksm_dir,
            target_local,
            target_global,
            _,
        ) = self._setup(tmp_path)

        args = _make_args(
            bundle_spec=None,
            display=True,
            global_=True,
        )

        with (
            patch(
                "ksm.commands.add.interactive_select",
                return_value=["aws"],
            ),
            patch(
                "ksm.commands.add.scope_select",
                return_value="global",
            ) as mock_scope,
        ):
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=(ksm_dir / "manifest.json"),
                target_local=target_local,
                target_global=target_global,
            )

        assert code == 0
        mock_scope.assert_not_called()

    # -- Property 38: interactive add defaults to "local"
    #    when stdin not TTY --
    # **Validates: Requirements 11.7**

    def test_defaults_to_local_when_stdin_not_tty(
        self,
        tmp_path: Path,
    ) -> None:
        """Property 38: when stdin is not a TTY,
        scope_select is skipped and scope defaults
        to "local".
        **Validates: Requirements 11.7**"""
        from ksm.commands.add import run_add

        (
            idx,
            manifest,
            ksm_dir,
            target_local,
            target_global,
            _,
        ) = self._setup(tmp_path)

        args = _make_args(
            bundle_spec=None,
            display=True,
        )

        with (
            patch(
                "ksm.commands.add.interactive_select",
                return_value=["aws"],
            ),
            patch("sys.stdin") as mock_stdin,
            patch(
                "ksm.commands.add.scope_select",
                return_value="local",
            ) as mock_scope,
        ):
            mock_stdin.isatty.return_value = False
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=(ksm_dir / "manifest.json"),
                target_local=target_local,
                target_global=target_global,
            )

        assert code == 0
        mock_scope.assert_not_called()
        # Should install to local (default)
        assert manifest.entries[0].scope == "local"

    # -- Property 39: scope_select abort returns exit 0 --
    # **Validates: Requirements 11.1, 15.1**

    def test_scope_select_abort_returns_zero(
        self,
        tmp_path: Path,
    ) -> None:
        """Property 39: when scope_select returns None
        (user aborted), run_add returns exit code 0.
        **Validates: Requirements 11.1**"""
        from ksm.commands.add import run_add

        (
            idx,
            manifest,
            ksm_dir,
            target_local,
            target_global,
            _,
        ) = self._setup(tmp_path)

        args = _make_args(
            bundle_spec=None,
            display=True,
        )

        with (
            patch("sys.stdin") as mock_stdin,
            patch(
                "ksm.commands.add.interactive_select",
                return_value=["aws"],
            ),
            patch(
                "ksm.commands.add.scope_select",
                return_value=None,
            ),
        ):
            mock_stdin.isatty.return_value = True
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=(ksm_dir / "manifest.json"),
                target_local=target_local,
                target_global=target_global,
            )

        assert code == 0
        assert len(manifest.entries) == 0

    def test_scope_select_abort_auto_launch_returns_zero(
        self,
        tmp_path: Path,
    ) -> None:
        """Property 39: scope_select abort on auto-launch
        path also returns exit code 0.
        **Validates: Requirements 11.1**"""
        from ksm.commands.add import run_add

        (
            idx,
            manifest,
            ksm_dir,
            target_local,
            target_global,
            _,
        ) = self._setup(tmp_path)

        args = _make_args(bundle_spec=None)

        with (
            patch("sys.stdin") as mock_stdin,
            patch(
                "ksm.commands.add.interactive_select",
                return_value=["aws"],
            ),
            patch(
                "ksm.commands.add.scope_select",
                return_value=None,
            ),
        ):
            mock_stdin.isatty.return_value = True
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=(ksm_dir / "manifest.json"),
                target_local=target_local,
                target_global=target_global,
            )

        assert code == 0
        assert len(manifest.entries) == 0

    # -- Property 40: selected scope is passed to
    #    install_bundle --
    # **Validates: Requirements 15.1, 15.2, 15.4**

    def test_scope_local_passed_to_install_bundle(
        self,
        tmp_path: Path,
    ) -> None:
        """Property 40: when scope_select returns "local",
        install_bundle receives scope="local" and files
        go to target_local.
        **Validates: Requirements 15.1, 15.4**"""
        from ksm.commands.add import run_add

        (
            idx,
            manifest,
            ksm_dir,
            target_local,
            target_global,
            _,
        ) = self._setup(tmp_path)

        args = _make_args(
            bundle_spec=None,
            display=True,
        )

        with (
            patch(
                "ksm.commands.add.interactive_select",
                return_value=["aws"],
            ),
            patch(
                "ksm.commands.add.scope_select",
                return_value="local",
            ),
            patch(
                "ksm.commands.add.install_bundle",
                wraps=__import__(
                    "ksm.installer",
                    fromlist=["install_bundle"],
                ).install_bundle,
            ) as mock_install,
        ):
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=(ksm_dir / "manifest.json"),
                target_local=target_local,
                target_global=target_global,
            )

        assert code == 0
        mock_install.assert_called_once()
        _, kwargs = mock_install.call_args
        assert kwargs["scope"] == "local"
        assert kwargs["target_dir"] == target_local

    def test_scope_global_passed_to_install_bundle(
        self,
        tmp_path: Path,
    ) -> None:
        """Property 40: when scope_select returns "global",
        install_bundle receives scope="global" and files
        go to target_global.
        **Validates: Requirements 15.2, 15.4**"""
        from ksm.commands.add import run_add

        (
            idx,
            manifest,
            ksm_dir,
            target_local,
            target_global,
            _,
        ) = self._setup(tmp_path)

        args = _make_args(
            bundle_spec=None,
            display=True,
        )

        with (
            patch("sys.stdin") as mock_stdin,
            patch(
                "ksm.commands.add.interactive_select",
                return_value=["aws"],
            ),
            patch(
                "ksm.commands.add.scope_select",
                return_value="global",
            ),
            patch(
                "ksm.commands.add.install_bundle",
                wraps=__import__(
                    "ksm.installer",
                    fromlist=["install_bundle"],
                ).install_bundle,
            ) as mock_install,
        ):
            mock_stdin.isatty.return_value = True
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=(ksm_dir / "manifest.json"),
                target_local=target_local,
                target_global=target_global,
            )

        assert code == 0
        mock_install.assert_called_once()
        _, kwargs = mock_install.call_args
        assert kwargs["scope"] == "global"
        assert kwargs["target_dir"] == target_global

    def test_flag_scope_passed_when_selector_skipped(
        self,
        tmp_path: Path,
    ) -> None:
        """Property 40: when -g is provided and
        scope_select is skipped, install_bundle
        receives scope="global".
        **Validates: Requirements 15.3**"""
        from ksm.commands.add import run_add

        (
            idx,
            manifest,
            ksm_dir,
            target_local,
            target_global,
            _,
        ) = self._setup(tmp_path)

        args = _make_args(
            bundle_spec=None,
            display=True,
            global_=True,
        )

        with (
            patch(
                "ksm.commands.add.interactive_select",
                return_value=["aws"],
            ),
            patch(
                "ksm.commands.add.install_bundle",
                wraps=__import__(
                    "ksm.installer",
                    fromlist=["install_bundle"],
                ).install_bundle,
            ) as mock_install,
        ):
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=(ksm_dir / "manifest.json"),
                target_local=target_local,
                target_global=target_global,
            )

        assert code == 0
        mock_install.assert_called_once()
        _, kwargs = mock_install.call_args
        assert kwargs["scope"] == "global"
        assert kwargs["target_dir"] == target_global


# ── Phase 4.2: UX Visual Overhaul — add success output ──────
# Feature: ux-visual-overhaul
# **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**


class TestAddSuccessOutputVisualOverhaul:
    """Tests for add command success output formatting.

    Verifies the output format:
      ✓ Installed <name> → <path> (<scope>)
    with semantic colors: success checkmark, accent name,
    SYM_ARROW, muted scope.
    """

    _SUCCESS_CODE = "\033[92m"
    _ACCENT_CODE = "\033[96m"
    _MUTED_CODE = "\033[2m"
    _RESET = "\033[0m"

    def _run_add_with_color(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        bundle_name: str = "mybundle",
        use_global: bool = False,
    ) -> str:
        """Helper: run add with color enabled, return stderr."""
        from ksm.commands.add import run_add

        reg = _setup_registry(
            tmp_path,
            {bundle_name: {"skills": {"S.md": b"skill"}}},
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
        args = _make_args(
            bundle_spec=bundle_name,
            global_=use_global,
        )

        with patch(
            "ksm.color._color_level", return_value=2
        ):
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=target_local,
                target_global=target_global,
            )

        assert code == 0
        return capsys.readouterr().err

    def test_accent_styled_bundle_name(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 7.1: bundle name styled with accent (96)."""
        err = self._run_add_with_color(
            tmp_path, capsys, "mybundle"
        )
        assert f"{self._ACCENT_CODE}mybundle{self._RESET}" in err

    def test_sym_arrow_in_output(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 7.1: SYM_ARROW present in success line."""
        from ksm.color import SYM_ARROW

        err = self._run_add_with_color(
            tmp_path, capsys
        )
        assert SYM_ARROW in err

    def test_muted_scope_label_local(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 7.1: scope label styled with muted (2)."""
        err = self._run_add_with_color(
            tmp_path, capsys, use_global=False
        )
        assert f"{self._MUTED_CODE}(local){self._RESET}" in err

    def test_muted_scope_label_global(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 7.1: global scope label styled with muted."""
        err = self._run_add_with_color(
            tmp_path, capsys, use_global=True
        )
        assert f"{self._MUTED_CODE}(global){self._RESET}" in err

    def test_scope_path_local(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 7.1: local scope shows .kiro/ path."""
        err = self._run_add_with_color(
            tmp_path, capsys, use_global=False
        )
        assert ".kiro/" in err

    def test_scope_path_global(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 7.1: global scope shows ~/.kiro/ path."""
        err = self._run_add_with_color(
            tmp_path, capsys, use_global=True
        )
        assert "~/.kiro/" in err

    def test_success_styled_checkmark(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 7.1: SYM_CHECK styled with success (92)."""
        from ksm.color import SYM_CHECK

        err = self._run_add_with_color(
            tmp_path, capsys
        )
        expected = (
            f"{self._SUCCESS_CODE}{SYM_CHECK}{self._RESET}"
        )
        assert expected in err

    def test_full_format_pattern(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 7.1: full output matches expected pattern."""
        from ksm.color import SYM_ARROW, SYM_CHECK

        err = self._run_add_with_color(
            tmp_path, capsys, "testbundle"
        )
        check = (
            f"{self._SUCCESS_CODE}{SYM_CHECK}{self._RESET}"
        )
        name = (
            f"{self._ACCENT_CODE}testbundle{self._RESET}"
        )
        scope = (
            f"{self._MUTED_CODE}(local){self._RESET}"
        )
        expected = (
            f"{check} Installed {name}"
            f" {SYM_ARROW} .kiro/ {scope}"
        )
        assert expected in err

    def test_diff_summary_present(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 7.2-7.4: diff summary lines present."""
        err = self._run_add_with_color(
            tmp_path, capsys
        )
        # New file should show + symbol and (new)
        assert "+" in err
        assert "(new)" in err

    def test_ephemeral_add_same_format(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 7.1: --from ephemeral uses same format."""
        from ksm.commands.add import run_add

        clone_dir = tmp_path / "clone"
        bundle_path = clone_dir / "mybundle"
        (bundle_path / "skills").mkdir(parents=True)
        (bundle_path / "skills" / "S.md").write_bytes(
            b"skill"
        )

        target_local = tmp_path / "workspace" / ".kiro"
        ksm_dir = tmp_path / "ksm_state"
        ksm_dir.mkdir(parents=True)

        idx = RegistryIndex(registries=[])
        manifest = Manifest(entries=[])
        args = _make_args(
            bundle_spec="mybundle",
            from_url="https://github.com/org/repo.git",
        )

        with (
            patch(
                "ksm.commands.add.clone_ephemeral",
                return_value=clone_dir,
            ),
            patch("ksm.commands.add.shutil.rmtree"),
            patch(
                "ksm.color._color_level",
                return_value=2,
            ),
        ):
            code = run_add(
                args,
                registry_index=idx,
                manifest=manifest,
                manifest_path=ksm_dir / "manifest.json",
                target_local=target_local,
                target_global=tmp_path / "home" / ".kiro",
            )

        assert code == 0
        captured = capsys.readouterr()
        assert self._ACCENT_CODE in captured.err
        assert "Installed" in captured.err
        assert self._SUCCESS_CODE in captured.err
