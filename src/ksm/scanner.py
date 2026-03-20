"""Bundle scanner for ksm.

Scans a registry directory for valid bundles — directories that
contain at least one recognised subdirectory (skills/, steering/,
hooks/, agents/).
"""

from dataclasses import dataclass
from pathlib import Path

RECOGNISED_SUBDIRS: frozenset[str] = frozenset(
    {"skills", "steering", "hooks", "agents"}
)


@dataclass
class BundleInfo:
    """Metadata about a discovered bundle."""

    name: str
    path: Path
    subdirectories: list[str]
    registry_name: str = ""


def scan_registry(
    registry_path: Path,
    registry_name: str = "",
) -> list[BundleInfo]:
    """Return all valid bundles found in a registry directory.

    A valid bundle is a top-level subdirectory of registry_path that
    contains at least one recognised subdirectory.

    Args:
        registry_path: Path to the registry directory.
        registry_name: Optional name to populate on each BundleInfo.
    """
    bundles: list[BundleInfo] = []

    if not registry_path.is_dir():
        return bundles

    for entry in sorted(registry_path.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue

        recognised = [
            sd.name
            for sd in sorted(entry.iterdir())
            if sd.is_dir() and sd.name in RECOGNISED_SUBDIRS
        ]

        if recognised:
            bundles.append(
                BundleInfo(
                    name=entry.name,
                    path=entry,
                    subdirectories=recognised,
                    registry_name=registry_name,
                )
            )

    return bundles
