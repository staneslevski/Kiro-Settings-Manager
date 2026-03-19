"""Integration tests for ksm — end-to-end workflows.

Tests the full add → ls → sync → rm lifecycle, ephemeral registry,
dot notation, subdirectory filters, and add-registry flows.

Requirements: 1.1–1.8, 3.1–3.3, 4.1–4.11, 9.1–9.8, 12.1–12.8
"""

import argparse
from pathlib import Path
from unittest.mock import patch

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
