"""Bug condition exploration: dispatch functions pass paths without .kiro suffix.

Property 1: For _dispatch_add, _dispatch_sync, and _dispatch_rm, the
target_local and target_global kwargs passed to the command runner MUST
end with '.kiro'.

This test is expected to FAIL on unfixed code (proving the bug exists)
and PASS after the fix is applied.
"""

import argparse
from pathlib import Path, PurePosixPath
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

# Strategy for random path segments
_seg = st.from_regex(r"[a-z][a-z0-9]{0,9}", fullmatch=True)


def _make_add_args(bundle="mybundle", global_flag=False):
    ns = argparse.Namespace()
    ns.bundle_spec = bundle
    ns.command = "add"
    # scope flags
    setattr(ns, "global", global_flag)
    ns.local = not global_flag
    ns.interactive = False
    ns.display = False
    ns.skills_only = False
    ns.steering_only = False
    ns.hooks_only = False
    ns.agents_only = False
    ns.from_url = None
    ns.dry_run = False
    ns.yes = False
    return ns


def _make_sync_args(bundles=None, sync_all=True):
    ns = argparse.Namespace()
    ns.bundle_names = bundles or []
    ns.command = "sync"
    ns.all = sync_all
    ns.yes = True
    ns.dry_run = False
    return ns


def _make_rm_args(bundle="mybundle", global_flag=False):
    ns = argparse.Namespace()
    ns.bundle_spec = bundle
    ns.command = "rm"
    setattr(ns, "global", global_flag)
    ns.local = not global_flag
    ns.interactive = False
    ns.display = False
    ns.dry_run = False
    ns.yes = True
    return ns


@given(cwd_seg=_seg, home_seg=_seg)
@settings(deadline=None)
def test_dispatch_add_target_local_ends_with_kiro(cwd_seg, home_seg):
    cwd = PurePosixPath(f"/{cwd_seg}/project")
    home = PurePosixPath(f"/{home_seg}/user")
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
        MockPath.cwd.return_value = Path(str(cwd))
        MockPath.home.return_value = Path(str(home))

        from ksm.cli import _dispatch_add

        _dispatch_add(_make_add_args())

    assert str(captured["target_local"]).endswith(
        ".kiro"
    ), f"target_local={captured['target_local']} does not end with .kiro"


@given(cwd_seg=_seg, home_seg=_seg)
@settings(deadline=None)
def test_dispatch_add_target_global_ends_with_kiro(cwd_seg, home_seg):
    cwd = PurePosixPath(f"/{cwd_seg}/project")
    home = PurePosixPath(f"/{home_seg}/user")
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
        MockPath.cwd.return_value = Path(str(cwd))
        MockPath.home.return_value = Path(str(home))

        from ksm.cli import _dispatch_add

        _dispatch_add(_make_add_args(global_flag=True))

    assert str(captured["target_global"]).endswith(
        ".kiro"
    ), f"target_global={captured['target_global']} does not end with .kiro"


@given(cwd_seg=_seg, home_seg=_seg)
@settings(deadline=None)
def test_dispatch_sync_target_local_ends_with_kiro(cwd_seg, home_seg):
    cwd = PurePosixPath(f"/{cwd_seg}/project")
    home = PurePosixPath(f"/{home_seg}/user")
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
        MockPath.cwd.return_value = Path(str(cwd))
        MockPath.home.return_value = Path(str(home))

        from ksm.cli import _dispatch_sync

        _dispatch_sync(_make_sync_args())

    assert str(captured["target_local"]).endswith(
        ".kiro"
    ), f"target_local={captured['target_local']} does not end with .kiro"


@given(cwd_seg=_seg, home_seg=_seg)
@settings(deadline=None)
def test_dispatch_sync_target_global_ends_with_kiro(cwd_seg, home_seg):
    cwd = PurePosixPath(f"/{cwd_seg}/project")
    home = PurePosixPath(f"/{home_seg}/user")
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
        MockPath.cwd.return_value = Path(str(cwd))
        MockPath.home.return_value = Path(str(home))

        from ksm.cli import _dispatch_sync

        _dispatch_sync(_make_sync_args())

    assert str(captured["target_global"]).endswith(
        ".kiro"
    ), f"target_global={captured['target_global']} does not end with .kiro"


@given(cwd_seg=_seg, home_seg=_seg)
@settings(deadline=None)
def test_dispatch_rm_target_local_ends_with_kiro(cwd_seg, home_seg):
    cwd = PurePosixPath(f"/{cwd_seg}/project")
    home = PurePosixPath(f"/{home_seg}/user")
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
        MockPath.cwd.return_value = Path(str(cwd))
        MockPath.home.return_value = Path(str(home))

        from ksm.cli import _dispatch_rm

        _dispatch_rm(_make_rm_args())

    assert str(captured["target_local"]).endswith(
        ".kiro"
    ), f"target_local={captured['target_local']} does not end with .kiro"


@given(cwd_seg=_seg, home_seg=_seg)
@settings(deadline=None)
def test_dispatch_rm_target_global_ends_with_kiro(cwd_seg, home_seg):
    cwd = PurePosixPath(f"/{cwd_seg}/project")
    home = PurePosixPath(f"/{home_seg}/user")
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
        MockPath.cwd.return_value = Path(str(cwd))
        MockPath.home.return_value = Path(str(home))

        from ksm.cli import _dispatch_rm

        _dispatch_rm(_make_rm_args(global_flag=True))

    assert str(captured["target_global"]).endswith(
        ".kiro"
    ), f"target_global={captured['target_global']} does not end with .kiro"
