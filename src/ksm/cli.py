"""CLI entry point for ksm.

Provides the ``main()`` function registered as the ``ksm`` console
script.  Uses argparse with subparsers for add, ls, sync,
add-registry, and rm.

Requirements: 8.1–8.5
"""

import argparse
from pathlib import Path

from ksm import __version__
from ksm.manifest import load_manifest, Manifest
from ksm.persistence import (
    ensure_ksm_dir,
    MANIFEST_FILE,
    REGISTRIES_FILE,
)
from ksm.registry import load_registry_index, RegistryIndex


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with subparsers."""
    parser = argparse.ArgumentParser(
        prog="ksm",
        description="Kiro Settings Manager — manage configuration bundles",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    sub = parser.add_subparsers(dest="command")

    # --- add ---
    add_p = sub.add_parser("add", help="Install a bundle")
    add_p.add_argument(
        "bundle_spec", nargs="?", default=None, help="Bundle name or dot notation"
    )
    add_p.add_argument(
        "-l", "--local", dest="local", action="store_true", help="Install locally"
    )
    add_p.add_argument(
        "-g",
        "--global",
        dest="global_",
        action="store_true",
        help="Install globally",
    )
    add_p.add_argument(
        "--display",
        action="store_true",
        help="Interactive bundle selector",
    )
    add_p.add_argument(
        "--from",
        dest="from_url",
        default=None,
        help="Ephemeral git registry URL",
    )
    add_p.add_argument(
        "--skills-only",
        action="store_true",
        help="Copy only skills/",
    )
    add_p.add_argument(
        "--agents-only",
        action="store_true",
        help="Copy only agents/",
    )
    add_p.add_argument(
        "--steering-only",
        action="store_true",
        help="Copy only steering/",
    )
    add_p.add_argument(
        "--hooks-only",
        action="store_true",
        help="Copy only hooks/",
    )

    # --- ls ---
    sub.add_parser("ls", help="List installed bundles")

    # --- sync ---
    sync_p = sub.add_parser("sync", help="Sync installed bundles")
    sync_p.add_argument(
        "bundle_names",
        nargs="*",
        default=[],
        help="Bundle names to sync",
    )
    sync_p.add_argument(
        "--all",
        action="store_true",
        help="Sync all installed bundles",
    )
    sync_p.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )

    # --- add-registry ---
    ar_p = sub.add_parser("add-registry", help="Register a git bundle registry")
    ar_p.add_argument("git_url", help="Git repository URL")

    # --- rm ---
    rm_p = sub.add_parser("rm", help="Remove an installed bundle")
    rm_p.add_argument(
        "bundle_name",
        nargs="?",
        default=None,
        help="Bundle to remove",
    )
    rm_p.add_argument(
        "-l",
        "--local",
        dest="local",
        action="store_true",
        help="Remove local install",
    )
    rm_p.add_argument(
        "-g",
        "--global",
        dest="global_",
        action="store_true",
        help="Remove global install",
    )
    rm_p.add_argument(
        "--display",
        action="store_true",
        help="Interactive removal selector",
    )

    return parser


def main() -> None:
    """Parse args and dispatch to the appropriate command handler."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        raise SystemExit(2)

    dispatch = {
        "add": _dispatch_add,
        "ls": _dispatch_ls,
        "sync": _dispatch_sync,
        "add-registry": _dispatch_add_registry,
        "rm": _dispatch_rm,
    }

    handler = dispatch[args.command]
    exit_code = handler(args)
    raise SystemExit(exit_code)


def _dispatch_add(args: argparse.Namespace) -> int:
    """Wire up and run the add command."""
    from ksm.commands.add import run_add

    ensure_ksm_dir()
    registry_index = _load_registry_index()
    manifest = _load_manifest()

    return run_add(
        args,
        registry_index=registry_index,
        manifest=manifest,
        manifest_path=MANIFEST_FILE,
        target_local=Path.cwd() / ".kiro",
        target_global=Path.home() / ".kiro",
    )


def _dispatch_ls(args: argparse.Namespace) -> int:
    """Wire up and run the ls command."""
    from ksm.commands.ls import run_ls

    manifest = _load_manifest()
    return run_ls(args, manifest=manifest)


def _dispatch_sync(args: argparse.Namespace) -> int:
    """Wire up and run the sync command."""
    from ksm.commands.sync import run_sync

    ensure_ksm_dir()
    registry_index = _load_registry_index()
    manifest = _load_manifest()

    return run_sync(
        args,
        registry_index=registry_index,
        manifest=manifest,
        manifest_path=MANIFEST_FILE,
        target_local=Path.cwd() / ".kiro",
        target_global=Path.home() / ".kiro",
    )


def _dispatch_add_registry(args: argparse.Namespace) -> int:
    """Wire up and run the add-registry command."""
    from ksm.commands.add_registry import run_add_registry

    ensure_ksm_dir()
    registry_index = _load_registry_index()

    from ksm.persistence import KSM_DIR

    return run_add_registry(
        args,
        registry_index=registry_index,
        registry_index_path=REGISTRIES_FILE,
        cache_dir=KSM_DIR / "cache",
    )


def _dispatch_rm(args: argparse.Namespace) -> int:
    """Wire up and run the rm command."""
    from ksm.commands.rm import run_rm

    ensure_ksm_dir()
    manifest = _load_manifest()

    return run_rm(
        args,
        manifest=manifest,
        manifest_path=MANIFEST_FILE,
        target_local=Path.cwd() / ".kiro",
        target_global=Path.home() / ".kiro",
    )


def _load_registry_index() -> RegistryIndex:
    """Load registry index, creating default on first run."""
    default_path = Path(__file__).resolve().parent.parent.parent / "config_bundles"
    return load_registry_index(
        REGISTRIES_FILE,
        default_registry_path=default_path,
    )


def _load_manifest() -> Manifest:
    """Load the install manifest."""
    return load_manifest(MANIFEST_FILE)
