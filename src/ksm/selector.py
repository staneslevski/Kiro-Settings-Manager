"""Interactive bundle selector for ksm.

Provides terminal-based interactive selection for adding and
removing bundles. Uses Textual TUI when available, falling
back to a numbered-list prompt otherwise.

All UI rendering goes to stderr to keep stdout clean for
piped data (Req 25). Falls back to a numbered-list prompt
when Textual is unavailable, stdin is not a TTY, or
TERM=dumb (Reqs 7, 26, 29).
"""

import os
import sys

try:
    import tty
    import termios

    _HAS_TERMIOS = True
except ImportError:
    tty = None  # type: ignore[assignment]
    termios = None  # type: ignore[assignment]
    _HAS_TERMIOS = False

from ksm.color import bold, dim
from ksm.manifest import ManifestEntry
from ksm.scanner import BundleInfo


def _can_run_textual() -> bool:
    """Check if Textual TUI can be used.

    Returns True only when all conditions are met:
    - stdin is a TTY
    - TERM is not ``dumb``
    - Textual is importable

    Returns False otherwise, signalling the caller to use
    the numbered-list fallback. (Reqs 7.1, 7.2, 7.3, 8.5, 8.6)
    """
    if not sys.stdin.isatty():
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    try:
        import textual  # noqa: F401

        return True
    except ImportError:
        return False


# Keep as alias for backward compatibility during transition
_use_raw_mode = _can_run_textual


def _numbered_list_select(
    items: list[tuple[str, str]],
    header: str,
) -> int | None:
    """Cross-platform fallback: numbered list rendered to stderr.

    Displays items with 1-based indices, reads a number from
    stdin. Returns the 0-based index of the selected item, or
    None if the user enters ``q`` or EOF. Re-prompts on invalid
    input. (Reqs 26, 29)
    """
    sys.stderr.write(f"\n{header}\n\n")
    for i, (name, label) in enumerate(items, 1):
        line = f"  {i}. {name}"
        if label:
            line += f"  {label}"
        sys.stderr.write(line + "\n")
    sys.stderr.write("\n")
    sys.stderr.flush()

    while True:
        try:
            answer = input(f"Enter number [1-{len(items)}] or q: ")
        except EOFError:
            return None
        answer = answer.strip()
        if answer == "q":
            return None
        try:
            num = int(answer)
        except ValueError:
            sys.stderr.write(f"Invalid input. Enter 1-{len(items)} or q.\n")
            sys.stderr.flush()
            continue
        if 1 <= num <= len(items):
            return num - 1
        sys.stderr.write(f"Invalid input. Enter 1-{len(items)} or q.\n")
        sys.stderr.flush()


def clamp_index(index: int, count: int) -> int:
    """Clamp an index to valid range [0, count-1]."""
    return max(0, min(index, count - 1))


_ADD_HEADER = "Select a bundle to install"
_ADD_INSTRUCTIONS = "↑/↓ navigate, Enter select, q quit"
_RM_HEADER = "Select a bundle to remove"
_RM_INSTRUCTIONS = "↑/↓ navigate, Enter select, q quit"


def render_add_selector(
    bundles: list[BundleInfo],
    installed_names: set[str],
    selected: int,
    filter_text: str = "",
    multi_selected: set[int] | None = None,
) -> list[str]:
    """Render the add-bundle selector lines.

    Returns a header line, an instruction line, a blank
    separator, then the bundle list. Bundles are sorted
    alphabetically (case-insensitive) and optionally filtered
    by ``filter_text`` (case-insensitive substring match).

    The selected line gets a ``>`` prefix; installed bundles
    get an ``[installed]`` label. When ``multi_selected`` is
    provided, each line shows ``[✓]`` or ``[ ]`` indicators.
    Names are padded to align columns.
    (Reqs 3, 14, 15)
    """
    sorted_bundles = sorted(bundles, key=lambda b: b.name.lower())
    if filter_text:
        ft = filter_text.lower()
        sorted_bundles = [b for b in sorted_bundles if ft in b.name.lower()]

    # Detect ambiguous names (Req 4.1, 4.2)
    name_counts: dict[str, int] = {}
    for b in sorted_bundles:
        name_counts[b.name] = name_counts.get(b.name, 0) + 1
    ambiguous = {n for n, c in name_counts.items() if c > 1}

    # Build display names
    display_names: list[str] = []
    for b in sorted_bundles:
        if b.name in ambiguous and b.registry_name:
            display_names.append(f"{b.registry_name}/{b.name}")
        else:
            display_names.append(b.name)

    # Re-sort by display name
    paired = list(zip(display_names, sorted_bundles))
    paired.sort(key=lambda p: p[0].lower())
    display_names = [p[0] for p in paired]
    sorted_bundles = [p[1] for p in paired]

    max_name = max((len(dn) for dn in display_names), default=0)
    lines: list[str] = [
        bold(_ADD_HEADER, stream=sys.stderr),
        dim(_ADD_INSTRUCTIONS, stream=sys.stderr),
        "",
    ]
    if filter_text:
        lines[2] = dim(f"Filter: {filter_text}", stream=sys.stderr)
    for i, bundle in enumerate(sorted_bundles):
        prefix = ">" if i == selected else " "
        check = ""
        if multi_selected is not None:
            check = "[✓] " if i in multi_selected else "[ ] "
        padded = display_names[i].ljust(max_name)
        if i == selected:
            padded = bold(padded, stream=sys.stderr)
        label = (
            dim(" [installed]", stream=sys.stderr)
            if bundle.name in installed_names
            else ""
        )
        lines.append(f"{prefix} {check}{padded}{label}")
    return lines


def render_removal_selector(
    entries: list[ManifestEntry],
    selected: int,
    filter_text: str = "",
    multi_selected: set[int] | None = None,
) -> list[str]:
    """Render the removal selector lines.

    Returns a header line, an instruction line, a blank
    separator, then the entry list. Entries are sorted
    alphabetically by bundle name (case-insensitive) and
    optionally filtered by ``filter_text`` (case-insensitive
    substring match).

    When ``multi_selected`` is provided, each line shows
    ``[✓]`` or ``[ ]`` indicators. Names are padded to align
    columns. (Req 3.1, 3.2, 3.3, 14, 15)
    """
    sorted_entries = sorted(entries, key=lambda e: e.bundle_name.lower())
    if filter_text:
        ft = filter_text.lower()
        sorted_entries = [e for e in sorted_entries if ft in e.bundle_name.lower()]
    max_name = max((len(e.bundle_name) for e in sorted_entries), default=0)
    lines: list[str] = [
        bold(_RM_HEADER, stream=sys.stderr),
        dim(_RM_INSTRUCTIONS, stream=sys.stderr),
        "",
    ]
    if filter_text:
        lines[2] = dim(f"Filter: {filter_text}", stream=sys.stderr)
    for i, entry in enumerate(sorted_entries):
        prefix = ">" if i == selected else " "
        check = ""
        if multi_selected is not None:
            check = "[✓] " if i in multi_selected else "[ ] "
        padded = entry.bundle_name.ljust(max_name)
        scope_label = dim(f"[{entry.scope}]", stream=sys.stderr)
        lines.append(f"{prefix} {check}{padded} {scope_label}")
    return lines


def process_key(key_bytes: bytes, current_index: int, count: int) -> tuple[str, int]:
    """Process a keypress and return (action, new_index).

    Actions: ``"select"``, ``"quit"``, ``"navigate"``,
    ``"toggle"``, ``"filter_char"``, ``"backspace"``,
    ``"noop"``.
    """
    if key_bytes == b"\r" or key_bytes == b"\n":
        return ("select", current_index)
    if key_bytes == b"\x1b[A":  # Up arrow
        return (
            "navigate",
            clamp_index(current_index - 1, count),
        )
    if key_bytes == b"\x1b[B":  # Down arrow
        return (
            "navigate",
            clamp_index(current_index + 1, count),
        )
    if key_bytes == b" ":
        return ("toggle", current_index)
    if key_bytes == b"\x7f":
        return ("backspace", current_index)
    if key_bytes == b"\x1b":
        return ("quit", current_index)
    if key_bytes == b"q":
        return ("quit", current_index)
    # Single printable ASCII byte → filter character
    if len(key_bytes) == 1 and 32 < key_bytes[0] < 127:
        return ("filter_char", current_index)
    return ("noop", current_index)


def _read_key() -> bytes:
    """Read a single keypress from stdin in raw mode."""
    ch = sys.stdin.buffer.read(1)
    if ch == b"\x1b":
        # Could be an escape sequence
        extra = sys.stdin.buffer.read(2)
        return ch + extra
    return ch


_SCOPE_OPTIONS = [
    ("local", "Local (.kiro/)"),
    ("global", "Global (~/.kiro/)"),
]
_SCOPE_HEADER = "Select installation scope:"
_SCOPE_INSTRUCTIONS = "↑/↓ navigate, Enter select, q quit"


def scope_select() -> str | None:
    """Interactive scope selection.

    Returns ``"local"``, ``"global"``, or ``None`` (abort).

    Raw mode: inline arrow-key navigation (no alternate
    screen buffer). Fallback: numbered list prompt.
    Non-TTY stdin in fallback: returns ``None`` (caller
    defaults to ``"local"``).

    (Reqs 11, 12, 13, 16)
    """
    if not _can_run_textual():
        # Numbered-list fallback
        if not sys.stdin.isatty():
            return None
        sys.stderr.write(f"\n{_SCOPE_HEADER}\n\n")
        for i, (_key, label) in enumerate(_SCOPE_OPTIONS, 1):
            sys.stderr.write(f"  {i}. {label}\n")
        sys.stderr.write("\n")
        sys.stderr.flush()

        while True:
            try:
                answer = input("Enter number [1-2] or q: ")
            except EOFError:
                return None
            answer = answer.strip()
            if answer == "q":
                return None
            if answer == "" or answer == "1":
                return "local"
            if answer == "2":
                return "global"
            sys.stderr.write("Invalid input. Enter 1-2 or q.\n")
            sys.stderr.flush()

    # Raw mode path — inline rendering
    selected = 0
    count = len(_SCOPE_OPTIONS)
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            lines: list[str] = [
                bold(_SCOPE_HEADER, stream=sys.stderr),
                dim(
                    _SCOPE_INSTRUCTIONS,
                    stream=sys.stderr,
                ),
                "",
            ]
            for i, (_key, label) in enumerate(_SCOPE_OPTIONS):
                prefix = ">" if i == selected else " "
                text = f"{prefix} {label}"
                if i == selected:
                    text = bold(text, stream=sys.stderr)
                lines.append(text)

            output = "\r\n".join(lines) + "\r\n"
            sys.stderr.write(output)
            sys.stderr.flush()

            key = _read_key()
            action, selected = process_key(key, selected, count)
            if action == "select":
                return _SCOPE_OPTIONS[selected][0]
            if action == "quit":
                return None
    except KeyboardInterrupt:
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def interactive_select(
    bundles: list[BundleInfo],
    installed_names: set[str],
) -> list[str] | None:
    """Show interactive add-bundle selector.

    Returns a list of selected bundle names, or ``None`` if
    the user quits with ``q`` or Escape. When multi-select
    is used (Space to toggle), Enter confirms all toggled
    items. Without any toggles, Enter returns a single-item
    list.

    All UI rendering goes to stderr (Req 25).
    Uses alternate screen buffer in raw mode (Req 30).
    Falls back to numbered-list prompt when raw mode
    unavailable (Reqs 26, 29).
    """
    if not bundles:
        return None

    sorted_bundles = sorted(bundles, key=lambda b: b.name.lower())
    names = [b.name for b in sorted_bundles]

    if not _can_run_textual():
        items = [
            (
                b.name,
                "[installed]" if b.name in installed_names else "",
            )
            for b in sorted_bundles
        ]
        idx = _numbered_list_select(items, "Select a bundle to install:")
        if idx is None:
            return None
        return [names[idx]]

    selected = 0
    filter_text = ""
    multi_selected: set[int] = set()
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        # Enter alternate screen buffer (Req 30)
        sys.stderr.write("\033[?1049h")
        sys.stderr.flush()
        while True:
            # Compute filtered names for index mapping
            if filter_text:
                ft = filter_text.lower()
                filtered = [n for n in names if ft in n.lower()]
            else:
                filtered = names
            count = len(filtered) if filtered else 1
            selected = clamp_index(selected, count)

            lines = render_add_selector(
                bundles,
                installed_names,
                selected,
                filter_text=filter_text,
                multi_selected=(multi_selected if multi_selected else None),
            )
            output = "\r\n".join(lines) + "\r\n"
            sys.stderr.write("\033[?25l\033[H" + output + "\033[J\033[?25h")
            sys.stderr.flush()

            key = _read_key()
            action, selected = process_key(key, selected, count)
            if action == "select":
                if multi_selected:
                    return [
                        filtered[i] for i in sorted(multi_selected) if i < len(filtered)
                    ]
                if filtered:
                    return [filtered[selected]]
                return None
            if action == "quit":
                return None
            if action == "filter_char":
                filter_text += key.decode("ascii", "ignore")
                selected = 0
                multi_selected = set()
            elif action == "backspace":
                filter_text = filter_text[:-1]
                selected = 0
                multi_selected = set()
            elif action == "toggle":
                if selected in multi_selected:
                    multi_selected.discard(selected)
                else:
                    multi_selected.add(selected)
    finally:
        sys.stderr.write("\033[?25h")
        # Exit alternate screen buffer (Req 30)
        sys.stderr.write("\033[?1049l")
        sys.stderr.flush()
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def interactive_removal_select(
    entries: list[ManifestEntry],
) -> list[ManifestEntry] | None:
    """Show interactive removal selector.

    Returns a list of selected ManifestEntry objects, or
    ``None`` if the user quits with ``q`` or Escape. When
    multi-select is used (Space to toggle), Enter confirms
    all toggled items. Without any toggles, Enter returns a
    single-item list.

    All UI rendering goes to stderr (Req 25).
    Uses alternate screen buffer in raw mode (Req 30).
    Falls back to numbered-list prompt when raw mode
    unavailable (Reqs 26, 29).
    """
    if not entries:
        return None

    sorted_entries = sorted(entries, key=lambda e: e.bundle_name.lower())

    if not _can_run_textual():
        items = [(e.bundle_name, f"[{e.scope}]") for e in sorted_entries]
        idx = _numbered_list_select(items, "Select a bundle to remove:")
        if idx is None:
            return None
        return [sorted_entries[idx]]

    selected = 0
    filter_text = ""
    multi_selected: set[int] = set()
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        # Enter alternate screen buffer (Req 30)
        sys.stderr.write("\033[?1049h")
        sys.stderr.flush()
        while True:
            # Compute filtered entries for index mapping
            if filter_text:
                ft = filter_text.lower()
                filtered = [e for e in sorted_entries if ft in e.bundle_name.lower()]
            else:
                filtered = sorted_entries
            count = len(filtered) if filtered else 1
            selected = clamp_index(selected, count)

            lines = render_removal_selector(
                entries,
                selected,
                filter_text=filter_text,
                multi_selected=(multi_selected if multi_selected else None),
            )
            output = "\r\n".join(lines) + "\r\n"
            sys.stderr.write("\033[?25l\033[H" + output + "\033[J\033[?25h")
            sys.stderr.flush()

            key = _read_key()
            action, selected = process_key(key, selected, count)
            if action == "select":
                if multi_selected:
                    return [
                        filtered[i] for i in sorted(multi_selected) if i < len(filtered)
                    ]
                if filtered:
                    return [filtered[selected]]
                return None
            if action == "quit":
                return None
            if action == "filter_char":
                filter_text += key.decode("ascii", "ignore")
                selected = 0
                multi_selected = set()
            elif action == "backspace":
                filter_text = filter_text[:-1]
                selected = 0
                multi_selected = set()
            elif action == "toggle":
                if selected in multi_selected:
                    multi_selected.discard(selected)
                else:
                    multi_selected.add(selected)
    finally:
        sys.stderr.write("\033[?25h")
        # Exit alternate screen buffer (Req 30)
        sys.stderr.write("\033[?1049l")
        sys.stderr.flush()
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
