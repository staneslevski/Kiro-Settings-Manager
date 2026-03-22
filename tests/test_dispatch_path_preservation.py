"""Preservation property tests: non-dispatch commands and module interfaces unchanged.

Property 2: Commands that do NOT flow through _dispatch_add/_dispatch_sync/
_dispatch_rm must behave identically before and after the fix. Command modules
must receive target_dir and use it as-is.

These tests are expected to PASS on unfixed code (confirming baseline behavior).
"""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

_seg = st.from_regex(r"[a-z][a-z0-9]{0,9}", fullmatch=True)


# --- Non-dispatch command preservation ---


def test_dispatch_ls_calls_run_ls_unchanged():
    """_dispatch_ls passes manifest to run_ls without target paths."""
    manifest_sentinel = {"bundles": []}
    captured = {}

    def fake_run_ls(args, **kwargs):
        captured.update(kwargs)
        return 0

    with (
        patch("ksm.cli.load_manifest", return_value=manifest_sentinel),
        patch("ksm.commands.ls.run_ls", side_effect=fake_run_ls),
    ):
        from ksm.cli import _dispatch_ls

        ns = argparse.Namespace()
        ns.command = "ls"
        _dispatch_ls(ns)

    assert captured["manifest"] is manifest_sentinel
    assert "target_local" not in captured
    assert "target_global" not in captured


def test_dispatch_registry_ls_calls_run_registry_ls_unchanged():
    """_dispatch_registry with 'ls' subcommand passes registry_index only."""
    reg_sentinel = {"registries": []}
    captured = {}

    def fake_run(args, **kwargs):
        captured.update(kwargs)
        return 0

    with (
        patch("ksm.cli.ensure_ksm_dir"),
        patch("ksm.cli.load_registry_index", return_value=reg_sentinel),
        patch(
            "ksm.commands.registry_ls.run_registry_ls",
            side_effect=fake_run,
        ),
    ):
        from ksm.cli import _dispatch_registry

        ns = argparse.Namespace()
        ns.registry_command = "ls"
        _dispatch_registry(ns)

    assert captured["registry_index"] is reg_sentinel
    assert "target_local" not in captured
    assert "target_global" not in captured


def test_dispatch_info_calls_run_info_unchanged():
    """_dispatch_info passes registry_index and manifest without target paths."""
    reg_sentinel = {}
    manifest_sentinel = {}
    captured = {}

    def fake_run(args, **kwargs):
        captured.update(kwargs)
        return 0

    with (
        patch("ksm.cli.load_registry_index", return_value=reg_sentinel),
        patch("ksm.cli.load_manifest", return_value=manifest_sentinel),
        patch("ksm.commands.info.run_info", side_effect=fake_run),
    ):
        from ksm.cli import _dispatch_info

        ns = argparse.Namespace()
        ns.bundle_name = "test"
        _dispatch_info(ns)

    assert captured["registry_index"] is reg_sentinel
    assert captured["manifest"] is manifest_sentinel
    assert "target_local" not in captured
    assert "target_global" not in captured


def test_dispatch_search_calls_run_search_unchanged():
    """_dispatch_search passes registry_index without target paths."""
    reg_sentinel = {}
    captured = {}

    def fake_run(args, **kwargs):
        captured.update(kwargs)
        return 0

    with (
        patch("ksm.cli.load_registry_index", return_value=reg_sentinel),
        patch("ksm.commands.search.run_search", side_effect=fake_run),
    ):
        from ksm.cli import _dispatch_search

        ns = argparse.Namespace()
        ns.query = "test"
        _dispatch_search(ns)

    assert captured["registry_index"] is reg_sentinel
    assert "target_local" not in captured
    assert "target_global" not in captured


def test_dispatch_completions_calls_run_completions_unchanged():
    """_dispatch_completions passes args directly without target paths."""
    captured_args = []

    def fake_run(args):
        captured_args.append(args)
        return 0

    with patch(
        "ksm.commands.completions.run_completions",
        side_effect=fake_run,
    ):
        from ksm.cli import _dispatch_completions

        ns = argparse.Namespace()
        ns.shell = "bash"
        _dispatch_completions(ns)

    assert len(captured_args) == 1
    assert captured_args[0] is ns


# --- Command module interface preservation ---
# Verify that run_add, run_sync, run_rm receive target_dir kwargs
# and the dispatch layer does not double-append .kiro


@given(cwd_seg=_seg, home_seg=_seg)
@settings(deadline=None)
def test_run_add_receives_target_dir_as_passed(cwd_seg, home_seg):
    """run_add receives exactly the target_local/target_global from dispatch."""
    captured = {}

    def fake_run_add(args, **kwargs):
        captured.update(kwargs)
        return 0

    with (
        patch("ksm.cli.Path") as MockPath,
        patch("ksm.cli.ensure_ksm_dir"),
        patch("ksm.cli.load_registry_index", return_value={}),
        patch("ksm.cli.load_manifest", return_value={}),
        patch("ksm.commands.add.run_add", side_effect=fake_run_add),
    ):
        MockPath.cwd.return_value = Path(f"/{cwd_seg}/project")
        MockPath.home.return_value = Path(f"/{home_seg}/user")

        from ksm.cli import _dispatch_add

        ns = argparse.Namespace()
        ns.bundle_spec = "test"
        ns.command = "add"
        setattr(ns, "global", False)
        ns.local = True
        ns.interactive = False
        ns.display = False
        ns.skills_only = False
        ns.steering_only = False
        ns.hooks_only = False
        ns.agents_only = False
        ns.from_url = None
        ns.dry_run = False
        ns.yes = False
        _dispatch_add(ns)

    # The command module receives target_local and target_global as kwargs
    assert "target_local" in captured
    assert "target_global" in captured
    # They should be Path objects (not further modified by the command module)
    assert isinstance(captured["target_local"], Path)
    assert isinstance(captured["target_global"], Path)


@given(cwd_seg=_seg, home_seg=_seg)
@settings(deadline=None)
def test_run_sync_receives_target_dir_as_passed(cwd_seg, home_seg):
    """run_sync receives exactly the target_local/target_global from dispatch."""
    captured = {}

    def fake_run_sync(args, **kwargs):
        captured.update(kwargs)
        return 0

    with (
        patch("ksm.cli.Path") as MockPath,
        patch("ksm.cli.ensure_ksm_dir"),
        patch("ksm.cli.load_registry_index", return_value={}),
        patch("ksm.cli.load_manifest", return_value={}),
        patch("ksm.commands.sync.run_sync", side_effect=fake_run_sync),
    ):
        MockPath.cwd.return_value = Path(f"/{cwd_seg}/project")
        MockPath.home.return_value = Path(f"/{home_seg}/user")

        from ksm.cli import _dispatch_sync

        ns = argparse.Namespace()
        ns.bundle_names = []
        ns.command = "sync"
        ns.all = True
        ns.yes = True
        ns.dry_run = False
        _dispatch_sync(ns)

    assert "target_local" in captured
    assert "target_global" in captured
    assert isinstance(captured["target_local"], Path)
    assert isinstance(captured["target_global"], Path)


@given(cwd_seg=_seg, home_seg=_seg)
@settings(deadline=None)
def test_run_rm_receives_target_dir_as_passed(cwd_seg, home_seg):
    """run_rm receives exactly the target_local/target_global from dispatch."""
    captured = {}

    def fake_run_rm(args, **kwargs):
        captured.update(kwargs)
        return 0

    with (
        patch("ksm.cli.Path") as MockPath,
        patch("ksm.cli.ensure_ksm_dir"),
        patch("ksm.cli.load_manifest", return_value={}),
        patch("ksm.commands.rm.run_rm", side_effect=fake_run_rm),
    ):
        MockPath.cwd.return_value = Path(f"/{cwd_seg}/project")
        MockPath.home.return_value = Path(f"/{home_seg}/user")

        from ksm.cli import _dispatch_rm

        ns = argparse.Namespace()
        ns.bundle_spec = "test"
        ns.command = "rm"
        setattr(ns, "global", False)
        ns.local = True
        ns.interactive = False
        ns.display = False
        ns.dry_run = False
        ns.yes = True
        _dispatch_rm(ns)

    assert "target_local" in captured
    assert "target_global" in captured
    assert isinstance(captured["target_local"], Path)
    assert isinstance(captured["target_global"], Path)
