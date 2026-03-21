"""Rm command for ksm.

Handles ``ksm rm <bundle_name>`` with flags ``-l``, ``-g``,
``--interactive``/``-i``, ``--yes``/``-y``, ``--dry-run``.

Requirements: 1, 2, 31.2
"""

import argparse
import sys
from pathlib import Path
from typing import TextIO

from ksm.color import bold, dim, green
from ksm.errors import format_deprecation, format_error, format_warning
from ksm.manifest import Manifest, ManifestEntry, save_manifest
from ksm.remover import RemovalResult, remove_bundle
from ksm.selector import interactive_removal_select


def _check_tty_for_prompt(yes_flag: bool) -> bool:
    """Check if stdin is a TTY when confirmation is needed.

    If stdin is not a TTY and --yes is not provided, prints error
    to stderr and returns False. (Req 31.2)

    Returns True if we can proceed (either TTY or --yes provided).
    """
    if not sys.stdin.isatty():
        print(
            format_error(
                "Confirmation required but stdin is" " not a terminal.",
                "Non-interactive mode detected.",
                "Use --yes to skip confirmation.",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        return False
    return True


def _format_confirmation(
    entry: ManifestEntry,
    stream: TextIO | None = None,
) -> str:
    """Build confirmation prompt listing files to be removed.

    Format (Req 1.1, 7.1–7.4):
      This will remove <N> files from <scope> scope:
        <file1>
        <file2>
        ...

      Continue? [y/n]
    """
    file_count = len(entry.installed_files)
    raw_scope = (
        ".kiro/" if entry.scope == "local" else "~/.kiro/"
    )
    scope_desc = bold(raw_scope, stream=stream)
    lines = [
        f"This will remove '{entry.bundle_name}'"
        f" ({entry.scope} scope):",
        f"  {file_count} file(s) in {scope_desc}",
    ]
    for f in entry.installed_files:
        lines.append(f"    {dim(f, stream=stream)}")
    lines.append("")
    lines.append("Continue? [y/n] ")
    return "\n".join(lines)


def _format_result(
    bundle_name: str,
    scope: str,
    result: RemovalResult,
    stream: TextIO | None = None,
) -> str:
    """Build summary message from RemovalResult.

    Format (Req 2.1, 2.2, 2.3):
      Removed '<bundle>' (<scope>): <N> files deleted
      Removed '<bundle>' (<scope>): <N> files deleted, <M> already missing
    """
    removed = len(result.removed_files)
    skipped = len(result.skipped_files)
    prefix = green("Removed", stream=stream)

    if skipped == 0:
        return (
            f"{prefix} '{bundle_name}' ({scope}):"
            f" {removed} file(s) deleted"
        )
    elif removed == 0:
        return (
            f"{prefix} '{bundle_name}' ({scope}): "
            f"all {skipped} file(s) were already missing"
        )
    else:
        return (
            f"{prefix} '{bundle_name}' ({scope}): "
            f"{removed} file(s) deleted,"
            f" {skipped} already missing"
        )


def _format_dry_run_rm(entry: ManifestEntry) -> str:
    """Build dry-run preview for rm command (Req 12.2)."""
    scope_desc = ".kiro/" if entry.scope == "local" else "~/.kiro/"
    lines = [
        f"Would remove '{entry.bundle_name}' ({entry.scope} scope):",
        f"  {len(entry.installed_files)} file(s) in {scope_desc}",
    ]
    for f in entry.installed_files:
        lines.append(f"    {f}")
    return "\n".join(lines)


def run_rm(
    args: argparse.Namespace,
    *,
    manifest: Manifest,
    manifest_path: Path,
    target_local: Path,
    target_global: Path,
) -> int:
    """Execute the rm command. Returns exit code."""
    yes_flag: bool = getattr(args, "yes", False)
    dry_run: bool = getattr(args, "dry_run", False)

    # Handle --display deprecation (Req 5.6)
    display = getattr(args, "display", False)
    interactive = getattr(args, "interactive", False)
    if display:
        print(
            format_deprecation(
                "--display",
                "-i/--interactive",
                "v0.2.0",
                "v1.0.0",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        interactive = True

    # Determine bundle_name early for -i ignore check
    bundle_name: str | None = getattr(args, "bundle_name", None)

    # If bundle_name provided AND -i, ignore -i (Req 5.10)
    if bundle_name and interactive:
        print(
            format_warning(
                "-i ignored because a bundle" " was specified.",
                "Proceeding with the specified bundle.",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        interactive = False

    # Handle --interactive mode
    if interactive:
        if not manifest.entries:
            print("No bundles currently installed.")
            return 0

        selected_list = interactive_removal_select(manifest.entries)
        if selected_list is None:
            return 0

        selected = selected_list[0]
        scope = selected.scope
        target_dir = target_global if scope == "global" else target_local

        # Confirmation prompt for interactive path (Req 1.6)
        if not yes_flag:
            if not _check_tty_for_prompt(yes_flag):
                return 1
            prompt = _format_confirmation(
                selected, stream=sys.stderr
            )
            try:
                response = input(prompt)
            except EOFError:
                return 0
            if response.strip() != "y":
                return 0

        # Dry-run: preview without modifying (Req 12.2)
        if dry_run:
            print(_format_dry_run_rm(selected), file=sys.stderr)
            return 0

        result = remove_bundle(selected, target_dir, manifest)
        save_manifest(manifest, manifest_path)
        print(
            _format_result(
                selected.bundle_name,
                scope,
                result,
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        return 0

    # Determine scope and target
    if bundle_name is None:
        print(
            format_error(
                "No bundle specified.",
                "Provide a bundle name or use -i" " for interactive mode.",
                "Example: ksm rm <bundle_name>",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        return 1

    scope = "global" if getattr(args, "global_", False) else "local"
    target_dir = target_global if scope == "global" else target_local

    # Find matching manifest entry
    matches = [
        e for e in manifest.entries if e.bundle_name == bundle_name and e.scope == scope
    ]

    if not matches:
        print(
            format_error(
                f"Bundle '{bundle_name}' is not installed" f" at {scope} scope.",
                "The bundle may be installed at a" " different scope.",
                "Run `ksm list` to see installed" " bundles.",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        return 1

    entry = matches[0]

    # Confirmation prompt (Req 1.1, 1.2, 1.3, 1.5)
    if not yes_flag:
        if not _check_tty_for_prompt(yes_flag):
            return 1
        prompt = _format_confirmation(
            entry, stream=sys.stderr
        )
        try:
            response = input(prompt)
        except EOFError:
            return 0
        if response.strip() != "y":
            return 0

    # Dry-run: preview without modifying (Req 12.2)
    if dry_run:
        print(_format_dry_run_rm(entry), file=sys.stderr)
        return 0

    result = remove_bundle(entry, target_dir, manifest)
    save_manifest(manifest, manifest_path)
    print(
        _format_result(
            bundle_name,
            scope,
            result,
            stream=sys.stderr,
        ),
        file=sys.stderr,
    )
    return 0
