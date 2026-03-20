"""Color output utilities for ksm.

Provides ANSI color formatting with automatic TTY detection
and NO_COLOR/TERM=dumb support per https://no-color.org/.
"""

import os
import sys
from typing import TextIO


def _color_enabled_for_stream(stream: TextIO) -> bool:
    """Check if color output should be enabled for a stream.

    Returns False when:
    - NO_COLOR env var is set (any value)
    - TERM=dumb
    - The target stream is not a TTY
    """
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    if not hasattr(stream, "isatty"):
        return False
    return stream.isatty()


def _color_enabled() -> bool:
    """Check if color output should be enabled for stdout."""
    return _color_enabled_for_stream(sys.stdout)


def _color_enabled_stderr() -> bool:
    """Check if color output should be enabled for stderr."""
    return _color_enabled_for_stream(sys.stderr)


def _wrap(code: str, text: str, stream: TextIO | None = None) -> str:
    """Wrap text with ANSI escape code if color is enabled."""
    if stream is not None:
        check = _color_enabled_for_stream(stream)
    else:
        check = _color_enabled()
    if not check:
        return text
    return f"\033[{code}m{text}\033[0m"


def green(text: str, stream: TextIO | None = None) -> str:
    """Format text in green (success)."""
    return _wrap("32", text, stream)


def red(text: str, stream: TextIO | None = None) -> str:
    """Format text in red (error)."""
    return _wrap("31", text, stream)


def yellow(text: str, stream: TextIO | None = None) -> str:
    """Format text in yellow (warning)."""
    return _wrap("33", text, stream)


def dim(text: str, stream: TextIO | None = None) -> str:
    """Format text in dim/gray (secondary info)."""
    return _wrap("2", text, stream)


def bold(text: str, stream: TextIO | None = None) -> str:
    """Format text in bold."""
    return _wrap("1", text, stream)
