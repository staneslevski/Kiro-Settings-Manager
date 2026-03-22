"""Low-level file copying utilities for ksm.

Provides byte-for-byte file copying with skip-if-identical
optimisation and directory structure preservation.
"""

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TextIO

from ksm.color import dim, green, muted, success, warning_style, yellow


class CopyStatus(Enum):
    """Status of a single file copy operation."""

    NEW = "new"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


@dataclass
class CopyResult:
    """Result of copying a single file."""

    path: Path
    status: CopyStatus


def files_identical(a: Path, b: Path) -> bool:
    """Compare two files byte-for-byte.

    Returns True if both files exist and have identical content.
    """
    if not a.exists() or not b.exists():
        return False
    if a.stat().st_size != b.stat().st_size:
        return False
    return a.read_bytes() == b.read_bytes()


def copy_file(src: Path, dst: Path, skip_identical: bool = True) -> CopyResult:
    """Copy a single file from src to dst.

    Returns a CopyResult with the destination path and status:
    - NEW: file did not exist at dst
    - UPDATED: file existed but had different content
    - UNCHANGED: file existed with identical content (skipped)

    Creates parent directories of dst if they don't exist.
    """
    if skip_identical and dst.exists() and files_identical(src, dst):
        return CopyResult(path=dst, status=CopyStatus.UNCHANGED)

    existed = dst.exists()
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    status = CopyStatus.UPDATED if existed else CopyStatus.NEW
    return CopyResult(path=dst, status=status)


def copy_tree(src: Path, dst: Path, skip_identical: bool = True) -> list[CopyResult]:
    """Recursively copy src directory to dst.

    Returns list of CopyResult for every file encountered,
    including unchanged files.
    """
    results: list[CopyResult] = []

    for src_file in sorted(src.rglob("*")):
        if not src_file.is_file():
            continue

        rel = src_file.relative_to(src)
        dst_file = dst / rel

        result = copy_file(src_file, dst_file, skip_identical=skip_identical)
        results.append(result)

    return results


# Status symbols for file-level diff output (Req 22)
_STATUS_SYMBOLS: dict[CopyStatus, str] = {
    CopyStatus.NEW: "+",
    CopyStatus.UPDATED: "~",
    CopyStatus.UNCHANGED: "=",
}


_STATUS_COLORS: dict[CopyStatus, Callable[..., str]] = {
    CopyStatus.NEW: success,
    CopyStatus.UPDATED: warning_style,
    CopyStatus.UNCHANGED: muted,
}


def format_diff_summary(
    results: list[CopyResult],
    base_path: Path | None = None,
    stream: TextIO | None = None,
) -> str:
    """Format CopyResult list as file-level diff summary.

    Uses semantic colors and symbol constants:
      + steering/code-review.md (new)      ← success + muted
      ~ skills/refactor/SKILL.md (updated) ← warning_style + muted
      = hooks/pre-commit.json (unchanged)  ← muted + muted

    When base_path is provided, displays paths relative to it.
    """
    lines: list[str] = []
    for r in results:
        sym = _STATUS_SYMBOLS[r.status]
        color_fn = _STATUS_COLORS[r.status]
        colored_sym = color_fn(sym, stream=stream)
        display_path = r.path
        if base_path is not None:
            try:
                display_path = r.path.relative_to(base_path)
            except ValueError:
                pass
        colored_label = muted(f"({r.status.value})", stream=stream)
        lines.append(f"  {colored_sym} {display_path} {colored_label}")
    return "\n".join(lines)
    return "\n".join(lines)
