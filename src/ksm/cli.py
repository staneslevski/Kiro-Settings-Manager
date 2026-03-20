"""CLI entry point for ksm.

Provides the ``main()`` function registered as the ``ksm`` console
script.  Uses argparse with subparsers for add, ls, sync, rm,
add-registry, registry (add/ls/rm/inspect), init, info, search,
and completions.

Requirements: 4.1–4.4, 8.1–8.5, 17, 18, 19, 20, 21
"""

import argparse
import sys
from pathlib import Path

from ksm import __version__
from ksm.manifest import load_manifest
from ksm.persistence import (
    ensure_ksm_dir,
    KSM_DIR,
    MANIFEST_FILE,
    REGISTRIES_FILE,
)
from ksm.registry import load_registry_index


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser with subparsers."""
    parser = argparse.ArgumentParser(
        prog="ksm",
        description=("Kiro Settings Manager — manage configuration bundles"),
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
        "bundle_spec",
        nargs="?",
        default=None,
        help="Bundle name or dot notation",
    )
    add_p.add_argument(
        "-l",
        "--local",
        dest="local",
        action="store_true",
        help="Install locally",
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
        help="Launch interactive selector",
    )
    add_p.add_argument(
        "--from",
        dest="from_url",
        default=None,
        help="Ephemeral git URL to install from",
    )
    add_p.add_argument(
        "--skills-only",
        action="store_true",
        help="Install only skills",
    )
    add_p.add_argument(
        "--agents-only",
        action="store_true",
        help="Install only agents",
    )
    add_p.add_argument(
        "--steering-only",
        action="store_true",
        help="Install only steering",
    )
    add_p.add_argument(
        "--hooks-only",
        action="store_true",
        help="Install only hooks",
    )

    # --- ls ---
    ls_p = sub.add_parser("ls", help="List installed bundles")
    ls_p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show installed files",
    )
    ls_p.add_argument(
        "--scope",
        choices=["local", "global"],
        default=None,
        help="Filter by scope",
    )
    ls_p.add_argument(
        "--format",
        dest="output_format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )

    # --- sync ---
    sync_p = sub.add_parser("sync", help="Sync installed bundles")
    sync_p.add_argument(
        "bundle_names",
        nargs="*",
        help="Bundle names to sync",
    )
    sync_p.add_argument(
        "--all",
        action="store_true",
        help="Sync all installed bundles",
    )
    sync_p.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )

    # --- rm ---
    rm_p = sub.add_parser("rm", help="Remove an installed bundle")
    rm_p.add_argument(
        "bundle_name",
        nargs="?",
        default=None,
        help="Bundle name to remove",
    )
    rm_p.add_argument(
        "-l",
        "--local",
        dest="local",
        action="store_true",
        help="Remove from local scope",
    )
    rm_p.add_argument(
        "-g",
        "--global",
        dest="global_",
        action="store_true",
        help="Remove from global scope",
    )
    rm_p.add_argument(
        "--display",
        action="store_true",
        help="Launch interactive removal selector",
    )

    # --- add-registry ---
    ar_p = sub.add_parser("add-registry", help="Register a git bundle registry")
    ar_p.add_argument("git_url", help="Git URL of the registry")

    # --- registry (subcommand group) ---
    reg_p = sub.add_parser("registry", help="Manage registries")
    reg_sub = reg_p.add_subparsers(dest="registry_command")

    reg_add_p = reg_sub.add_parser("add", help="Add a registry")
    reg_add_p.add_argument("git_url", help="Git URL of the registry")
    reg_sub.add_parser("ls", help="List registries")

    reg_rm_p = reg_sub.add_parser("rm", help="Remove a registry")
    reg_rm_p.add_argument("registry_name", help="Name of registry to remove")

    reg_inspect_p = reg_sub.add_parser("inspect", help="Inspect a registry")
    reg_inspect_p.add_argument(
        "registry_name",
        help="Name of registry to inspect",
    )

    # --- init ---
    sub.add_parser("init", help="Initialise .kiro/ directory")

    # --- info ---
    info_p = sub.add_parser("info", help="Show bundle information")
    info_p.add_argument("bundle_name", help="Bundle name to inspect")

    # --- search ---
    search_p = sub.add_parser("search", help="Search for bundles")
    search_p.add_argument("query", help="Search query")

    # --- completions ---
    comp_p = sub.add_parser("completions", help="Generate shell completions")
    comp_p.add_argument(
        "shell",
        choices=["bash", "zsh", "fish"],
        help="Shell type",
    )

    return parser


# ------------------------------------------------------------------
# Dispatch helpers
# ------------------------------------------------------------------


def _dispatch_add(args: argparse.Namespace) -> int:
    """Dispatch the add command."""
    ensure_ksm_dir()
    registry_index = load_registry_index(REGISTRIES_FILE)
    manifest = load_manifest(MANIFEST_FILE)

    from ksm.commands.add import run_add

    return run_add(
        args,
        registry_index=registry_index,
        manifest=manifest,
        manifest_path=MANIFEST_FILE,
        target_local=Path.cwd(),
        target_global=Path.home(),
    )


def _dispatch_ls(args: argparse.Namespace) -> int:
    """Dispatch the ls command."""
    manifest = load_manifest(MANIFEST_FILE)

    from ksm.commands.ls import run_ls

    return run_ls(args, manifest=manifest)


def _dispatch_sync(args: argparse.Namespace) -> int:
    """Dispatch the sync command."""
    ensure_ksm_dir()
    registry_index = load_registry_index(REGISTRIES_FILE)
    manifest = load_manifest(MANIFEST_FILE)

    from ksm.commands.sync import run_sync

    return run_sync(
        args,
        registry_index=registry_index,
        manifest=manifest,
        manifest_path=MANIFEST_FILE,
        target_local=Path.cwd(),
        target_global=Path.home(),
    )


def _dispatch_add_registry(args: argparse.Namespace) -> int:
    """Dispatch the add-registry command."""
    ensure_ksm_dir()
    registry_index = load_registry_index(REGISTRIES_FILE)

    from ksm.commands.add_registry import run_add_registry

    return run_add_registry(
        args,
        registry_index=registry_index,
        registry_index_path=REGISTRIES_FILE,
        cache_dir=KSM_DIR / "cache",
    )


def _dispatch_rm(args: argparse.Namespace) -> int:
    """Dispatch the rm command."""
    ensure_ksm_dir()
    manifest = load_manifest(MANIFEST_FILE)

    from ksm.commands.rm import run_rm

    return run_rm(
        args,
        manifest=manifest,
        manifest_path=MANIFEST_FILE,
        target_local=Path.cwd(),
        target_global=Path.home(),
    )


def _dispatch_registry(args: argparse.Namespace) -> int:
    """Dispatch registry subcommands."""
    ensure_ksm_dir()
    registry_index = load_registry_index(REGISTRIES_FILE)
    subcmd = getattr(args, "registry_command", None)

    if subcmd == "ls":
        from ksm.commands.registry_ls import run_registry_ls

        return run_registry_ls(args, registry_index=registry_index)

    if subcmd == "rm":
        from ksm.commands.registry_rm import run_registry_rm

        return run_registry_rm(
            args,
            registry_index=registry_index,
            registry_index_path=REGISTRIES_FILE,
        )

    if subcmd == "inspect":
        from ksm.commands.registry_inspect import (
            run_registry_inspect,
        )

        return run_registry_inspect(args, registry_index=registry_index)

    if subcmd == "add":
        from ksm.commands.add_registry import run_add_registry

        return run_add_registry(
            args,
            registry_index=registry_index,
            registry_index_path=REGISTRIES_FILE,
            cache_dir=KSM_DIR / "cache",
        )

    # No subcommand — print help
    print(
        "usage: ksm registry {add,ls,rm,inspect}",
        file=sys.stderr,
    )
    return 2


def _dispatch_init(args: argparse.Namespace) -> int:
    """Dispatch the init command."""
    from ksm.commands.init import run_init

    try:
        registry_index = load_registry_index(REGISTRIES_FILE)
    except FileNotFoundError:
        registry_index = None

    try:
        manifest = load_manifest(MANIFEST_FILE)
    except Exception:
        manifest = None

    return run_init(
        args,
        target_dir=Path.cwd(),
        registry_index=registry_index,
        manifest=manifest,
    )


def _dispatch_info(args: argparse.Namespace) -> int:
    """Dispatch the info command."""
    registry_index = load_registry_index(REGISTRIES_FILE)
    manifest = load_manifest(MANIFEST_FILE)

    from ksm.commands.info import run_info

    return run_info(
        args,
        registry_index=registry_index,
        manifest=manifest,
    )


def _dispatch_search(args: argparse.Namespace) -> int:
    """Dispatch the search command."""
    registry_index = load_registry_index(REGISTRIES_FILE)

    from ksm.commands.search import run_search

    return run_search(args, registry_index=registry_index)


def _dispatch_completions(args: argparse.Namespace) -> int:
    """Dispatch the completions command."""
    from ksm.commands.completions import run_completions

    return run_completions(args)


# ------------------------------------------------------------------
# Command dispatch table
# ------------------------------------------------------------------

_DISPATCH_NAMES: dict[str, str] = {
    "add": "_dispatch_add",
    "ls": "_dispatch_ls",
    "sync": "_dispatch_sync",
    "add-registry": "_dispatch_add_registry",
    "rm": "_dispatch_rm",
    "registry": "_dispatch_registry",
    "init": "_dispatch_init",
    "info": "_dispatch_info",
    "search": "_dispatch_search",
    "completions": "_dispatch_completions",
}


def main() -> None:
    """Parse arguments and dispatch to the appropriate command."""
    parser = _build_parser()
    args = parser.parse_args()

    command = args.command
    if command is None:
        parser.print_help()
        raise SystemExit(2)

    func_name = _DISPATCH_NAMES.get(command)
    if func_name is None:
        parser.print_help()
        raise SystemExit(2)

    # Look up via module globals so patches take effect
    import ksm.cli as _self

    handler = getattr(_self, func_name)
    exit_code: int = handler(args)
    raise SystemExit(exit_code)
