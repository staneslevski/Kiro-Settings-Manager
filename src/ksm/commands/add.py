"""Add command for ksm.

Handles ``ksm add <bundle_spec>`` with flags ``-l``, ``-g``,
``--interactive``/``-i``, ``--from``, ``--only <type>``.
"""

import argparse
import shutil
import sys
from pathlib import Path

from ksm.dot_notation import (
    DotSelection,
    parse_dot_notation,
    validate_dot_selection,
)
from ksm.copier import format_diff_summary
from ksm.errors import (
    BundleNotFoundError,
    GitError,
    InvalidSubdirectoryError,
)
from ksm.git_ops import (
    checkout_version,
    clone_ephemeral,
    list_versions,
)
from ksm.installer import install_bundle
from ksm.manifest import Manifest, save_manifest
from ksm.registry import RegistryEntry, RegistryIndex
from ksm.resolver import resolve_bundle
from ksm.scanner import scan_registry
from ksm.selector import interactive_select
from ksm.signal_handler import unregister_temp_dir


def _build_subdirectory_filter(
    args: argparse.Namespace,
) -> set[str] | None:
    """Build subdirectory filter set from --only flags (Req 5)."""
    only: list[str] | None = getattr(args, "only", None)
    if only:
        return set(only)
    # Support individual *_only flags from CLI
    result: set[str] = set()
    if getattr(args, "skills_only", False):
        result.add("skills")
    if getattr(args, "steering_only", False):
        result.add("steering")
    if getattr(args, "hooks_only", False):
        result.add("hooks")
    if getattr(args, "agents_only", False):
        result.add("agents")
    return result if result else None


def _format_dry_run_add(
    bundle_name: str,
    scope: str,
    target_dir: Path,
    subdirectory_filter: set[str] | None,
) -> str:
    """Build dry-run preview for add command (Req 12.1)."""
    scope_desc = ".kiro/" if scope == "local" else "~/.kiro/"
    lines = [f"Would install '{bundle_name}' to {scope_desc} ({scope} scope)"]
    if subdirectory_filter:
        lines.append(f"  Subdirectories: {', '.join(sorted(subdirectory_filter))}")
    lines.append(f"  Target: {target_dir}")
    return "\n".join(lines)


def parse_version_spec(spec: str) -> tuple[str, str | None]:
    """Parse 'bundle@version' syntax.

    Returns (bundle_spec, version) where version is None if
    no '@' is present.
    """
    if "@" in spec:
        parts = spec.rsplit("@", 1)
        return parts[0], parts[1] if parts[1] else None
    return spec, None


def run_add(
    args: argparse.Namespace,
    *,
    registry_index: RegistryIndex,
    manifest: Manifest,
    manifest_path: Path,
    target_local: Path,
    target_global: Path,
) -> int:
    """Execute the add command. Returns exit code."""
    subdirectory_filter = _build_subdirectory_filter(args)

    # Parse bundle spec for dot notation
    bundle_spec: str | None = getattr(args, "bundle_spec", None)
    dot_selection: DotSelection | None = None

    # Handle --interactive mode (also triggered by --display alias)
    display = getattr(args, "display", False) or getattr(args, "interactive", False)
    if display:
        bundle_name = _handle_display(registry_index, manifest)
        if bundle_name is None:
            return 0
        bundle_spec = bundle_name

    if bundle_spec is None:
        # Auto-launch selector if TTY (Req 9)
        if sys.stdin.isatty():
            bundle_name = _handle_display(registry_index, manifest)
            if bundle_name is None:
                return 0
            bundle_spec = bundle_name
        else:
            print(
                "Error: no bundle specified",
                file=sys.stderr,
            )
            return 1

    # Parse dot notation
    dot_selection = parse_dot_notation(bundle_spec)
    if dot_selection is not None:
        try:
            validate_dot_selection(dot_selection)
        except InvalidSubdirectoryError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        bundle_spec = dot_selection.bundle_name

    # Parse version spec (bundle@version)
    version: str | None = None
    bundle_spec, version = parse_version_spec(bundle_spec)

    # Check mutual exclusion: dot notation + subdirectory filter
    if dot_selection is not None and subdirectory_filter is not None:
        print(
            "Error: dot notation and subdirectory filter "
            "flags are mutually exclusive",
            file=sys.stderr,
        )
        return 1

    # Determine scope
    scope = "global" if getattr(args, "global_", False) else "local"
    target_dir = target_global if scope == "global" else target_local
    dry_run: bool = getattr(args, "dry_run", False)

    # Dry-run: preview without modifying (Req 12.1)
    if dry_run:
        print(
            _format_dry_run_add(bundle_spec, scope, target_dir, subdirectory_filter),
            file=sys.stderr,
        )
        return 0

    # Handle --from ephemeral registry
    from_url: str | None = getattr(args, "from_url", None)
    ephemeral_path: Path | None = None

    try:
        if from_url is not None:
            return _handle_ephemeral(
                from_url=from_url,
                bundle_name=bundle_spec,
                target_dir=target_dir,
                scope=scope,
                subdirectory_filter=subdirectory_filter,
                dot_selection=dot_selection,
                manifest=manifest,
                manifest_path=manifest_path,
            )

        # Resolve bundle from registered registries
        try:
            resolved = resolve_bundle(bundle_spec, registry_index)
        except BundleNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        # Handle versioned install
        if version is not None:
            registry_path = Path(resolved.path).parent
            try:
                checkout_version(registry_path, version)
            except GitError:
                available = list_versions(registry_path)
                if available:
                    print(
                        f"Error: version '{version}' not found. "
                        f"Available: {', '.join(available)}",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"Error: version '{version}' not found "
                        f"and no versions available.",
                        file=sys.stderr,
                    )
                return 1

        # Check dot notation item exists
        if dot_selection is not None:
            item_path = (
                resolved.path / dot_selection.subdirectory / dot_selection.item_name
            )
            if not item_path.exists():
                print(
                    f"Error: item '{dot_selection.item_name}' "
                    f"not found in "
                    f"{dot_selection.subdirectory}/",
                    file=sys.stderr,
                )
                return 1

        try:
            results = install_bundle(
                bundle=resolved,
                target_dir=target_dir,
                scope=scope,
                subdirectory_filter=subdirectory_filter,
                dot_selection=dot_selection,
                manifest=manifest,
                source_label=resolved.registry_name,
                version=version,
            )
        except SystemExit:
            return 1

        if results:
            print(
                format_diff_summary(results),
                file=sys.stderr,
            )

        save_manifest(manifest, manifest_path)
        return 0

    finally:
        if ephemeral_path is not None:
            shutil.rmtree(ephemeral_path, ignore_errors=True)
            unregister_temp_dir(ephemeral_path)


def _handle_display(
    registry_index: RegistryIndex,
    manifest: Manifest,
) -> str | None:
    """Launch interactive selector and return chosen bundle name."""
    all_bundles = []
    for entry in registry_index.registries:
        registry_path = Path(entry.local_path)
        bundles = scan_registry(registry_path)
        for bundle in bundles:
            bundle.registry_name = entry.name
        all_bundles.extend(bundles)

    installed_names = {e.bundle_name for e in manifest.entries}
    result = interactive_select(all_bundles, installed_names)
    if result is None:
        return None
    return result[0] if result else None


def _handle_ephemeral(
    *,
    from_url: str,
    bundle_name: str,
    target_dir: Path,
    scope: str,
    subdirectory_filter: set[str] | None,
    dot_selection: DotSelection | None,
    manifest: Manifest,
    manifest_path: Path,
) -> int:
    """Handle --from ephemeral registry flow."""
    ephemeral_path: Path | None = None
    try:
        ephemeral_path = clone_ephemeral(from_url)

        # Build a temporary registry index for the ephemeral clone
        temp_idx = RegistryIndex(
            registries=[
                RegistryEntry(
                    name=from_url,
                    url=from_url,
                    local_path=str(ephemeral_path),
                    is_default=False,
                )
            ]
        )

        try:
            resolved = resolve_bundle(bundle_name, temp_idx)
        except BundleNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        # Check dot notation item exists
        if dot_selection is not None:
            item_path = (
                resolved.path / dot_selection.subdirectory / dot_selection.item_name
            )
            if not item_path.exists():
                print(
                    f"Error: item '{dot_selection.item_name}' "
                    f"not found in "
                    f"{dot_selection.subdirectory}/",
                    file=sys.stderr,
                )
                return 1

        try:
            results = install_bundle(
                bundle=resolved,
                target_dir=target_dir,
                scope=scope,
                subdirectory_filter=subdirectory_filter,
                dot_selection=dot_selection,
                manifest=manifest,
                source_label=from_url,
            )
        except SystemExit:
            return 1

        if results:
            print(
                format_diff_summary(results),
                file=sys.stderr,
            )

        save_manifest(manifest, manifest_path)
        return 0

    finally:
        if ephemeral_path is not None:
            shutil.rmtree(ephemeral_path, ignore_errors=True)
            unregister_temp_dir(ephemeral_path)
