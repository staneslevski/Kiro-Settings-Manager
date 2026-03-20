"""Legacy add-registry command for ksm.

Handles ``ksm add-registry <git_url>`` — deprecated thin wrapper
that prints a deprecation warning and delegates to
``registry_add.run_registry_add``.

Requirements: 8.1, 8.2, 8.3, 8.4
"""

import argparse
import sys
from pathlib import Path

from ksm.errors import format_deprecation
from ksm.registry import RegistryIndex


def run_add_registry(
    args: argparse.Namespace,
    *,
    registry_index: RegistryIndex,
    registry_index_path: Path,
    cache_dir: Path,
) -> int:
    """Legacy add-registry command. Delegates to registry_add."""
    print(
        format_deprecation(
            "ksm add-registry",
            "ksm registry add",
            "v0.2.0",
            "v1.0.0",
        ),
        file=sys.stderr,
    )
    from ksm.commands.registry_add import run_registry_add

    return run_registry_add(
        args,
        registry_index=registry_index,
        registry_index_path=registry_index_path,
        cache_dir=cache_dir,
    )
