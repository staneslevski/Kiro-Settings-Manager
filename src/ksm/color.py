"""Color output utilities for ksm.

Provides ANSI color wrapping functions that respect NO_COLOR,
TERM=dumb, and non-TTY streams. Includes semantic color functions,
terminal capability detection, Unicode symbol system, and column
alignment utilities.

Requirements: 10.1, 10.2, 10.3, 10.5, 10.6, 10.7
"""

import locale
import os
import re
import sys
from collections.abc import Sequence
from typing import TextIO

# ---------------------------------------------------------------------------
# Terminal capability detection
# ---------------------------------------------------------------------------


def _color_level(stream: TextIO | None = None) -> int:
    """Determine color support level.

    Priority order:
    1. NO_COLOR set → 0
    2. TERM=dumb → 0
    3. Non-TTY stream → 0
    4. COLORTERM=truecolor|24bit → 4
    5. TERM contains '256color' → 3
    6. Default TTY → 2
    """
    if os.environ.get("NO_COLOR") is not None:
        return 0
    if os.environ.get("TERM") == "dumb":
        return 0
    target = stream if stream is not None else sys.stdout
    if not hasattr(target, "isatty") or not target.isatty():
        return 0
    colorterm = os.environ.get("COLORTERM", "").lower()
    if colorterm in ("truecolor", "24bit"):
        return 4
    term = os.environ.get("TERM", "")
    if "256color" in term:
        return 3
    return 2


def _color_enabled(stream: TextIO | None = None) -> bool:
    """Check if color output is enabled for the given stream.

    Color is disabled when:
    - NO_COLOR env var is set (any value)
    - TERM=dumb
    - Stream is not a TTY
    """
    return _color_level(stream) > 0


def _supports_unicode() -> bool:
    """Check if terminal likely supports Unicode.

    Returns False when TERM=dumb or preferred encoding is not UTF-8.
    """
    if os.environ.get("TERM") == "dumb":
        return False
    try:
        encoding = locale.getpreferredencoding(False)
    except Exception:
        return False
    return encoding.lower().replace("-", "") == "utf8"


# ---------------------------------------------------------------------------
# Symbol constants
# ---------------------------------------------------------------------------

if _supports_unicode():
    SYM_CHECK = "✓"
    SYM_CROSS = "✗"
    SYM_ARROW = "→"
    SYM_DOT = "·"
else:
    SYM_CHECK = "*"
    SYM_CROSS = "x"
    SYM_ARROW = "->"
    SYM_DOT = "-"

# Fixed symbols (no Unicode detection needed)
SYM_NEW = "+"
SYM_UPDATED = "~"
SYM_UNCHANGED = "="


# ---------------------------------------------------------------------------
# Core wrapping and style functions
# ---------------------------------------------------------------------------


def _wrap(text: str, code: str, stream: TextIO | None = None) -> str:
    """Wrap text with ANSI escape code if color is enabled.

    On 8-color terminals (level 1), downgrades bright codes (90-97)
    to standard codes (30-37).
    """
    level = _color_level(stream)
    if level == 0:
        return text
    if level == 1:
        # Downgrade bright variants in compound codes
        parts = code.split(";")
        parts = [
            str(int(p) - 60) if p.isdigit() and 90 <= int(p) <= 97 else p for p in parts
        ]
        code = ";".join(parts)
    return f"\033[{code}m{text}\033[0m"


def style(text: str, *codes: str, stream: TextIO | None = None) -> str:
    """Apply multiple ANSI codes as a single escape sequence.

    Example: style("hello", "1", "96") → bold bright cyan.
    Joins codes with ';' into one \\033[...m sequence.
    Returns plain text when color level is 0.
    """
    return _wrap(text, ";".join(codes), stream)


# ---------------------------------------------------------------------------
# Legacy color functions (backward-compatible)
# ---------------------------------------------------------------------------


def green(text: str, stream: TextIO | None = None) -> str:
    """Green text."""
    return _wrap(text, "32", stream)


def red(text: str, stream: TextIO | None = None) -> str:
    """Red text."""
    return _wrap(text, "31", stream)


def yellow(text: str, stream: TextIO | None = None) -> str:
    """Yellow text."""
    return _wrap(text, "33", stream)


def dim(text: str, stream: TextIO | None = None) -> str:
    """Dim text."""
    return _wrap(text, "2", stream)


def bold(text: str, stream: TextIO | None = None) -> str:
    """Bold text."""
    return _wrap(text, "1", stream)


# ---------------------------------------------------------------------------
# Semantic color functions
# ---------------------------------------------------------------------------


def success(text: str, stream: TextIO | None = None) -> str:
    """Bright green (92) — success states, checkmarks."""
    return _wrap(text, "92", stream)


def error_style(text: str, stream: TextIO | None = None) -> str:
    """Bright red (91) — error prefixes, failures."""
    return _wrap(text, "91", stream)


def warning_style(text: str, stream: TextIO | None = None) -> str:
    """Bright yellow (93) — warning/deprecation prefixes."""
    return _wrap(text, "93", stream)


def accent(text: str, stream: TextIO | None = None) -> str:
    """Bright cyan (96) — bundle names, highlights."""
    return _wrap(text, "96", stream)


def info(text: str, stream: TextIO | None = None) -> str:
    """Bright blue (94) — informational labels, scope badges."""
    return _wrap(text, "94", stream)


def muted(text: str, stream: TextIO | None = None) -> str:
    """Dim (2) — secondary information. Alias for dim()."""
    return _wrap(text, "2", stream)


def subtle(text: str, stream: TextIO | None = None) -> str:
    """Dim italic (2;3) — hints, suggestions."""
    return _wrap(text, "2;3", stream)


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences for width calculation."""
    return _ANSI_RE.sub("", text)


def _align_columns(
    rows: Sequence[tuple[str, ...]],
    gap: int = 2,
) -> list[str]:
    """Align columns with consistent padding.

    Uses _strip_ansi() for accurate width calculation.
    Pads all columns except the last.
    Returns empty list for empty input.
    """
    if not rows:
        return []
    max_cols = max(len(r) for r in rows)
    widths = [0] * max_cols
    for row in rows:
        for i, cell in enumerate(row):
            w = len(_strip_ansi(cell))
            if w > widths[i]:
                widths[i] = w
    lines: list[str] = []
    for row in rows:
        parts: list[str] = []
        for i, cell in enumerate(row):
            if i < len(row) - 1:
                pad = widths[i] - len(_strip_ansi(cell)) + gap
                parts.append(cell + " " * pad)
            else:
                parts.append(cell)
        lines.append("".join(parts))
    return lines
