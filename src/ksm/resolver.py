"""Bundle resolver for ksm.

Finds a bundle by name across all registered registries.
"""

from dataclasses import dataclass, field
from pathlib import Path

from ksm.errors import BundleNotFoundError
from ksm.registry import RegistryIndex
from ksm.scanner import scan_registry


@dataclass
class ResolvedBundle:
    """A bundle resolved to a specific registry location."""

    name: str
    path: Path
    registry_name: str
    subdirectories: list[str]


@dataclass
class ResolvedBundleResult:
    """Result of resolving a bundle name across registries."""

    matches: list[ResolvedBundle] = field(default_factory=list)
    searched: list[str] = field(default_factory=list)


def resolve_bundle(
    bundle_name: str,
    registry_index: RegistryIndex,
) -> ResolvedBundleResult:
    """Search all registries for a bundle by name.

    Returns ALL matches (not just the first). The caller is
    responsible for handling ambiguity (multiple matches) or
    not-found (zero matches).
    """
    result = ResolvedBundleResult()
    for entry in registry_index.registries:
        result.searched.append(entry.name)
        registry_path = Path(entry.local_path)
        bundles = scan_registry(registry_path)
        for bundle in bundles:
            if bundle.name == bundle_name:
                result.matches.append(
                    ResolvedBundle(
                        name=bundle.name,
                        path=bundle.path,
                        registry_name=entry.name,
                        subdirectories=bundle.subdirectories,
                    )
                )
    return result


def parse_qualified_name(
    spec: str,
) -> tuple[str | None, str]:
    """Parse 'registry/bundle' or plain 'bundle'.

    Returns (registry_name, bundle_name). registry_name is
    None for unqualified names.
    """
    if "/" in spec and not spec.startswith("/"):
        parts = spec.split("/", 1)
        return parts[0], parts[1]
    return None, spec


def resolve_qualified_bundle(
    qualified_name: str,
    registry_index: RegistryIndex,
) -> ResolvedBundle:
    """Resolve a qualified bundle name (registry/bundle).

    Raises BundleNotFoundError if the registry or bundle is
    not found.
    """
    reg_name, bundle_name = parse_qualified_name(qualified_name)

    if reg_name is None:
        raise ValueError(
            f"Expected qualified name (registry/bundle)," f" got: {qualified_name}"
        )

    # Find the registry entry
    entry = None
    for e in registry_index.registries:
        if e.name == reg_name:
            entry = e
            break

    if entry is None:
        available = [e.name for e in registry_index.registries]
        raise BundleNotFoundError(
            f"Registry '{reg_name}' not found." f" Available: {', '.join(available)}",
            searched_registries=available,
        )

    # Scan the registry for the bundle
    registry_path = Path(entry.local_path)
    bundles = scan_registry(registry_path)
    for bundle in bundles:
        if bundle.name == bundle_name:
            return ResolvedBundle(
                name=bundle.name,
                path=bundle.path,
                registry_name=entry.name,
                subdirectories=bundle.subdirectories,
            )

    raise BundleNotFoundError(
        bundle_name,
        searched_registries=[entry.name],
    )
