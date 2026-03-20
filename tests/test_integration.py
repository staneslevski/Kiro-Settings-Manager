"""Integration tests for ksm — end-to-end workflows.

Tests the full add → ls → sync → rm lifecycle, ephemeral registry,
dot notation, subdirectory filters, and add-registry flows.

Requirements: 1.1–1.8, 3.1–3.3, 4.1–4.11, 9.1–9.8, 12.1–12.8
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from ksm.commands.add import run_add
from ksm.commands.ls import run_ls
from ksm.commands.rm import run_rm
from ksm.commands.sync import run_sync
from ksm.manifest import Manifest
from ksm.registry import RegistryEntry, RegistryIndex


def _setup_registry(
    tmp_path: Path,
    bundles: dict[str, dict[str, dict[str, bytes]]],
) -> Path:
    """Create a registry directory with bundles on disk."""
    reg = tmp_path / "registry"
    for bname, subdirs in bundles.items():
        for sd, files in subdirs.items():
            for fname, content in files.items():
                fpath = reg / bname / sd / fname
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.write_bytes(content)
    return reg


def _make_index(reg: Path) -> RegistryIndex:
    """Build a RegistryIndex pointing at a local registry."""
    return RegistryIndex(
        registries=[
            RegistryEntry(
                name="default",
                url=None,
                local_path=str(reg),
                is_default=True,
            )
        ]
    )


class TestFullLifecycle:
    """Test add → ls → sync → rm workflow end-to-end."""

    def test_add_ls_sync_rm(self, tmp_path: Path) -> None:
        """Full lifecycle: add a bundle, list it, sync it, remove it."""
        reg = _setup_registry(
            tmp_path,
            {
                "myapp": {
                    "skills": {"s1.md": b"skill-v1"},
                    "steering": {"st1.md": b"steer-v1"},
                }
            },
        )
        idx = _make_index(reg)
        manifest = Manifest(entries=[])
        manifest_path = tmp_path / "ksm" / "manifest.json"
        manifest_path.parent.mkdir(parents=True)
        target_local = tmp_path / "workspace" / ".kiro"
        target_global = tmp_path / "home" / ".kiro"

        # --- ADD ---
        add_args = argparse.Namespace(
            bundle_spec="myapp",
            interactive=False,
            from_url=None,
            local=False,
            global_=False,
            only=None,
            dry_run=False,
        )
        code = run_add(
            add_args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=manifest_path,
            target_local=target_local,
            target_global=target_global,
        )
        assert code == 0
        assert (target_local / "skills" / "s1.md").read_bytes() == b"skill-v1"
        assert (target_local / "steering" / "st1.md").read_bytes() == b"steer-v1"
        assert len(manifest.entries) == 1
        assert manifest.entries[0].bundle_name == "myapp"
        assert manifest.entries[0].scope == "local"

        # --- LS ---
        ls_args = argparse.Namespace()
        code = run_ls(ls_args, manifest=manifest)
        assert code == 0

        # --- SYNC ---
        # Update source file to simulate upstream change
        (reg / "myapp" / "skills" / "s1.md").write_bytes(b"skill-v2")

        sync_args = argparse.Namespace(
            bundle_names=["myapp"],
            all=False,
            yes=True,
            dry_run=False,
        )
        code = run_sync(
            sync_args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=manifest_path,
            target_local=target_local,
            target_global=target_global,
        )
        assert code == 0
        assert (target_local / "skills" / "s1.md").read_bytes() == b"skill-v2"

        # --- RM ---
        rm_args = argparse.Namespace(
            bundle_name="myapp",
            interactive=False,
            local=False,
            global_=False,
            yes=True,
            dry_run=False,
        )
        code = run_rm(
            rm_args,
            manifest=manifest,
            manifest_path=manifest_path,
            target_local=target_local,
            target_global=target_global,
        )
        assert code == 0
        assert not (target_local / "skills" / "s1.md").exists()
        assert not (target_local / "steering" / "st1.md").exists()
        assert len(manifest.entries) == 0


class TestEphemeralRegistryE2E:
    """Test add with --from ephemeral registry end-to-end."""

    def test_from_flag_installs_and_cleans_up(self, tmp_path: Path) -> None:
        """--from clones, installs, and cleans up temp dir."""
        # Create a fake "remote" repo on disk
        remote = tmp_path / "remote_repo"
        (remote / "mybundle" / "skills" / "s.md").parent.mkdir(parents=True)
        (remote / "mybundle" / "skills" / "s.md").write_bytes(b"remote-skill")

        manifest = Manifest(entries=[])
        manifest_path = tmp_path / "ksm" / "manifest.json"
        manifest_path.parent.mkdir(parents=True)
        target_local = tmp_path / "workspace" / ".kiro"
        target_global = tmp_path / "home" / ".kiro"

        # Empty registry index (no registries)
        idx = RegistryIndex(registries=[])

        args = argparse.Namespace(
            bundle_spec="mybundle",
            interactive=False,
            from_url="https://example.com/repo.git",
            local=False,
            global_=False,
            only=None,
        )

        # Mock clone_ephemeral to return our local "remote"
        with patch(
            "ksm.commands.add.clone_ephemeral",
            return_value=remote,
        ):
            # Prevent shutil.rmtree from deleting our fixture
            with patch("ksm.commands.add.shutil.rmtree"):
                code = run_add(
                    args,
                    registry_index=idx,
                    manifest=manifest,
                    manifest_path=manifest_path,
                    target_local=target_local,
                    target_global=target_global,
                )

        assert code == 0
        assert (target_local / "skills" / "s.md").read_bytes() == b"remote-skill"
        assert manifest.entries[0].source_registry == ("https://example.com/repo.git")
        # Registry index should be unchanged (ephemeral not persisted)
        assert len(idx.registries) == 0


class TestDotNotationE2E:
    """Test add with dot notation end-to-end."""

    def test_dot_notation_installs_single_item(self, tmp_path: Path) -> None:
        """Dot notation installs only the targeted item."""
        reg = _setup_registry(
            tmp_path,
            {
                "aws": {
                    "skills": {
                        "cross-account/SKILL.md": b"ca-skill",
                        "other/SKILL.md": b"other-skill",
                    },
                    "steering": {"guide.md": b"guide"},
                }
            },
        )
        idx = _make_index(reg)
        manifest = Manifest(entries=[])
        manifest_path = tmp_path / "ksm" / "manifest.json"
        manifest_path.parent.mkdir(parents=True)
        target_local = tmp_path / "workspace" / ".kiro"
        target_global = tmp_path / "home" / ".kiro"

        args = argparse.Namespace(
            bundle_spec="aws.skills.cross-account",
            interactive=False,
            from_url=None,
            local=False,
            global_=False,
            only=None,
        )
        code = run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=manifest_path,
            target_local=target_local,
            target_global=target_global,
        )
        assert code == 0
        assert (target_local / "skills" / "cross-account" / "SKILL.md").exists()
        # Other items should NOT be installed
        assert not (target_local / "skills" / "other" / "SKILL.md").exists()
        assert not (target_local / "steering" / "guide.md").exists()


class TestSubdirectoryFiltersE2E:
    """Test add with subdirectory filters end-to-end."""

    def test_skills_only_filter(self, tmp_path: Path) -> None:
        """--only skills copies only skills/ subdirectory."""
        reg = _setup_registry(
            tmp_path,
            {
                "myapp": {
                    "skills": {"s.md": b"skill"},
                    "steering": {"st.md": b"steer"},
                    "hooks": {"h.json": b"hook"},
                }
            },
        )
        idx = _make_index(reg)
        manifest = Manifest(entries=[])
        manifest_path = tmp_path / "ksm" / "manifest.json"
        manifest_path.parent.mkdir(parents=True)
        target_local = tmp_path / "workspace" / ".kiro"
        target_global = tmp_path / "home" / ".kiro"

        args = argparse.Namespace(
            bundle_spec="myapp",
            interactive=False,
            from_url=None,
            local=False,
            global_=False,
            only=["skills"],
        )
        code = run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=manifest_path,
            target_local=target_local,
            target_global=target_global,
        )
        assert code == 0
        assert (target_local / "skills" / "s.md").exists()
        assert not (target_local / "steering" / "st.md").exists()
        assert not (target_local / "hooks" / "h.json").exists()


class TestAddRegistryE2E:
    """Test registry add with mocked git clone end-to-end."""

    def test_add_registry_clones_and_registers(self, tmp_path: Path) -> None:
        """registry add clones repo and adds to registry index."""
        from ksm.commands.registry_add import run_registry_add

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        idx_path = tmp_path / "registries.json"
        idx = RegistryIndex(registries=[])

        def fake_clone(url: str, target: Path) -> None:
            # Simulate git clone by creating bundle structure
            (target / "shared" / "steering" / "rules.md").parent.mkdir(parents=True)
            (target / "shared" / "steering" / "rules.md").write_bytes(b"rules")

        args = argparse.Namespace(git_url="https://github.com/org/team-configs.git")

        with patch(
            "ksm.commands.registry_add.clone_repo",
            side_effect=fake_clone,
        ):
            code = run_registry_add(
                args,
                registry_index=idx,
                registry_index_path=idx_path,
                cache_dir=cache_dir,
            )

        assert code == 0
        assert len(idx.registries) == 1
        assert idx.registries[0].name == "team-configs"
        assert idx.registries[0].url == "https://github.com/org/team-configs.git"


class TestRegistryAddForceE2E:
    """Test registry add with --force end-to-end (Req 1.5)."""

    def test_force_replaces_cache_and_reregisters(
        self,
        tmp_path: Path,
    ) -> None:
        """--force removes old cache, re-clones, re-registers."""
        from ksm.commands.registry_add import run_registry_add

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        idx_path = tmp_path / "registries.json"

        # Pre-populate cache and index as if already added
        target = cache_dir / "team-configs"
        target.mkdir()
        (target / "old-file.txt").write_bytes(b"old")

        url = "https://github.com/org/team-configs.git"
        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="team-configs",
                    url=url,
                    local_path=str(target),
                    is_default=False,
                )
            ]
        )

        def fake_clone(clone_url: str, dest: Path) -> None:
            dest.mkdir(parents=True, exist_ok=True)
            bdir = dest / "shared" / "steering"
            bdir.mkdir(parents=True)
            (bdir / "rules.md").write_bytes(b"new-rules")

        args = argparse.Namespace(
            git_url=url,
            force=True,
            custom_name=None,
        )

        with patch(
            "ksm.commands.registry_add.clone_repo",
            side_effect=fake_clone,
        ):
            code = run_registry_add(
                args,
                registry_index=idx,
                registry_index_path=idx_path,
                cache_dir=cache_dir,
            )

        assert code == 0
        # Old file should be gone (cache was replaced)
        assert not (target / "old-file.txt").exists()
        # New content should exist
        assert (
            target / "shared" / "steering" / "rules.md"
        ).read_bytes() == b"new-rules"
        # Should have exactly one entry (old removed, new added)
        assert len(idx.registries) == 1
        assert idx.registries[0].name == "team-configs"


class TestRegistryRemoveFeedbackE2E:
    """Test registry remove feedback end-to-end (Req 3.1)."""

    def test_remove_prints_cache_cleaned(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Remove prints cache cleaned message when dir exists."""
        from ksm.commands.registry_rm import run_registry_rm

        cache_path = tmp_path / "cache" / "my-reg"
        cache_path.mkdir(parents=True)
        (cache_path / "data.txt").write_bytes(b"data")
        idx_path = tmp_path / "registries.json"

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="my-reg",
                    url="https://example.com/repo.git",
                    local_path=str(cache_path),
                    is_default=False,
                )
            ]
        )

        args = argparse.Namespace(registry_name="my-reg")

        with patch("ksm.commands.registry_rm.save_registry_index"):
            code = run_registry_rm(
                args,
                registry_index=idx,
                registry_index_path=idx_path,
            )

        assert code == 0
        assert len(idx.registries) == 0
        assert not cache_path.exists()
        err = capsys.readouterr().err
        assert "Cache directory cleaned:" in err
        assert str(cache_path) in err


class TestAddQualifiedNameE2E:
    """Test add with qualified name end-to-end (Req 4.3, 10.1)."""

    def test_qualified_name_installs_from_correct_registry(
        self,
        tmp_path: Path,
    ) -> None:
        """registry/bundle syntax installs from the right source."""
        # Create two registries with same bundle name
        reg_a = tmp_path / "reg-a"
        (reg_a / "shared" / "skills" / "s.md").parent.mkdir(parents=True)
        (reg_a / "shared" / "skills" / "s.md").write_bytes(b"skill-a")

        reg_b = tmp_path / "reg-b"
        (reg_b / "shared" / "skills" / "s.md").parent.mkdir(parents=True)
        (reg_b / "shared" / "skills" / "s.md").write_bytes(b"skill-b")

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="alpha",
                    url=None,
                    local_path=str(reg_a),
                    is_default=True,
                ),
                RegistryEntry(
                    name="beta",
                    url=None,
                    local_path=str(reg_b),
                    is_default=False,
                ),
            ]
        )

        manifest = Manifest(entries=[])
        manifest_path = tmp_path / "manifest.json"
        target_local = tmp_path / "workspace" / ".kiro"
        target_global = tmp_path / "home" / ".kiro"

        # Install from beta registry using qualified name
        args = argparse.Namespace(
            bundle_spec="beta/shared",
            interactive=False,
            from_url=None,
            local=False,
            global_=False,
            only=None,
            dry_run=False,
        )
        code = run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=manifest_path,
            target_local=target_local,
            target_global=target_global,
        )
        assert code == 0
        installed = (target_local / "skills" / "s.md").read_bytes()
        assert installed == b"skill-b"

    def test_ambiguous_unqualified_name_errors(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Unqualified name with multiple matches → error."""
        reg_a = tmp_path / "reg-a"
        (reg_a / "shared" / "skills" / "s.md").parent.mkdir(parents=True)
        (reg_a / "shared" / "skills" / "s.md").write_bytes(b"skill-a")

        reg_b = tmp_path / "reg-b"
        (reg_b / "shared" / "skills" / "s.md").parent.mkdir(parents=True)
        (reg_b / "shared" / "skills" / "s.md").write_bytes(b"skill-b")

        idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name="alpha",
                    url=None,
                    local_path=str(reg_a),
                    is_default=True,
                ),
                RegistryEntry(
                    name="beta",
                    url=None,
                    local_path=str(reg_b),
                    is_default=False,
                ),
            ]
        )

        manifest = Manifest(entries=[])
        manifest_path = tmp_path / "manifest.json"
        target_local = tmp_path / "workspace" / ".kiro"
        target_global = tmp_path / "home" / ".kiro"

        args = argparse.Namespace(
            bundle_spec="shared",
            interactive=False,
            from_url=None,
            local=False,
            global_=False,
            only=None,
            dry_run=False,
        )
        code = run_add(
            args,
            registry_index=idx,
            manifest=manifest,
            manifest_path=manifest_path,
            target_local=target_local,
            target_global=target_global,
        )
        assert code == 1
        err = capsys.readouterr().err
        assert "multiple registries" in err
        assert "alpha" in err
        assert "beta" in err


class TestDispatchRegistryCanonicalNames:
    """Test _dispatch_registry handles canonical names (Req 7.6)."""

    def test_dispatch_registry_remove_canonical(
        self,
        tmp_path: Path,
    ) -> None:
        """registry remove dispatches to run_registry_rm."""
        import ksm.cli as cli_mod

        args = argparse.Namespace(
            command="registry",
            registry_command="remove",
            registry_name="test-reg",
        )
        with (
            patch.object(cli_mod, "ensure_ksm_dir"),
            patch.object(
                cli_mod,
                "load_registry_index",
                return_value=RegistryIndex(registries=[]),
            ),
            patch(
                "ksm.commands.registry_rm.run_registry_rm",
                return_value=0,
            ) as mock_rm,
        ):
            code = cli_mod._dispatch_registry(args)

        assert code == 0
        mock_rm.assert_called_once()

    def test_dispatch_registry_list_canonical(
        self,
        tmp_path: Path,
    ) -> None:
        """registry list dispatches to run_registry_ls."""
        import ksm.cli as cli_mod

        args = argparse.Namespace(
            command="registry",
            registry_command="list",
        )
        with (
            patch.object(cli_mod, "ensure_ksm_dir"),
            patch.object(
                cli_mod,
                "load_registry_index",
                return_value=RegistryIndex(registries=[]),
            ),
            patch(
                "ksm.commands.registry_ls.run_registry_ls",
                return_value=0,
            ) as mock_ls,
        ):
            code = cli_mod._dispatch_registry(args)

        assert code == 0
        mock_ls.assert_called_once()

    def test_dispatch_registry_add_to_registry_add(
        self,
        tmp_path: Path,
    ) -> None:
        """registry add dispatches to registry_add module."""
        import ksm.cli as cli_mod

        args = argparse.Namespace(
            command="registry",
            registry_command="add",
            git_url="https://example.com/repo.git",
            force=False,
            custom_name=None,
        )
        with (
            patch.object(cli_mod, "ensure_ksm_dir"),
            patch.object(
                cli_mod,
                "load_registry_index",
                return_value=RegistryIndex(registries=[]),
            ),
            patch(
                "ksm.commands.registry_add.run_registry_add",
                return_value=0,
            ) as mock_add,
        ):
            code = cli_mod._dispatch_registry(args)

        assert code == 0
        mock_add.assert_called_once()


class TestLegacyAddRegistryDelegation:
    """Test legacy add-registry delegates with --force/--name (Req 8.2)."""

    def test_legacy_delegates_with_force(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """add-registry --force delegates to run_registry_add."""
        from ksm.commands.add_registry import run_add_registry

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        idx_path = tmp_path / "registries.json"
        idx = RegistryIndex(registries=[])

        args = argparse.Namespace(
            git_url="https://example.com/repo.git",
            force=True,
            custom_name=None,
        )

        with patch(
            "ksm.commands.registry_add.run_registry_add",
            return_value=0,
        ) as mock_add:
            code = run_add_registry(
                args,
                registry_index=idx,
                registry_index_path=idx_path,
                cache_dir=cache_dir,
            )

        assert code == 0
        mock_add.assert_called_once()
        # Should print deprecation warning
        err = capsys.readouterr().err
        assert "Deprecated:" in err
        assert "ksm add-registry" in err
        assert "ksm registry add" in err

    def test_legacy_delegates_with_name(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """add-registry --name delegates to run_registry_add."""
        from ksm.commands.add_registry import run_add_registry

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        idx_path = tmp_path / "registries.json"
        idx = RegistryIndex(registries=[])

        args = argparse.Namespace(
            git_url="https://example.com/repo.git",
            force=False,
            custom_name="my-custom",
        )

        with patch(
            "ksm.commands.registry_add.run_registry_add",
            return_value=0,
        ) as mock_add:
            code = run_add_registry(
                args,
                registry_index=idx,
                registry_index_path=idx_path,
                cache_dir=cache_dir,
            )

        assert code == 0
        mock_add.assert_called_once()
        # Verify args passed through
        call_args = mock_add.call_args
        assert call_args.args[0].custom_name == "my-custom"
        assert call_args.args[0].force is False
