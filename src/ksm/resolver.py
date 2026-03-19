"""Bundle resolver for ksm.

Finds a bundle by name across all registered registries.
"""

from dataclasses import dataclass
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


def resolve_bundle(
    bundle_name: str,
    registry_index: RegistryIndex,
) -> ResolvedBundle:
    """Search all registries for a bundle by name.

    Returns the first match found. Raises BundleNotFoundError if
    the bundle is not found in any registered registry.
    """
    searched: list[str] = []
    for entry in registry_index.registries:
        searched.append(entry.name)
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
    raise BundleNotFoundError(bundle_name, searched_registries=searched)
