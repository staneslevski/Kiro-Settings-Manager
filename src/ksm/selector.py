"""Interactive bundle selector for ksm.

Provides terminal-based interactive selection for adding and
removing bundles. Uses Textual TUI when available, falling
back to a numbered-list prompt otherwise.

All UI rendering goes to stderr to keep stdout clean for
piped data. Falls back to a numbered-list prompt when
Textual is unavailable, stdin is not a TTY, or TERM=dumb.
"""

import os
import sys

from ksm.color import bold, dim
from ksm.manifest import ManifestEntry
from ksm.scanner import BundleInfo


def group_bundles_by_registry(
    bundles: list[BundleInfo],
) -> dict[str, list[BundleInfo]]:
    """Group bundles by registry name.

    Returns an insertion-ordered dict where:
    - Keys are ``registry_name`` values, sorted
      case-insensitively with empty string last.
    - Values are lists of ``BundleInfo`` sorted
      case-insensitively by ``name``.
    """
    from collections import defaultdict

    groups: dict[str, list[BundleInfo]] = defaultdict(list)
    for bundle in bundles:
        groups[bundle.registry_name].append(bundle)

    sorted_keys = sorted(
        groups.keys(),
        key=lambda k: (k == "", k.lower()),
    )

    return {k: sorted(groups[k], key=lambda b: b.name.lower()) for k in sorted_keys}


def _can_run_textual() -> bool:
    """Check if Textual TUI can be used.

    Returns True only when all conditions are met:
    - stdin is a TTY
    - TERM is not ``dumb``
    - Textual is importable

    Returns False otherwise, signalling the caller to use
    the numbered-list fallback.
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
    group_headers: dict[int, str] | None = None,
) -> int | None:
    """Cross-platform fallback: numbered list rendered to stderr.

    Displays items with 1-based indices, reads a number from
    stdin. Returns the 0-based index of the selected item, or
    None if the user enters ``q`` or EOF. Re-prompts on invalid
    input.

    When ``group_headers`` is provided, a text header line is
    printed before the item at each keyed index. Keys are
    0-based item indices; values are the header text.
    """
    sys.stderr.write(f"\n{header}\n\n")
    for i, (name, label) in enumerate(items, 1):
        if group_headers and (i - 1) in group_headers:
            gh = group_headers[i - 1]
            sys.stderr.write(f"\n  {gh}\n")
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
    separator, then registry-grouped bundle lines. Bundles
    are grouped by registry (sorted case-insensitively),
    with bundles within each group sorted case-insensitively
    by name. Each group is preceded by a dimmed registry
    name header line.

    When ``filter_text`` is provided, bundles are filtered
    first (case-insensitive substring on name or registry),
    then grouped. Groups with zero matches are omitted.

    The ``selected`` index and ``multi_selected`` set
    reference positions in the flattened bundle list
    (excluding header lines).
    """
    sorted_bundles = sorted(
        bundles,
        key=lambda b: (b.name.lower(), b.registry_name.lower()),
    )
    if filter_text:
        ft = filter_text.lower()
        sorted_bundles = [
            b
            for b in sorted_bundles
            if ft in b.name.lower() or ft in b.registry_name.lower()
        ]

    grouped = group_bundles_by_registry(sorted_bundles)

    flat_bundles: list[BundleInfo] = []
    for group in grouped.values():
        flat_bundles.extend(group)

    max_name = max((len(b.name) for b in flat_bundles), default=0)
    badge_text = " [installed]"
    any_installed = any(b.name in installed_names for b in flat_bundles)
    badge_width = len(badge_text) if any_installed else 0
    lines: list[str] = [
        bold(_ADD_HEADER, stream=sys.stderr),
        dim(_ADD_INSTRUCTIONS, stream=sys.stderr),
        "",
    ]
    if filter_text:
        lines[2] = dim(f"Filter: {filter_text}", stream=sys.stderr)
    bundle_idx = 0
    for reg_name, group in grouped.items():
        header_label = reg_name if reg_name else "(no registry)"
        lines.append(dim(header_label, stream=sys.stderr))
        for bundle in group:
            i = bundle_idx
            prefix = ">" if i == selected else " "
            check = ""
            if multi_selected is not None:
                check = "[✓] " if i in multi_selected else "[ ] "
            padded = bundle.name.ljust(max_name)
            if i == selected:
                padded = bold(padded, stream=sys.stderr)
            if bundle.name in installed_names:
                label = dim(badge_text, stream=sys.stderr)
            else:
                label = " " * badge_width
            reg_col = ""
            if bundle.registry_name:
                reg_col = "  " + dim(bundle.registry_name, stream=sys.stderr)
            lines.append(f"{prefix} {check}{padded}{label}{reg_col}")
            bundle_idx += 1
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
    optionally filtered by ``filter_text``.

    When ``multi_selected`` is provided, each line shows
    ``[✓]`` or ``[ ]`` indicators. Names are padded to align
    columns.
    """
    sorted_entries = sorted(entries, key=lambda e: e.bundle_name.lower())
    if filter_text:
        ft = filter_text.lower()
        sorted_entries = [e for e in sorted_entries if ft in e.bundle_name.lower()]
    max_name = max((len(e.bundle_name) for e in sorted_entries), default=0)
    max_scope_inner = max((len(e.scope) for e in sorted_entries), default=0)
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
        raw_scope = f"[{entry.scope.ljust(max_scope_inner)}]"
        scope_label = dim(raw_scope, stream=sys.stderr)
        lines.append(f"{prefix} {check}{padded} {scope_label}")
    return lines


_SCOPE_OPTIONS = [
    ("local", "Local (.kiro/)"),
    ("global", "Global (~/.kiro/)"),
]
_SCOPE_HEADER = "Select installation scope:"


def scope_select() -> str | None:
    """Interactive scope selection.

    Returns ``"local"``, ``"global"``, or ``None`` (abort).

    Delegates to ScopeSelectorApp when Textual is available,
    otherwise falls back to numbered-list prompt. Non-TTY
    stdin in fallback returns ``None`` (caller defaults to
    ``"local"``).
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

    # Textual path
    try:
        from ksm.tui import ScopeSelectorApp

        app = ScopeSelectorApp()
        app.run(inline=True)
        return app.selected_scope
    except KeyboardInterrupt:
        return None
    except Exception as exc:
        print(f"Selector error: {exc}", file=sys.stderr)
        return None


def interactive_select(
    bundles: list[BundleInfo],
    installed_names: set[str],
) -> list[str] | None:
    """Show interactive add-bundle selector.

    Returns a list of selected bundle names, or ``None`` if
    the user quits. Delegates to BundleSelectorApp when
    Textual is available, otherwise falls back to numbered-list.
    """
    if not bundles:
        return None

    sorted_bundles = sorted(
        bundles,
        key=lambda b: (b.name.lower(), b.registry_name.lower()),
    )

    if not _can_run_textual():
        grouped = group_bundles_by_registry(sorted_bundles)
        flat_bundles: list[BundleInfo] = []
        items: list[tuple[str, str]] = []
        group_headers: dict[int, str] = {}

        for reg_name, group in grouped.items():
            header = reg_name if reg_name else "(no registry)"
            group_headers[len(items)] = header
            for b in group:
                label_parts: list[str] = []
                if b.name in installed_names:
                    label_parts.append("[installed]")
                items.append((b.name, "  ".join(label_parts)))
                flat_bundles.append(b)

        idx = _numbered_list_select(
            items,
            "Select a bundle to install:",
            group_headers=group_headers,
        )
        if idx is None:
            return None
        selected_bundle = flat_bundles[idx]
        if selected_bundle.registry_name:
            return [f"{selected_bundle.registry_name}" f"/{selected_bundle.name}"]
        return [selected_bundle.name]

    # Textual path
    try:
        from ksm.tui import BundleSelectorApp

        app = BundleSelectorApp(bundles, installed_names)
        app.run()
        return app.selected_names
    except KeyboardInterrupt:
        return None
    except Exception as exc:
        print(f"Selector error: {exc}", file=sys.stderr)
        return None


def interactive_removal_select(
    entries: list[ManifestEntry],
) -> list[ManifestEntry] | None:
    """Show interactive removal selector.

    Returns a list of selected ManifestEntry objects, or
    ``None`` if the user quits. Delegates to RemovalSelectorApp
    when Textual is available, otherwise falls back to
    numbered-list.
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

    # Textual path
    try:
        from ksm.tui import RemovalSelectorApp

        app = RemovalSelectorApp(entries)
        app.run()
        return app.selected_entries
    except KeyboardInterrupt:
        return None
    except Exception as exc:
        print(f"Selector error: {exc}", file=sys.stderr)
        return None
