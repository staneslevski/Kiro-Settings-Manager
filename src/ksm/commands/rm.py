"""Rm command for ksm.

Handles ``ksm rm <bundle_name>`` with flags ``-l``, ``-g``,
``--interactive``/``-i``, ``--yes``/``-y``, ``--dry-run``.

Requirements: 1, 2, 31.2
"""

import argparse
import sys
from pathlib import Path
from typing import TextIO

from ksm.color import SYM_CHECK, accent, bold, info, muted, success
from ksm.errors import format_deprecation, format_error, format_warning
from ksm.manifest import Manifest, ManifestEntry, find_entries, save_manifest
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
    """Build confirmation prompt listing files to be removed."""
    file_count = len(entry.installed_files)
    name = accent(entry.bundle_name, stream=stream)
    scope_label = info(entry.scope, stream=stream)
    count_str = muted(f"{file_count} files in .kiro/:", stream=stream)
    lines = [
        f"Remove {name} from {scope_label} scope?",
        f"  {count_str}",
    ]
    for f in entry.installed_files:
        lines.append(f"    {muted(f, stream=stream)}")
    lines.append("")
    yn = bold("[y/n]", stream=stream)
    lines.append(f"Continue? {yn} ")
    return "\n".join(lines)


def _format_result(
    bundle_name: str,
    scope: str,
    result: RemovalResult,
    stream: TextIO | None = None,
) -> str:
    """Build summary message from RemovalResult."""
    removed = len(result.removed_files)
    skipped = len(result.skipped_files)
    check = success(SYM_CHECK, stream=stream)
    name = accent(bundle_name, stream=stream)

    if skipped == 0:
        summary = muted(f"{removed} files deleted ({scope})", stream=stream)
    elif removed == 0:
        summary = muted(
            f"all {skipped} files were already missing ({scope})",
            stream=stream,
        )
    else:
        summary = muted(
            f"{removed} files deleted," f" {skipped} already missing ({scope})",
            stream=stream,
        )
    return f"{check} Removed {name} — {summary}"


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

        # Filter entries by scope if -l/-g provided (Req 14.3)
        entries_to_show = manifest.entries
        if getattr(args, "global_", False):
            entries_to_show = [e for e in manifest.entries if e.scope == "global"]
        elif getattr(args, "local", False):
            entries_to_show = [e for e in manifest.entries if e.scope == "local"]

        if not entries_to_show:
            print("No matching bundles at the" " specified scope.")
            return 0

        # Filter local entries to current workspace only
        workspace_path = str(target_local.parent.resolve())
        entries_to_show = [
            e
            for e in entries_to_show
            if e.scope == "global" or e.workspace_path == workspace_path
        ]

        if not entries_to_show:
            print("No matching bundles at the" " specified scope.")
            return 0

        selected_list = interactive_removal_select(entries_to_show)
        if selected_list is None:
            return 0

        selected = selected_list[0]
        scope = selected.scope
        target_dir = target_global if scope == "global" else target_local

        # Confirmation prompt for interactive path (Req 1.6)
        if not yes_flag:
            if not _check_tty_for_prompt(yes_flag):
                return 1
            prompt = _format_confirmation(selected, stream=sys.stderr)
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

    # Find matching manifest entry (workspace-aware for local scope)
    if scope == "local":
        workspace_path = str(target_local.parent.resolve())
        matches = find_entries(manifest, bundle_name, scope, workspace_path)
    else:
        matches = find_entries(manifest, bundle_name, scope)

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
        prompt = _format_confirmation(entry, stream=sys.stderr)
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
