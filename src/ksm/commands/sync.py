"""Sync command for ksm.

Handles `ksm sync <bundle_name> [<bundle_name> ...]` and
`ksm sync --all` with optional --yes to skip confirmation.

Requirements: 13, 31.1
"""

import argparse
import sys
from pathlib import Path
from typing import TextIO

from ksm.color import SYM_ARROW, SYM_CHECK, SYM_DOT, accent, bold, muted, success
from ksm.commands.ide2cli import auto_convert
from ksm.copier import CopyResult, copy_tree, format_diff_summary
from ksm.errors import format_error, format_warning
from ksm.git_ops import pull_repo
from ksm.installer import install_bundle
from ksm.manifest import Manifest, ManifestEntry, find_entries, save_manifest
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


def _build_confirmation_message(
    entries: list[ManifestEntry],
    stream: TextIO | None = None,
) -> str:
    """Build confirmation listing bundles with scope and file count."""
    count_header = bold(f"Sync {len(entries)} bundles?", stream=stream)
    lines = [count_header]
    for e in entries:
        file_count = len(e.installed_files)
        file_word = "file" if file_count == 1 else "files"
        name = accent(e.bundle_name, stream=stream)
        meta = muted(
            f"{e.scope}  {SYM_DOT} {file_count} {file_word}",
            stream=stream,
        )
        lines.append(f"  {name}  {meta}")
    lines.append("")
    yn = bold("[y/n]", stream=stream)
    lines.append(f"This will overwrite configuration files." f" Continue? {yn} ")
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
        # Deduplicate by (bundle_name, scope, workspace_path)
        # to avoid syncing the same bundle multiple times per
        # workspace. Keeps first entry per key (oldest, since
        # entries are appended chronologically). Issue #28.
        seen: set[tuple[str, str, str | None]] = set()
        entries_to_sync = []
        for e in manifest.entries:
            key = (e.bundle_name, e.scope, e.workspace_path)
            if key not in seen:
                seen.add(key)
                entries_to_sync.append(e)
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
        prompt = _build_confirmation_message(entries_to_sync, stream=sys.stderr)
        try:
            response = input(prompt)
        except EOFError:
            response = "n"
        if response.strip() != "y":
            return 0

    # Dry-run: preview without modifying (Req 12.3)
    if dry_run:
        print(
            _build_confirmation_message(entries_to_sync, stream=sys.stderr).rstrip(
                "\nContinue? [y/n] "
            ),
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

    # Collect target workspaces for hook distribution
    if sync_all:
        ws_paths: set[str] = set()
        for e in manifest.entries:
            if e.scope == "local" and e.workspace_path:
                ws_paths.add(e.workspace_path)
        # Also include current workspace
        ws_paths.add(str(target_local.parent.resolve()))
        target_workspaces = [Path(p) for p in sorted(ws_paths)]
    else:
        target_workspaces = [target_local.parent]

    _sync_global_hooks(
        registry_index=registry_index,
        manifest=manifest,
        target_workspaces=target_workspaces,
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
    if entry.scope == "global":
        target_dir = target_global
    elif entry.workspace_path is not None:
        ws = Path(entry.workspace_path)
        if not ws.exists():
            print(
                format_warning(
                    f"Workspace '{entry.workspace_path}'" " no longer exists.",
                    f"Skipping sync for" f" '{entry.bundle_name}'.",
                    stream=sys.stderr,
                ),
                file=sys.stderr,
            )
            return
        target_dir = ws / ".kiro"
    else:
        target_dir = target_local

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
        check = success(SYM_CHECK, stream=sys.stderr)
        name = accent(entry.bundle_name, stream=sys.stderr)
        print(
            f"{check} Synced {name}",
            file=sys.stderr,
        )
        print(
            format_diff_summary(results, stream=sys.stderr),
            file=sys.stderr,
        )
        rel = [str(r.path.relative_to(target_dir)) for r in results]
        generated = auto_convert(target_dir, rel)
        if generated:
            ws_path: str | None = (
                str(target_dir.parent.resolve()) if entry.scope == "local" else None
            )
            matches = find_entries(
                manifest,
                entry.bundle_name,
                entry.scope,
                ws_path,
            )
            if matches:
                matches[0].installed_files.extend(generated)


def _sync_global_hooks(
    *,
    registry_index: RegistryIndex,
    manifest: Manifest,
    target_workspaces: list[Path],
) -> list[CopyResult]:
    """Copy hooks from global bundles to workspace(s).

    Finds global manifest entries with has_hooks=True, resolves
    each bundle from the registry, and copies only the hooks/
    subdirectory into each target workspace's .kiro/hooks/.

    Returns all CopyResult entries from the copy operations.
    """
    global_with_hooks = [
        e for e in manifest.entries if e.scope == "global" and e.has_hooks
    ]

    all_results: list[CopyResult] = []
    for entry in global_with_hooks:
        result = resolve_bundle(entry.bundle_name, registry_index)
        if not result.matches:
            searched = ", ".join(result.searched)
            print(
                format_warning(
                    f"Bundle '{entry.bundle_name}' not"
                    f" found in registries: {searched}",
                    "Skipping hook sync for this" " bundle.",
                    stream=sys.stderr,
                ),
                file=sys.stderr,
            )
            continue
        resolved = result.matches[0]

        # Check bundle actually has hooks/ subdir
        hooks_src = resolved.path / "hooks"
        if not hooks_src.is_dir():
            continue

        for ws_dir in target_workspaces:
            if not ws_dir.exists():
                print(
                    format_warning(
                        f"Workspace '{ws_dir}' no" " longer exists.",
                        "Skipping hook sync for this" " workspace.",
                        stream=sys.stderr,
                    ),
                    file=sys.stderr,
                )
                continue

            hooks_dst = ws_dir / ".kiro" / "hooks"
            results = copy_tree(hooks_src, hooks_dst)
            all_results.extend(results)

            if results:
                check = success(SYM_CHECK, stream=sys.stderr)
                name = accent(entry.bundle_name, stream=sys.stderr)
                arrow = SYM_ARROW
                print(
                    f"{check} Synced hooks from {name}"
                    f" {arrow} {ws_dir}/.kiro/hooks/",
                    file=sys.stderr,
                )
                print(
                    format_diff_summary(results, stream=sys.stderr),
                    file=sys.stderr,
                )

    return all_results
