"""Tests for the bug where ksm remove leaves orphaned JSON files.

When ``ksm add`` installs agent ``.md`` files, ``auto_convert``
generates companion ``.json`` files.  Previously these generated
files were not tracked in the manifest, so ``ksm remove`` only
deleted the ``.md`` source and left the ``.json`` orphaned.

The fix makes ``auto_convert`` return generated paths so callers
can append them to the manifest entry before saving.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ksm.commands.ide2cli import auto_convert
from ksm.manifest import Manifest
from ksm.registry import RegistryEntry, RegistryIndex
from ksm.remover import remove_bundle

# -- helpers ---------------------------------------------------------


def _agent_md_content(name: str = "test-agent") -> str:
    return (
        f"---\nname: {name}\n"
        f"description: A test agent\n"
        f"tools: [shell]\n---\n# Prompt\nDo things."
    )


def _hook_content(name: str = "on-save") -> str:
    data = {
        "version": "1.0.0",
        "enabled": True,
        "name": name,
        "when": {"type": "promptSubmit"},
        "then": {"type": "runCommand", "command": "echo ok"},
    }
    return json.dumps(data, indent=2)


def _setup_registry(
    tmp_path: Path,
    bundles: dict[str, dict[str, dict[str, bytes]]],
) -> Path:
    reg = tmp_path / "registry"
    for bname, subdirs in bundles.items():
        for sd, files in subdirs.items():
            for fname, content in files.items():
                fpath = reg / bname / sd / fname
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.write_bytes(content)
    return reg


def _make_add_args(**kwargs: object) -> argparse.Namespace:
    defaults = {
        "bundle_spec": "mybundle",
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


# -- auto_convert return value tests --------------------------------


def test_auto_convert_returns_agent_json_path(
    tmp_path: Path,
) -> None:
    """auto_convert returns the generated .json path for agents."""
    target = tmp_path / ".kiro"
    agents = target / "agents"
    agents.mkdir(parents=True)
    md = agents / "my-agent.md"
    md.write_text(_agent_md_content("my-agent"), encoding="utf-8")

    generated = auto_convert(target, ["agents/my-agent.md"])

    assert generated == ["agents/my-agent.json"]
    assert (target / "agents" / "my-agent.json").is_file()


def test_auto_convert_returns_hooks_json_path(
    tmp_path: Path,
) -> None:
    """auto_convert returns _cli_hooks.json for hook files."""
    target = tmp_path / ".kiro"
    hooks = target / "hooks"
    hooks.mkdir(parents=True)
    hook = hooks / "on-save.kiro.hook"
    hook.write_text(_hook_content(), encoding="utf-8")

    generated = auto_convert(target, ["hooks/on-save.kiro.hook"])

    assert "hooks/_cli_hooks.json" in generated
    assert (target / "hooks" / "_cli_hooks.json").is_file()


def test_auto_convert_returns_empty_for_non_convertible(
    tmp_path: Path,
) -> None:
    """auto_convert returns empty list when no convertible files."""
    target = tmp_path / ".kiro"
    steering = target / "steering"
    steering.mkdir(parents=True)
    (steering / "rules.md").write_text("# Rules", encoding="utf-8")

    generated = auto_convert(target, ["steering/rules.md"])

    assert generated == []


# -- end-to-end: add then remove ------------------------------------


def test_add_tracks_generated_json_in_manifest(
    tmp_path: Path,
) -> None:
    """ksm add records generated .json files in the manifest."""
    from ksm.commands.add import run_add

    reg = _setup_registry(
        tmp_path,
        {"mybundle": {"agents": {"helper.md": _agent_md_content("helper").encode()}}},
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

    args = _make_add_args(bundle_spec="mybundle")
    code = run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=target_global,
    )

    assert code == 0
    entry = manifest.entries[0]
    assert "agents/helper.md" in entry.installed_files
    assert "agents/helper.json" in entry.installed_files


def test_remove_deletes_generated_json_after_add(
    tmp_path: Path,
) -> None:
    """ksm remove deletes both .md and generated .json files."""
    from ksm.commands.add import run_add

    reg = _setup_registry(
        tmp_path,
        {"mybundle": {"agents": {"helper.md": _agent_md_content("helper").encode()}}},
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

    args = _make_add_args(bundle_spec="mybundle")
    run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=target_global,
    )

    # Both files should exist on disk
    assert (target_local / "agents" / "helper.md").is_file()
    assert (target_local / "agents" / "helper.json").is_file()

    # Now remove
    entry = manifest.entries[0]
    result = remove_bundle(entry, target_local, manifest)

    # Both files should be gone
    assert not (target_local / "agents" / "helper.md").exists()
    assert not (target_local / "agents" / "helper.json").exists()
    assert "agents/helper.md" in result.removed_files
    assert "agents/helper.json" in result.removed_files
    assert len(manifest.entries) == 0


def test_remove_deletes_cli_hooks_json_after_add(
    tmp_path: Path,
) -> None:
    """ksm remove deletes _cli_hooks.json generated from hooks."""
    from ksm.commands.add import run_add

    reg = _setup_registry(
        tmp_path,
        {"mybundle": {"hooks": {"on-save.kiro.hook": _hook_content().encode()}}},
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

    args = _make_add_args(bundle_spec="mybundle")
    run_add(
        args,
        registry_index=idx,
        manifest=manifest,
        manifest_path=ksm_dir / "manifest.json",
        target_local=target_local,
        target_global=target_global,
    )

    assert (target_local / "hooks" / "_cli_hooks.json").is_file()
    entry = manifest.entries[0]
    assert "hooks/_cli_hooks.json" in entry.installed_files

    result = remove_bundle(entry, target_local, manifest)

    assert not (target_local / "hooks" / "_cli_hooks.json").exists()
    assert "hooks/_cli_hooks.json" in result.removed_files
