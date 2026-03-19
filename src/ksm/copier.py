"""Low-level file copying utilities for ksm.

Provides byte-for-byte file copying with skip-if-identical
optimisation and directory structure preservation.
"""

import shutil
from pathlib import Path


def files_identical(a: Path, b: Path) -> bool:
    """Compare two files byte-for-byte.

    Returns True if both files exist and have identical content.
    """
    if not a.exists() or not b.exists():
        return False
    if a.stat().st_size != b.stat().st_size:
        return False
    return a.read_bytes() == b.read_bytes()


def copy_file(src: Path, dst: Path, skip_identical: bool = True) -> bool:
    """Copy a single file from src to dst.

    Returns True if the copy occurred, False if skipped.
    Creates parent directories of dst if they don't exist.
    """
    if skip_identical and dst.exists() and files_identical(src, dst):
        return False

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def copy_tree(src: Path, dst: Path, skip_identical: bool = True) -> list[Path]:
    """Recursively copy src directory to dst.

    Returns list of destination file paths that were actually copied
    (skipped files are not included).
    """
    copied: list[Path] = []

    for src_file in sorted(src.rglob("*")):
        if not src_file.is_file():
            continue

        rel = src_file.relative_to(src)
        dst_file = dst / rel

        if copy_file(src_file, dst_file, skip_identical=skip_identical):
            copied.append(dst_file)

    return copied
