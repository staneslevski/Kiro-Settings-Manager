"""Interactive bundle selector for ksm.

Provides terminal-based interactive selection for adding and
removing bundles, using raw terminal mode for key input.
"""

import sys
import tty
import termios
from typing import Optional

from ksm.manifest import ManifestEntry
from ksm.scanner import BundleInfo


def clamp_index(index: int, count: int) -> int:
    """Clamp an index to valid range [0, count-1]."""
    return max(0, min(index, count - 1))


def render_add_selector(
    bundles: list[BundleInfo],
    installed_names: set[str],
    selected: int,
) -> list[str]:
    """Render the add-bundle selector lines.

    Bundles are sorted alphabetically (case-insensitive).
    The selected line gets a ``>`` prefix; installed bundles
    get an ``[installed]`` label. Names are padded to align
    columns.
    """
    sorted_bundles = sorted(bundles, key=lambda b: b.name.lower())
    max_name = max((len(b.name) for b in sorted_bundles), default=0)
    lines: list[str] = []
    for i, bundle in enumerate(sorted_bundles):
        prefix = ">" if i == selected else " "
        padded = bundle.name.ljust(max_name)
        label = " [installed]" if bundle.name in installed_names else ""
        lines.append(f"{prefix} {padded}{label}")
    return lines


def render_removal_selector(
    entries: list[ManifestEntry],
    selected: int,
) -> list[str]:
    """Render the removal selector lines.

    Entries are sorted alphabetically by bundle name
    (case-insensitive). Each line shows the scope label.
    Names are padded to align columns.
    """
    sorted_entries = sorted(entries, key=lambda e: e.bundle_name.lower())
    max_name = max((len(e.bundle_name) for e in sorted_entries), default=0)
    lines: list[str] = []
    for i, entry in enumerate(sorted_entries):
        prefix = ">" if i == selected else " "
        padded = entry.bundle_name.ljust(max_name)
        lines.append(f"{prefix} {padded} [{entry.scope}]")
    return lines


def process_key(key_bytes: bytes, current_index: int, count: int) -> tuple[str, int]:
    """Process a keypress and return (action, new_index).

    Actions: ``"select"``, ``"quit"``, ``"navigate"``, ``"noop"``.
    """
    if key_bytes == b"\r" or key_bytes == b"\n":
        return ("select", current_index)
    if key_bytes == b"q" or key_bytes == b"\x1b":
        return ("quit", current_index)
    if key_bytes == b"\x1b[A":  # Up arrow
        return ("navigate", clamp_index(current_index - 1, count))
    if key_bytes == b"\x1b[B":  # Down arrow
        return ("navigate", clamp_index(current_index + 1, count))
    return ("noop", current_index)


def _read_key() -> bytes:
    """Read a single keypress from stdin in raw mode."""
    ch = sys.stdin.buffer.read(1)
    if ch == b"\x1b":
        # Could be an escape sequence
        extra = sys.stdin.buffer.read(2)
        return ch + extra
    return ch


def interactive_select(
    bundles: list[BundleInfo],
    installed_names: set[str],
) -> Optional[str]:
    """Show interactive add-bundle selector.

    Returns the selected bundle name, or ``None`` if the user
    quits with ``q`` or Escape.
    """
    if not bundles:
        return None

    sorted_bundles = sorted(bundles, key=lambda b: b.name.lower())
    names = [b.name for b in sorted_bundles]
    selected = 0

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            lines = render_add_selector(bundles, installed_names, selected)
            output = "\r\n".join(lines) + "\r\n"
            sys.stdout.write("\033[?25l\033[H" + output + "\033[J\033[?25h")
            sys.stdout.flush()

            key = _read_key()
            action, selected = process_key(key, selected, len(names))
            if action == "select":
                return names[selected]
            if action == "quit":
                return None
    finally:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def interactive_removal_select(
    entries: list[ManifestEntry],
) -> Optional[ManifestEntry]:
    """Show interactive removal selector.

    Returns the selected ManifestEntry, or ``None`` if the user
    quits with ``q`` or Escape.
    """
    if not entries:
        return None

    sorted_entries = sorted(entries, key=lambda e: e.bundle_name.lower())
    selected = 0

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            lines = render_removal_selector(entries, selected)
            output = "\r\n".join(lines) + "\r\n"
            sys.stdout.write("\033[?25l\033[H" + output + "\033[J\033[?25h")
            sys.stdout.flush()

            key = _read_key()
            action, selected = process_key(key, selected, len(sorted_entries))
            if action == "select":
                return sorted_entries[selected]
            if action == "quit":
                return None
    finally:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
