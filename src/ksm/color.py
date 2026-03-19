"""Color output utilities for ksm.

Provides ANSI color wrapping functions that respect NO_COLOR,
TERM=dumb, and non-TTY streams.

Requirements: 10.1, 10.2, 10.3, 10.5, 10.6, 10.7
"""

import os
import sys
from typing import TextIO


def _color_enabled(stream: TextIO | None = None) -> bool:
    """Check if color output is enabled for the given stream.

    Color is disabled when:
    - NO_COLOR env var is set (any value)
    - TERM=dumb
    - Stream is not a TTY
    """
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    target = stream if stream is not None else sys.stdout
    if not hasattr(target, "isatty"):
        return False
    return target.isatty()


def _wrap(text: str, code: str, stream: TextIO | None = None) -> str:
    """Wrap text with ANSI escape code if color is enabled."""
    if not _color_enabled(stream):
        return text
    return f"\033[{code}m{text}\033[0m"


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
