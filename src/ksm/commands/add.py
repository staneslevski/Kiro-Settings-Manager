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
from ksm.color import SYM_ARROW, SYM_CHECK, accent, muted, success
from ksm.copier import format_diff_summary
from ksm.errors import (
    GitError,
    InvalidSubdirectoryError,
    format_deprecation,
    format_error,
    format_warning,
)
from ksm.git_ops import (
    checkout_version,
    clone_ephemeral,
    list_versions,
)
from ksm.installer import install_bundle
from ksm.manifest import Manifest, build_installed_info, save_manifest
from ksm.registry import RegistryEntry, RegistryIndex
from ksm.resolver import (
    parse_qualified_name,
    resolve_bundle,
    resolve_qualified_bundle,
)
from ksm.scanner import scan_registry
from ksm.selector import interactive_select, scope_select
from ksm.signal_handler import unregister_temp_dir

VALID_ONLY_VALUES = {"skills", "agents", "steering", "hooks"}


def _build_subdirectory_filter(
    args: argparse.Namespace,
) -> set[str] | None:
    """Build subdirectory filter from --only or deprecated flags.

    Handles comma-separated values, repeated --only flags,
    validation, and deprecated --*-only flag migration.
    """
    only_raw: list[str] | None = getattr(args, "only", None)
    result: set[str] = set()

    if only_raw:
        for item in only_raw:
            for val in item.split(","):
                val = val.strip()
                if val not in VALID_ONLY_VALUES:
                    print(
                        format_error(
                            f"Invalid --only value: '{val}'",
                            "Valid values: " + ", ".join(sorted(VALID_ONLY_VALUES)),
                            "Example: --only skills,hooks",
                            stream=sys.stderr,
                        ),
                        file=sys.stderr,
                    )
                    raise SystemExit(2)
                result.add(val)
        return result

    # Deprecated --*-only flags (Req 12.7)
    deprecated_map = {
        "skills_only": "skills",
        "steering_only": "steering",
        "hooks_only": "hooks",
        "agents_only": "agents",
    }
    for attr, value in deprecated_map.items():
        if getattr(args, attr, False):
            flag = f"--{attr.replace('_', '-')}"
            print(
                format_deprecation(
                    flag,
                    f"--only {value}",
                    "v0.2.0",
                    "v1.0.0",
                    stream=sys.stderr,
                ),
                file=sys.stderr,
            )
            result.add(value)

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

    # Handle --display deprecation (Req 5.7)
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

    # If bundle_spec provided AND -i, ignore -i (Req 5.9)
    if bundle_spec and interactive:
        print(
            format_warning(
                "-i ignored because a bundle" " was specified.",
                "Proceeding with the specified bundle.",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        interactive = False

    _interactive_path = False

    if interactive:
        bundle_name = _handle_display(
            registry_index,
            manifest,
            workspace_path=str(target_local.parent.resolve()),
        )
        if bundle_name is None:
            return 0
        bundle_spec = bundle_name
        _interactive_path = True

    if bundle_spec is None:
        # Auto-launch selector if TTY (Req 9)
        if sys.stdin.isatty():
            bundle_name = _handle_display(
                registry_index,
                manifest,
                workspace_path=str(target_local.parent.resolve()),
            )
            if bundle_name is None:
                return 0
            bundle_spec = bundle_name
            _interactive_path = True
        else:
            print(
                format_error(
                    "No bundle specified.",
                    "Provide a bundle name or use -i" " for interactive mode.",
                    "Example: ksm add <bundle_name>",
                    stream=sys.stderr,
                ),
                file=sys.stderr,
            )
            return 1

    # Parse dot notation
    dot_selection = parse_dot_notation(bundle_spec)
    if dot_selection is not None:
        try:
            validate_dot_selection(dot_selection)
        except InvalidSubdirectoryError as e:
            print(
                format_error(
                    f"Invalid subdirectory: {e}",
                    "Check the dot notation syntax.",
                    "Valid types: skills, agents," " steering, hooks",
                    stream=sys.stderr,
                ),
                file=sys.stderr,
            )
            return 1
        bundle_spec = dot_selection.bundle_name

    # Parse version spec (bundle@version)
    version: str | None = None
    bundle_spec, version = parse_version_spec(bundle_spec)

    # Check mutual exclusion: dot notation + subdirectory filter
    if dot_selection is not None and subdirectory_filter is not None:
        print(
            format_error(
                "Dot notation and --only are mutually" " exclusive.",
                "Use one or the other, not both.",
                "Example: ksm add bundle.skills.item"
                " OR ksm add bundle --only skills",
                stream=sys.stderr,
            ),
            file=sys.stderr,
        )
        return 1

    # Determine scope
    has_flag = getattr(args, "global_", False) or getattr(args, "local", False)
    if _interactive_path and not has_flag:
        # Interactive path: prompt for scope (Req 11.1)
        if sys.stdin.isatty():
            chosen_scope = scope_select()
            if chosen_scope is None:
                return 0
            scope = chosen_scope
        else:
            scope = "local"  # Req 11.7
    else:
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

        # Parse qualified name (Req 10)
        reg_name, bare_name = parse_qualified_name(bundle_spec)

        if reg_name is not None:
            # Qualified: resolve from specific registry
            from ksm.errors import BundleNotFoundError

            try:
                resolved = resolve_qualified_bundle(bundle_spec, registry_index)
            except BundleNotFoundError as exc:
                print(
                    format_error(
                        str(exc),
                        "Check the registry and bundle" " names.",
                        "Run `ksm registry list` to see" " available registries.",
                        stream=sys.stderr,
                    ),
                    file=sys.stderr,
                )
                return 1
        else:
            # Unqualified: resolve across all registries
            result = resolve_bundle(bare_name, registry_index)
            if not result.matches:
                print(
                    format_error(
                        f"Bundle '{bare_name}' not found.",
                        f"Searched {len(result.searched)}"
                        " "
                        f"{'registry' if len(result.searched) == 1 else 'registries'}"
                        f": {', '.join(result.searched)}",
                        "Run `ksm registry list` to see" " available registries.",
                        stream=sys.stderr,
                    ),
                    file=sys.stderr,
                )
                return 1
            if len(result.matches) > 1:
                registries = [m.registry_name for m in result.matches]
                print(
                    format_error(
                        f"Bundle '{bare_name}' found in" " multiple registries.",
                        "Found in:" f" {', '.join(registries)}",
                        "Use qualified name:" " ksm add" f" <registry>/{bare_name}",
                        stream=sys.stderr,
                    ),
                    file=sys.stderr,
                )
                return 1
            resolved = result.matches[0]

        # Handle versioned install
        if version is not None:
            registry_path = Path(resolved.path).parent
            try:
                checkout_version(registry_path, version)
            except GitError:
                available = list_versions(registry_path)
                if available:
                    print(
                        format_error(
                            f"Version '{version}' not" " found.",
                            f"Available:" f" {', '.join(available)}",
                            "Use one of the listed" " versions.",
                            stream=sys.stderr,
                        ),
                        file=sys.stderr,
                    )
                else:
                    print(
                        format_error(
                            f"Version '{version}' not" " found.",
                            "No versions available in" " this registry.",
                            "Omit the @version to" " install the latest.",
                            stream=sys.stderr,
                        ),
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
                    format_error(
                        f"Item '{dot_selection.item_name}'"
                        f" not found in"
                        f" {dot_selection.subdirectory}/.",
                        "Check the item name and" " subdirectory.",
                        "Run `ksm info <bundle>` to see" " available items.",
                        stream=sys.stderr,
                    ),
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
            scope_path = ".kiro/" if scope == "local" else "~/.kiro/"
            check = success(SYM_CHECK, stream=sys.stderr)
            name = accent(bundle_spec, stream=sys.stderr)
            scope_label = muted(f"({scope})", stream=sys.stderr)
            print(
                f"{check} Installed {name} {SYM_ARROW}" f" {scope_path} {scope_label}",
                file=sys.stderr,
            )
            print(
                format_diff_summary(results, stream=sys.stderr),
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
    workspace_path: str,
) -> str | None:
    """Launch interactive selector and return chosen bundle name."""
    all_bundles = []
    for entry in registry_index.registries:
        registry_path = Path(entry.local_path)
        bundles = scan_registry(registry_path, registry_name=entry.name)
        all_bundles.extend(bundles)

    installed_info = build_installed_info(manifest, workspace_path)
    result = interactive_select(all_bundles, installed_info)
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

        result = resolve_bundle(bundle_name, temp_idx)
        if not result.matches:
            print(
                format_error(
                    f"Bundle '{bundle_name}' not found" f" in {from_url}.",
                    "The repository may not contain" " this bundle.",
                    "Check the URL and bundle name.",
                    stream=sys.stderr,
                ),
                file=sys.stderr,
            )
            return 1
        resolved = result.matches[0]

        # Check dot notation item exists
        if dot_selection is not None:
            item_path = (
                resolved.path / dot_selection.subdirectory / dot_selection.item_name
            )
            if not item_path.exists():
                print(
                    format_error(
                        f"Item '{dot_selection.item_name}'"
                        f" not found in"
                        f" {dot_selection.subdirectory}/.",
                        "Check the item name and" " subdirectory.",
                        "Run `ksm info <bundle>` to see" " available items.",
                        stream=sys.stderr,
                    ),
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
            scope_path = ".kiro/" if scope == "local" else "~/.kiro/"
            check = success(SYM_CHECK, stream=sys.stderr)
            name = accent(bundle_name, stream=sys.stderr)
            scope_label = muted(f"({scope})", stream=sys.stderr)
            print(
                f"{check} Installed {name} {SYM_ARROW}" f" {scope_path} {scope_label}",
                file=sys.stderr,
            )
            print(
                format_diff_summary(results, stream=sys.stderr),
                file=sys.stderr,
            )

        save_manifest(manifest, manifest_path)
        return 0

    finally:
        if ephemeral_path is not None:
            shutil.rmtree(ephemeral_path, ignore_errors=True)
            unregister_temp_dir(ephemeral_path)
