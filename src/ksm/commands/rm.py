"""Rm command for ksm.

Handles ``ksm rm <bundle_name>`` with flags ``-l``, ``-g``,
``--interactive``/``-i``, ``--yes``/``-y``, ``--dry-run``.

Requirements: 1, 2, 31.2
"""

import argparse
import sys
from pathlib import Path

from ksm.errors import format_deprecation
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
            "Error: confirmation required but stdin is not a terminal.\n"
            "  Use --yes to skip confirmation in non-interactive mode.",
            file=sys.stderr,
        )
        return False
    return True


def _format_confirmation(entry: ManifestEntry) -> str:
    """Build confirmation prompt listing files to be removed.

    Format (Req 1.1):
      This will remove <N> files from <scope> scope:
        <file1>
        <file2>
        ...

      Continue? [y/n]
    """
    file_count = len(entry.installed_files)
    scope_desc = ".kiro/" if entry.scope == "local" else "~/.kiro/"
    lines = [
        f"This will remove '{entry.bundle_name}' ({entry.scope} scope):",
        f"  {file_count} file(s) in {scope_desc}",
    ]
    for f in entry.installed_files:
        lines.append(f"    {f}")
    lines.append("")
    lines.append("Continue? [y/n] ")
    return "\n".join(lines)


def _format_result(
    bundle_name: str,
    scope: str,
    result: RemovalResult,
) -> str:
    """Build summary message from RemovalResult.

    Format (Req 2.1, 2.2, 2.3):
      Removed '<bundle>' (<scope>): <N> files deleted
      Removed '<bundle>' (<scope>): <N> files deleted, <M> already missing
    """
    removed = len(result.removed_files)
    skipped = len(result.skipped_files)

    if skipped == 0:
        return f"Removed '{bundle_name}' ({scope}): {removed} file(s) deleted"
    elif removed == 0:
        return (
            f"Removed '{bundle_name}' ({scope}): "
            f"all {skipped} file(s) were already missing"
        )
    else:
        return (
            f"Removed '{bundle_name}' ({scope}): "
            f"{removed} file(s) deleted, {skipped} already missing"
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
            ),
            file=sys.stderr,
        )
        interactive = True

    # Determine bundle_name early for -i ignore check
    bundle_name: str | None = getattr(args, "bundle_name", None)

    # If bundle_name provided AND -i, ignore -i (Req 5.10)
    if bundle_name and interactive:
        print(
            "Warning: -i ignored because a bundle" " was specified.",
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
            prompt = _format_confirmation(selected)
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
        print(_format_result(selected.bundle_name, scope, result), file=sys.stderr)
        return 0

    # Determine scope and target
    if bundle_name is None:
        print("Error: no bundle specified", file=sys.stderr)
        return 1

    scope = "global" if getattr(args, "global_", False) else "local"
    target_dir = target_global if scope == "global" else target_local

    # Find matching manifest entry
    matches = [
        e for e in manifest.entries if e.bundle_name == bundle_name and e.scope == scope
    ]

    if not matches:
        print(
            f"Error: bundle '{bundle_name}' is not installed " f"at {scope} scope",
            file=sys.stderr,
        )
        return 1

    entry = matches[0]

    # Confirmation prompt (Req 1.1, 1.2, 1.3, 1.5)
    if not yes_flag:
        if not _check_tty_for_prompt(yes_flag):
            return 1
        prompt = _format_confirmation(entry)
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
    print(_format_result(bundle_name, scope, result), file=sys.stderr)
    return 0
