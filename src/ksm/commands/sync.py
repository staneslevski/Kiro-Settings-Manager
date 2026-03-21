"""Sync command for ksm.

Handles `ksm sync <bundle_name> [<bundle_name> ...]` and
`ksm sync --all` with optional --yes to skip confirmation.

Requirements: 13, 31.1
"""

import argparse
import sys
from pathlib import Path

from ksm.color import green
from ksm.copier import format_diff_summary
from ksm.errors import format_error, format_warning
from ksm.git_ops import pull_repo
from ksm.installer import install_bundle
from ksm.manifest import Manifest, ManifestEntry, save_manifest
from ksm.registry import RegistryIndex
from ksm.resolver import resolve_bundle


def _check_tty_for_prompt(yes_flag: bool) -> bool:
    """Check if stdin is a TTY when confirmation is needed.

    If stdin is not a TTY and --yes is not provided, prints error
    to stderr and returns False. (Req 31.1)

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


def _build_confirmation_message(entries: list[ManifestEntry]) -> str:
    """Build specific confirmation listing bundle names and file counts.

    Format (Req 13.1, 13.2):
      Syncing N bundles: name1, name2, ...
      This will overwrite M configuration files in .kiro/ and/or ~/.kiro/.
      Continue? [y/n]
    """
    bundle_names = [e.bundle_name for e in entries]
    total_files = sum(len(e.installed_files) for e in entries)

    scopes = {e.scope for e in entries}
    if scopes == {"local"}:
        scope_desc = ".kiro/"
    elif scopes == {"global"}:
        scope_desc = "~/.kiro/"
    else:
        scope_desc = ".kiro/ and ~/.kiro/"

    lines = [
        f"Syncing {len(entries)} bundle(s): {', '.join(bundle_names)}",
        f"This will overwrite {total_files} configuration file(s) " f"in {scope_desc}.",
        "Continue? [y/n] ",
    ]
    return "\n".join(lines)


def run_sync(
    args: argparse.Namespace,
    *,
    registry_index: RegistryIndex,
    manifest: Manifest,
    manifest_path: Path,
    target_local: Path,
    target_global: Path,
) -> int:
    """Sync specified or all bundles. Returns exit code."""
    bundle_names: list[str] = getattr(args, "bundle_names", [])
    sync_all: bool = getattr(args, "all", False)
    skip_confirm: bool = getattr(args, "yes", False)
    dry_run: bool = getattr(args, "dry_run", False)

    if not bundle_names and not sync_all:
        print(
            format_error(
                "No bundles specified.",
                "Provide bundle name(s) or use --all.",
                "Example: ksm sync <bundle> or" " ksm sync --all",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        return 1

    # Determine which bundles to sync
    if sync_all:
        entries_to_sync = list(manifest.entries)
    else:
        entries_to_sync = []
        for name in bundle_names:
            matches = [e for e in manifest.entries if e.bundle_name == name]
            if not matches:
                print(
                    format_error(
                        f"Bundle '{name}' is not installed.",
                        "Cannot sync a bundle that is not" " installed.",
                        "Run `ksm list` to see installed" " bundles.",
                        stream=sys.stderr,
                    ),
                    file=sys.stderr,
                )
                continue
            entries_to_sync.extend(matches)

    if not entries_to_sync:
        return 0

    # TTY check before confirmation (Req 31.1)
    if not skip_confirm:
        if not _check_tty_for_prompt(skip_confirm):
            return 1
        # Build specific confirmation message (Req 13.1, 13.2)
        prompt = _build_confirmation_message(entries_to_sync)
        try:
            response = input(prompt)
        except EOFError:
            response = "n"
        if response.strip() != "y":
            return 0

    # Dry-run: preview without modifying (Req 12.3)
    if dry_run:
        print(
            _build_confirmation_message(entries_to_sync).rstrip("\nContinue? [y/n] "),
            file=sys.stderr,
        )
        return 0

    # Pull latest for custom git registries
    _pull_custom_registries(registry_index)

    # Sync each bundle
    for entry in entries_to_sync:
        _sync_entry(
            entry,
            registry_index=registry_index,
            manifest=manifest,
            target_local=target_local,
            target_global=target_global,
        )

    save_manifest(manifest, manifest_path)
    return 0


def _pull_custom_registries(
    registry_index: RegistryIndex,
) -> None:
    """Pull latest changes for non-default git registries."""
    for reg in registry_index.registries:
        if not reg.is_default and reg.url is not None:
            try:
                pull_repo(Path(reg.local_path))
            except Exception as e:
                print(
                    format_warning(
                        f"Failed to pull {reg.name}: {e}",
                        "Sync will use the local cache.",
                        stream=sys.stderr,
                    ),
                    file=sys.stderr,
                )


def _sync_entry(
    entry: ManifestEntry,
    *,
    registry_index: RegistryIndex,
    manifest: Manifest,
    target_local: Path,
    target_global: Path,
) -> None:
    """Re-install a single bundle from its source registry."""
    target_dir = target_global if entry.scope == "global" else target_local

    result = resolve_bundle(entry.bundle_name, registry_index)
    if not result.matches:
        searched = ", ".join(result.searched)
        print(
            format_warning(
                f"Bundle '{entry.bundle_name}' not found" f" in registries: {searched}",
                "Skipping sync for this bundle.",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        return
    resolved = result.matches[0]

    try:
        results = install_bundle(
            bundle=resolved,
            target_dir=target_dir,
            scope=entry.scope,
            subdirectory_filter=None,
            dot_selection=None,
            manifest=manifest,
            source_label=resolved.registry_name,
        )
    except SystemExit:
        print(
            format_warning(
                f"Failed to sync '{entry.bundle_name}'.",
                "The bundle may have changed upstream.",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        return

    if results:
        prefix = green("Synced:", stream=sys.stderr)
        print(
            f"{prefix} '{entry.bundle_name}'",
            file=sys.stderr,
        )
        print(
            format_diff_summary(results),
            file=sys.stderr,
        )
