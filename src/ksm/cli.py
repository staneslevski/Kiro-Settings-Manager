"""CLI entry point for ksm.

Provides the ``main()`` function registered as the ``ksm`` console
script.  Uses argparse with subparsers for add, ls, sync, rm,
add-registry, registry (add/ls/rm/inspect), init, info, search,
and completions.

Requirements: 4.1–4.4, 8.1–8.5, 17, 18, 19, 20, 21
"""

import argparse
import sys
import textwrap
from pathlib import Path

from ksm import __version__
from ksm.manifest import load_manifest, save_manifest
from ksm.persistence import (
    ensure_ksm_dir,
    KSM_DIR,
    MANIFEST_FILE,
    REGISTRIES_FILE,
    CONFIG_BUNDLES_DIR,
)
from ksm.registry import load_registry_index


def _add_list_args(parser: argparse.ArgumentParser) -> None:
    """Add shared arguments for list/ls subcommands."""
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show installed file paths under each bundle",
    )
    parser.add_argument(
        "--scope",
        choices=["local", "global"],
        default=None,
        help="Show only bundles in this scope (local or global)",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["text", "json"],
        default="text",
        help="Output format: text (default, grouped by scope) or json",
    )
    parser.add_argument(
        "--all",
        dest="show_all",
        action="store_true",
        help="Show bundles from all workspaces",
    )


def _add_rm_args(parser: argparse.ArgumentParser) -> None:
    """Add shared arguments for remove/rm subcommands."""
    parser.add_argument(
        "bundle_name",
        nargs="?",
        default=None,
        help="Bundle name to remove",
    )
    parser.add_argument(
        "-l",
        "--local",
        dest="local",
        action="store_true",
        help="Remove from local scope",
    )
    parser.add_argument(
        "-g",
        "--global",
        dest="global_",
        action="store_true",
        help="Remove from global scope",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Launch interactive removal selector",
    )
    parser.add_argument(
        "--display",
        action="store_true",
        help=argparse.SUPPRESS,
    )


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
        "-i",
        "--interactive",
        action="store_true",
        help="Launch interactive selector",
    )
    add_p.add_argument(
        "--display",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    add_p.add_argument(
        "--from",
        dest="from_url",
        default=None,
        help="Ephemeral git URL to install from",
    )
    add_p.add_argument(
        "--only",
        default=None,
        help="Install only specified subdirectories (comma-separated)",
    )
    add_p.add_argument(
        "--skills-only",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    add_p.add_argument(
        "--agents-only",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    add_p.add_argument(
        "--steering-only",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    add_p.add_argument(
        "--hooks-only",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    # --- list (primary) with ls as hidden alias ---
    _list_desc = (
        "Show all bundles currently tracked in the manifest.\n"
        "\n"
        "Reads ~/.kiro/ksm/manifest.json and prints every installed\n"
        "bundle grouped by scope (local first, then global). Each\n"
        "entry shows the bundle name, source registry, and a\n"
        "relative timestamp of the last install or sync.\n"
        "\n"
        "With --verbose, the individual files that belong to each\n"
        "bundle are listed underneath it. Use --scope to restrict\n"
        "output to a single scope, and --format json to get\n"
        "machine-readable output suitable for piping to jq."
    )
    _list_epilog = textwrap.dedent("""\
        examples:
          ksm list                  List all installed bundles
          ksm list -v               Include installed file paths
          ksm list --scope local    Show only workspace-level bundles
          ksm list --scope global   Show only user-level bundles
          ksm list --format json    Output as JSON (pipe to jq)
    """)
    list_p = sub.add_parser(
        "list",
        help="List installed bundles (ls)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=_list_desc,
        epilog=_list_epilog,
    )
    _add_list_args(list_p)

    ls_p = sub.add_parser("ls", help=argparse.SUPPRESS)
    _add_list_args(ls_p)

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

    # --- remove (primary) with rm as hidden alias ---
    remove_p = sub.add_parser("remove", help="Remove an installed bundle (rm)")
    _add_rm_args(remove_p)

    rm_p = sub.add_parser("rm", help=argparse.SUPPRESS)
    _add_rm_args(rm_p)

    # --- add-registry ---
    ar_p = sub.add_parser("add-registry", help="Register a git bundle registry")
    ar_p.add_argument("git_url", help="Git URL of the registry")
    ar_p.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force re-clone of cached registry",
    )
    ar_p.add_argument(
        "--name",
        default=None,
        help="Custom name for the registry",
    )

    # --- registry (subcommand group) ---
    reg_p = sub.add_parser("registry", help="Manage registries")
    reg_sub = reg_p.add_subparsers(dest="registry_command")

    reg_add_p = reg_sub.add_parser("add", help="Add a registry")
    reg_add_p.add_argument("git_url", help="Git URL of the registry")
    reg_add_p.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force re-clone of cached registry",
    )
    reg_add_p.add_argument(
        "--name",
        default=None,
        help="Custom name for the registry",
    )

    reg_sub.add_parser(
        "list",
        aliases=["ls"],
        help="List registries (ls)",
    )

    reg_rm_p = reg_sub.add_parser(
        "remove",
        aliases=["rm"],
        help="Remove a registry (rm)",
    )
    reg_rm_p.add_argument(
        "registry_name",
        help="Name of registry to remove",
    )

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

    # --- ide2cli ---
    _ide2cli_desc = (
        "Convert Kiro IDE-format agent and hook files to\n"
        "CLI-compatible JSON. Scans both the workspace .kiro/\n"
        "and global ~/.kiro/ directories in a single pass.\n"
        "The IDE files remain the source of truth; the CLI\n"
        "JSON files are derived output.\n"
        "\n"
        "Agents: .md files in agents/ with YAML frontmatter\n"
        "(name, description, tools) are converted to .json\n"
        "files in the same directory. IDE tool names are\n"
        "mapped automatically (e.g. read -> fs_read).\n"
        "\n"
        "Hooks: .kiro.hook files in hooks/ are converted to a\n"
        "grouped _cli_hooks.json file. Event types are mapped\n"
        "(e.g. promptSubmit -> userPromptSubmit). Hooks with\n"
        "enabled: false are skipped. Hook types without a CLI\n"
        "equivalent are skipped with a warning.\n"
        "\n"
        "Skills and steering use identical formats on both\n"
        "platforms and need no conversion.\n"
        "\n"
        "The command is idempotent — running it multiple times\n"
        "on unchanged input produces identical output."
    )
    sub.add_parser(
        "ide2cli",
        help="Convert IDE agent/hook files to CLI JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=_ide2cli_desc,
    )

    # Hide short aliases from the top-level choices metavar
    # so help shows only full-word primaries.
    _hidden = {"ls", "rm"}
    if parser._subparsers is not None:
        for action in parser._subparsers._actions:
            if isinstance(action, argparse._SubParsersAction):
                action._choices_actions = [
                    a for a in action._choices_actions if a.dest not in _hidden
                ]
                visible = [k for k in action.choices if k not in _hidden]
                action.metavar = "{" + ",".join(visible) + "}"
                break

    return parser


# ------------------------------------------------------------------
# Dispatch helpers
# ------------------------------------------------------------------


def _dispatch_add(args: argparse.Namespace) -> int:
    """Dispatch the add command."""
    ensure_ksm_dir()
    registry_index = load_registry_index(
        REGISTRIES_FILE, default_registry_path=CONFIG_BUNDLES_DIR
    )
    manifest = load_manifest(MANIFEST_FILE)

    from ksm.manifest import backfill_workspace_paths

    cwd = Path.cwd()
    if backfill_workspace_paths(manifest, cwd):
        save_manifest(manifest, MANIFEST_FILE)

    from ksm.commands.add import run_add

    return run_add(
        args,
        registry_index=registry_index,
        manifest=manifest,
        manifest_path=MANIFEST_FILE,
        target_local=cwd / ".kiro",
        target_global=Path.home() / ".kiro",
    )


def _dispatch_ls(args: argparse.Namespace) -> int:
    """Dispatch the ls command."""
    manifest = load_manifest(MANIFEST_FILE)

    from ksm.commands.ls import run_ls
    from ksm.manifest import backfill_workspace_paths

    cwd = Path.cwd()
    if backfill_workspace_paths(manifest, cwd):
        save_manifest(manifest, MANIFEST_FILE)

    return run_ls(
        args,
        manifest=manifest,
        workspace_path=str(cwd.resolve()),
    )


def _dispatch_sync(args: argparse.Namespace) -> int:
    """Dispatch the sync command."""
    ensure_ksm_dir()
    registry_index = load_registry_index(
        REGISTRIES_FILE, default_registry_path=CONFIG_BUNDLES_DIR
    )
    manifest = load_manifest(MANIFEST_FILE)

    from ksm.manifest import backfill_workspace_paths

    cwd = Path.cwd()
    if backfill_workspace_paths(manifest, cwd):
        save_manifest(manifest, MANIFEST_FILE)

    from ksm.commands.sync import run_sync

    return run_sync(
        args,
        registry_index=registry_index,
        manifest=manifest,
        manifest_path=MANIFEST_FILE,
        target_local=cwd / ".kiro",
        target_global=Path.home() / ".kiro",
    )


def _dispatch_add_registry(args: argparse.Namespace) -> int:
    """Dispatch the add-registry command."""
    ensure_ksm_dir()
    registry_index = load_registry_index(
        REGISTRIES_FILE, default_registry_path=CONFIG_BUNDLES_DIR
    )

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

    from ksm.manifest import backfill_workspace_paths

    cwd = Path.cwd()
    if backfill_workspace_paths(manifest, cwd):
        save_manifest(manifest, MANIFEST_FILE)

    from ksm.commands.rm import run_rm

    return run_rm(
        args,
        manifest=manifest,
        manifest_path=MANIFEST_FILE,
        target_local=cwd / ".kiro",
        target_global=Path.home() / ".kiro",
    )


def _dispatch_registry(args: argparse.Namespace) -> int:
    """Dispatch registry subcommands."""
    ensure_ksm_dir()
    registry_index = load_registry_index(
        REGISTRIES_FILE, default_registry_path=CONFIG_BUNDLES_DIR
    )
    subcmd = getattr(args, "registry_command", None)

    if subcmd in ("list", "ls"):
        from ksm.commands.registry_ls import run_registry_ls

        return run_registry_ls(args, registry_index=registry_index)

    if subcmd in ("remove", "rm"):
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
        from ksm.commands.registry_add import run_registry_add

        return run_registry_add(
            args,
            registry_index=registry_index,
            registry_index_path=REGISTRIES_FILE,
            cache_dir=KSM_DIR / "cache",
        )

    # No subcommand — print help
    print(
        "usage: ksm registry" " {add,remove,list,inspect}",
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
    registry_index = load_registry_index(
        REGISTRIES_FILE, default_registry_path=CONFIG_BUNDLES_DIR
    )
    manifest = load_manifest(MANIFEST_FILE)

    from ksm.commands.info import run_info

    return run_info(
        args,
        registry_index=registry_index,
        manifest=manifest,
    )


def _dispatch_search(args: argparse.Namespace) -> int:
    """Dispatch the search command."""
    registry_index = load_registry_index(
        REGISTRIES_FILE, default_registry_path=CONFIG_BUNDLES_DIR
    )

    from ksm.commands.search import run_search

    return run_search(args, registry_index=registry_index)


def _dispatch_completions(args: argparse.Namespace) -> int:
    """Dispatch the completions command."""
    from ksm.commands.completions import run_completions

    return run_completions(args)


def _dispatch_ide2cli(args: argparse.Namespace) -> int:
    """Dispatch the ide2cli command."""
    from ksm.commands.ide2cli import run_ide2cli

    return run_ide2cli(args)


# ------------------------------------------------------------------
# Command dispatch table
# ------------------------------------------------------------------

_DISPATCH_NAMES: dict[str, str] = {
    "add": "_dispatch_add",
    "list": "_dispatch_ls",
    "ls": "_dispatch_ls",
    "sync": "_dispatch_sync",
    "add-registry": "_dispatch_add_registry",
    "remove": "_dispatch_rm",
    "rm": "_dispatch_rm",
    "registry": "_dispatch_registry",
    "init": "_dispatch_init",
    "info": "_dispatch_info",
    "search": "_dispatch_search",
    "completions": "_dispatch_completions",
    "ide2cli": "_dispatch_ide2cli",
}


def main() -> None:
    """Parse arguments and dispatch to the appropriate command."""
    from ksm.signal_handler import install_signal_handler

    install_signal_handler()

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
