"""CLI entry point for ksm.

Provides the ``main()`` function registered as the ``ksm`` console
script.  Uses argparse with subparsers for add, ls, sync,
registry (add/ls/rm/inspect), and rm.

Requirements: 4, 5, 8, 11, 23, 24, 27, 28
"""

import argparse
import re
import sys
import textwrap
from pathlib import Path
from typing import NoReturn

from ksm import __version__
from ksm.manifest import load_manifest, Manifest
from ksm.persistence import (
    ensure_ksm_dir,
    MANIFEST_FILE,
    REGISTRIES_FILE,
)
from ksm.registry import load_registry_index, RegistryIndex
from ksm.typo_suggest import suggest_command


class KsmArgumentParser(argparse.ArgumentParser):
    """Custom parser with typo suggestions for unknown commands.

    Overrides ``error()`` to detect unknown-command errors and
    suggest the closest valid command using Levenshtein distance.
    Always includes a ``ksm --help`` hint.

    Requirements: 24.1, 24.2, 24.3, 24.4
    """

    def error(self, message: str) -> NoReturn:
        """Override to suggest closest command on unknown command."""
        match = re.search(
            r"argument command: invalid choice: '([^']+)'",
            message,
        )
        if match:
            unknown = match.group(1)
            valid_cmds: list[str] = []
            for action in self._actions:
                if isinstance(action, argparse._SubParsersAction):
                    valid_cmds = list(action.choices.keys())
                    break

            suggestion = suggest_command(unknown, valid_cmds)
            parts = [f'Error: Unknown command "{unknown}"']
            if suggestion:
                parts.append(f'  Did you mean "{suggestion}"?')
            parts.append('  Run "ksm --help" to see all available' " commands.")
            self.exit(2, "\n".join(parts) + "\n")

        # For all other errors, add --help hint
        self.print_usage(sys.stderr)
        self.exit(
            2,
            f"ksm: error: {message}\n" f'Run "ksm --help" for more information.\n',
        )


def _build_parser() -> KsmArgumentParser:
    """Build the top-level argument parser with subparsers."""
    parser = KsmArgumentParser(
        prog="ksm",
        description=("Kiro Settings Manager — manage configuration bundles"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Use "ksm <command> --help" for more information.',
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    # Global verbose/quiet — mutually exclusive (Req 28)
    vq_group = parser.add_mutually_exclusive_group()
    vq_group.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Verbose output to stderr",
    )
    vq_group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress non-error output",
    )

    sub = parser.add_subparsers(dest="command")

    # --- add ---
    add_p = sub.add_parser(
        "add",
        help="Install a bundle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              ksm add my-bundle
              ksm add my-bundle --only skills
              ksm add my-bundle.steering.code-review
              ksm add --from https://github.com/org/repo.git my-bundle
              ksm add -i
        """),
    )
    add_p.add_argument(
        "bundle_spec",
        nargs="?",
        default=None,
        help="Bundle name or dot notation",
    )
    add_scope = add_p.add_mutually_exclusive_group()
    add_scope.add_argument(
        "-l",
        "--local",
        dest="local",
        action="store_true",
        help="Install locally",
    )
    add_scope.add_argument(
        "-g",
        "--global",
        dest="global_",
        action="store_true",
        help="Install globally",
    )
    add_p.add_argument(
        "-i",
        "--interactive",
        dest="interactive",
        action="store_true",
        help="Interactive bundle selector",
    )
    add_p.add_argument(
        "--display",
        dest="display",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    add_p.add_argument(
        "--from",
        dest="from_url",
        default=None,
        help="Ephemeral git registry URL",
    )
    add_p.add_argument(
        "--only",
        dest="only",
        action="append",
        choices=["skills", "agents", "steering", "hooks"],
        default=None,
        help="Install only specified subdirectory types",
    )
    add_p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview install without modifying files",
    )

    # --- ls ---
    sub.add_parser(
        "ls",
        help="List installed bundles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              ksm ls
              ksm --verbose ls
        """),
    )

    # --- sync ---
    sync_p = sub.add_parser(
        "sync",
        help="Sync installed bundles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              ksm sync --all --yes
              ksm sync my-bundle
              ksm sync my-bundle other-bundle --yes
        """),
    )
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
    sync_p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview sync without modifying files",
    )

    # --- registry subcommand group (Req 4) ---
    reg_p = sub.add_parser(
        "registry",
        help="Manage bundle registries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              ksm registry add https://github.com/org/bundles.git
              ksm registry ls
              ksm registry rm my-registry
        """),
    )
    reg_sub = reg_p.add_subparsers(dest="registry_command")
    reg_add_p = reg_sub.add_parser(
        "add",
        help="Register a git bundle registry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              ksm registry add https://github.com/org/bundles.git
              ksm registry add git@github.com:org/bundles.git
        """),
    )
    reg_add_p.add_argument("git_url", help="Git repository URL")
    reg_sub.add_parser(
        "ls",
        help="List registered registries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              ksm registry ls
              ksm --verbose registry ls
        """),
    )
    reg_rm_p = reg_sub.add_parser(
        "rm",
        help="Remove a registered registry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              ksm registry rm my-registry
              ksm registry rm other-registry
        """),
    )
    reg_rm_p.add_argument("name", help="Registry name")
    reg_inspect_p = reg_sub.add_parser(
        "inspect",
        help="Inspect a registry's bundles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              ksm registry inspect default
              ksm registry inspect my-registry
        """),
    )
    reg_inspect_p.add_argument("name", help="Registry name")

    # --- rm ---
    rm_p = sub.add_parser(
        "rm",
        help="Remove an installed bundle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              ksm rm my-bundle
              ksm rm my-bundle -g
              ksm rm -i
        """),
    )
    rm_p.add_argument(
        "bundle_name",
        nargs="?",
        default=None,
        help="Bundle to remove",
    )
    rm_scope = rm_p.add_mutually_exclusive_group()
    rm_scope.add_argument(
        "-l",
        "--local",
        dest="local",
        action="store_true",
        help="Remove local install",
    )
    rm_scope.add_argument(
        "-g",
        "--global",
        dest="global_",
        action="store_true",
        help="Remove global install",
    )
    rm_p.add_argument(
        "-i",
        "--interactive",
        dest="interactive",
        action="store_true",
        help="Interactive removal selector",
    )
    rm_p.add_argument(
        "--display",
        dest="display",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    rm_p.add_argument(
        "-y",
        "--yes",
        action="store_true",
        default=False,
        help="Skip confirmation prompt",
    )
    rm_p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview removal without modifying files",
    )

    return parser


def _handle_display_deprecation(
    args: argparse.Namespace,
) -> None:
    """Emit deprecation warning if --display was used (Req 11.3)."""
    if getattr(args, "display", False):
        print(
            "Warning: --display is deprecated, " "use --interactive / -i instead.",
            file=sys.stderr,
        )
        args.interactive = True


def _print_curated_help() -> None:
    """Print a curated help screen for first-time users (Req 16)."""
    print(
        f"ksm — Kiro Settings Manager v{__version__}\n"
        "\n"
        "Manage configuration bundles for Kiro IDE.\n"
        "\n"
        "Commands:\n"
        "  add <bundle>       Install a bundle\n"
        "  rm <bundle>        Remove an installed bundle\n"
        "  ls                 List installed bundles\n"
        "  sync               Update installed bundles\n"
        "  registry add       Register a bundle source\n"
        "  registry ls        List registered sources\n"
        "  registry rm        Remove a registered source\n"
        "  registry inspect   Inspect a registry\n"
        "\n"
        "Quick start:\n"
        "  ksm add -i                   Browse and install\n"
        "  ksm add my-bundle            Install a bundle\n"
        "  ksm ls                       See what's installed\n"
        "\n"
        'Run "ksm <command> --help" for detailed usage.'
    )


def main() -> None:
    """Parse args and dispatch to the appropriate command handler."""
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        _print_curated_help()
        raise SystemExit(2)

    # Handle --display deprecation on add/rm (Req 11)
    if args.command in ("add", "rm"):
        _handle_display_deprecation(args)

    # Registry subcommand group (Req 4)
    if args.command == "registry":
        reg_cmd = getattr(args, "registry_command", None)
        if reg_cmd is None:
            # Show registry help when no subcommand given
            for action in parser._actions:
                if isinstance(action, argparse._SubParsersAction):
                    reg_parser = action.choices.get("registry")
                    if reg_parser:
                        reg_parser.print_help()
                    break
            raise SystemExit(0)
        reg_dispatch = {
            "add": _dispatch_registry_add,
            "ls": _dispatch_registry_ls,
            "rm": _dispatch_registry_rm,
            "inspect": _dispatch_registry_inspect,
        }
        handler = reg_dispatch[reg_cmd]
        exit_code = handler(args)
        raise SystemExit(exit_code)

    dispatch = {
        "add": _dispatch_add,
        "ls": _dispatch_ls,
        "sync": _dispatch_sync,
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


def _dispatch_registry_add(args: argparse.Namespace) -> int:
    """Wire up and run the registry add command."""
    from ksm.commands.registry_add import run_registry_add

    ensure_ksm_dir()
    registry_index = _load_registry_index()

    from ksm.persistence import KSM_DIR

    return run_registry_add(
        args,
        registry_index=registry_index,
        registry_index_path=REGISTRIES_FILE,
        cache_dir=KSM_DIR / "cache",
    )


def _dispatch_registry_ls(args: argparse.Namespace) -> int:
    """Wire up and run the registry ls command (stub)."""
    print("registry ls: not yet implemented", file=sys.stderr)
    return 1


def _dispatch_registry_rm(args: argparse.Namespace) -> int:
    """Wire up and run the registry rm command (stub)."""
    print("registry rm: not yet implemented", file=sys.stderr)
    return 1


def _dispatch_registry_inspect(
    args: argparse.Namespace,
) -> int:
    """Wire up and run the registry inspect command (stub)."""
    print(
        "registry inspect: not yet implemented",
        file=sys.stderr,
    )
    return 1


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
