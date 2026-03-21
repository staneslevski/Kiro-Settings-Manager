"""Textual TUI apps for ksm interactive selectors.

Contains BundleSelectorApp, RemovalSelectorApp, and ScopeSelectorApp.
These are lazily imported by selector.py only when Textual is available.
"""

from __future__ import annotations

from typing import ClassVar

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from ksm.manifest import ManifestEntry
from ksm.scanner import BundleInfo


class BundleSelectorApp(App[None]):
    """Interactive bundle selector using Textual."""

    CSS: ClassVar[str] = """
    .selector-header { text-style: bold; }
    .selector-instructions { text-style: dim; }
    .installed-badge { text-style: dim; }
    .selected-count { text-style: bold; dock: bottom; }
    OptionList { height: 1fr; }
    Input { dock: top; }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "quit_app", "Quit", show=False),
    ]

    def __init__(
        self,
        bundles: list[BundleInfo],
        installed_names: set[str],
    ) -> None:
        super().__init__()
        self.bundles = bundles
        self.installed_names = installed_names
        self.selected_names: list[str] | None = None
        self.multi_selected: set[int] = set()
        self.display_items: list[tuple[str, BundleInfo]] = []
        self.filtered_items: list[tuple[str, BundleInfo]] = []
        self._build_display_items()

    def _build_display_items(self) -> None:
        sorted_bundles = sorted(self.bundles, key=lambda b: b.name.lower())
        name_counts: dict[str, int] = {}
        for b in sorted_bundles:
            name_counts[b.name] = name_counts.get(b.name, 0) + 1
        ambiguous = {n for n, c in name_counts.items() if c > 1}

        items: list[tuple[str, BundleInfo]] = []
        for b in sorted_bundles:
            if b.name in ambiguous and b.registry_name:
                display = f"{b.registry_name}/{b.name}"
            else:
                display = b.name
            items.append((display, b))
        items.sort(key=lambda p: p[0].lower())
        self.display_items = items
        self.filtered_items = list(items)

    def compose(self) -> ComposeResult:
        yield Static("Select a bundle to install", classes="selector-header")
        yield Static(
            "↑/↓ navigate, Space toggle, Enter confirm, q/Esc quit",
            classes="selector-instructions",
        )
        yield Input(placeholder="Type to filter...")
        yield OptionList()
        yield Static("", id="selected-count", classes="selected-count")

    def on_mount(self) -> None:
        self._refresh_options()
        self.query_one(OptionList).focus()

    def _refresh_options(self) -> None:
        ol = self.query_one(OptionList)
        ol.clear_options()
        for i, (display, bundle) in enumerate(self.filtered_items):
            check = (
                "[✓] "
                if i in self.multi_selected
                else "[ ] " if self.multi_selected else ""
            )
            badge = " [installed]" if bundle.name in self.installed_names else ""
            ol.add_option(Option(f"{check}{display}{badge}", id=str(i)))
        if not self.filtered_items:
            filter_val = self.query_one(Input).value
            ol.add_option(Option(f"No bundles match '{filter_val}'", disabled=True))
        elif ol.highlighted is None:
            ol.highlighted = 0
        self._update_count()

    def _update_count(self) -> None:
        count_widget = self.query_one("#selected-count", Static)
        n = len(self.multi_selected)
        count_widget.update(f"{n} selected" if n > 0 else "")

    def on_input_changed(self, event: Input.Changed) -> None:
        ft = event.value.lower()
        if ft:
            self.filtered_items = [
                item for item in self.display_items if ft in item[0].lower()
            ]
        else:
            self.filtered_items = list(self.display_items)
        self.multi_selected = set()
        self._refresh_options()
        ol = self.query_one(OptionList)
        if self.filtered_items:
            ol.highlighted = 0

    def on_key(self, event: events.Key) -> None:
        if event.key == "q":
            filter_input = self.query_one(Input)
            if filter_input.has_focus and filter_input.value:
                return  # let Input handle it
            self.selected_names = None
            event.prevent_default()
            self.exit()
        elif event.key == "enter":
            event.prevent_default()
            self._confirm_selection()
        elif event.key == "space":
            ol = self.query_one(OptionList)
            if ol.highlighted is not None and self.filtered_items:
                idx = ol.highlighted
                if idx in self.multi_selected:
                    self.multi_selected.discard(idx)
                else:
                    self.multi_selected.add(idx)
                self._refresh_options()
                ol.highlighted = idx
            event.prevent_default()

    def _confirm_selection(self) -> None:
        if not self.filtered_items:
            return
        ol = self.query_one(OptionList)
        if self.multi_selected:
            self.selected_names = [
                self.filtered_items[i][1].name
                for i in sorted(self.multi_selected)
                if i < len(self.filtered_items)
            ]
        else:
            idx = ol.highlighted if ol.highlighted is not None else 0
            if idx < len(self.filtered_items):
                self.selected_names = [self.filtered_items[idx][1].name]
        self.exit()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self._confirm_selection()

    def action_quit_app(self) -> None:
        self.selected_names = None
        self.exit()


class RemovalSelectorApp(App[None]):
    """Interactive removal selector using Textual."""

    CSS: ClassVar[str] = """
    .selector-header { text-style: bold; }
    .selector-instructions { text-style: dim; }
    .scope-label { text-style: dim; }
    .selected-count { text-style: bold; dock: bottom; }
    OptionList { height: 1fr; }
    Input { dock: top; }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "quit_app", "Quit", show=False),
    ]

    def __init__(self, entries: list[ManifestEntry]) -> None:
        super().__init__()
        self.entries = sorted(entries, key=lambda e: e.bundle_name.lower())
        self.filtered_entries: list[ManifestEntry] = list(self.entries)
        self.selected_entries: list[ManifestEntry] | None = None
        self.multi_selected: set[int] = set()

    def compose(self) -> ComposeResult:
        yield Static("Select a bundle to remove", classes="selector-header")
        yield Static(
            "↑/↓ navigate, Space toggle, Enter confirm, q/Esc quit",
            classes="selector-instructions",
        )
        yield Input(placeholder="Type to filter...")
        yield OptionList()
        yield Static("", id="selected-count", classes="selected-count")

    def on_mount(self) -> None:
        self._refresh_options()
        self.query_one(OptionList).focus()

    def _refresh_options(self) -> None:
        ol = self.query_one(OptionList)
        ol.clear_options()
        for i, entry in enumerate(self.filtered_entries):
            check = (
                "[✓] "
                if i in self.multi_selected
                else "[ ] " if self.multi_selected else ""
            )
            ol.add_option(
                Option(f"{check}{entry.bundle_name} [{entry.scope}]", id=str(i))
            )
        if not self.filtered_entries:
            filter_val = self.query_one(Input).value
            ol.add_option(Option(f"No bundles match '{filter_val}'", disabled=True))
        elif ol.highlighted is None:
            ol.highlighted = 0
        self._update_count()

    def _update_count(self) -> None:
        count_widget = self.query_one("#selected-count", Static)
        n = len(self.multi_selected)
        count_widget.update(f"{n} selected" if n > 0 else "")

    def on_input_changed(self, event: Input.Changed) -> None:
        ft = event.value.lower()
        if ft:
            self.filtered_entries = [
                e for e in self.entries if ft in e.bundle_name.lower()
            ]
        else:
            self.filtered_entries = list(self.entries)
        self.multi_selected = set()
        self._refresh_options()
        ol = self.query_one(OptionList)
        if self.filtered_entries:
            ol.highlighted = 0

    def on_key(self, event: events.Key) -> None:
        if event.key == "q":
            filter_input = self.query_one(Input)
            if filter_input.has_focus and filter_input.value:
                return
            self.selected_entries = None
            event.prevent_default()
            self.exit()
        elif event.key == "enter":
            event.prevent_default()
            self._confirm_selection()
        elif event.key == "space":
            ol = self.query_one(OptionList)
            if ol.highlighted is not None and self.filtered_entries:
                idx = ol.highlighted
                if idx in self.multi_selected:
                    self.multi_selected.discard(idx)
                else:
                    self.multi_selected.add(idx)
                self._refresh_options()
                ol.highlighted = idx
            event.prevent_default()

    def _confirm_selection(self) -> None:
        if not self.filtered_entries:
            return
        ol = self.query_one(OptionList)
        if self.multi_selected:
            self.selected_entries = [
                self.filtered_entries[i]
                for i in sorted(self.multi_selected)
                if i < len(self.filtered_entries)
            ]
        else:
            idx = ol.highlighted if ol.highlighted is not None else 0
            if idx < len(self.filtered_entries):
                self.selected_entries = [self.filtered_entries[idx]]
        self.exit()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self._confirm_selection()

    def action_quit_app(self) -> None:
        self.selected_entries = None
        self.exit()


class ScopeSelectorApp(App[None]):
    """Interactive scope selector using Textual.

    Two options: Local (.kiro/) and Global (~/.kiro/).
    No filter, no multi-select. q always aborts.
    """

    CSS: ClassVar[str] = """
    .selector-header { text-style: bold; }
    .selector-instructions { text-style: dim; }
    OptionList { height: auto; max-height: 6; }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "quit_app", "Quit", show=False),
        Binding("q", "quit_app", "Quit", show=False),
    ]

    _SCOPE_OPTIONS: ClassVar[list[tuple[str, str]]] = [
        ("local", "Local (.kiro/)"),
        ("global", "Global (~/.kiro/)"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.selected_scope: str | None = None

    def compose(self) -> ComposeResult:
        yield Static("Select installation scope:", classes="selector-header")
        yield Static(
            "↑/↓ navigate, Enter select, q/Esc quit",
            classes="selector-instructions",
        )
        yield OptionList(*[Option(label, id=key) for key, label in self._SCOPE_OPTIONS])

    def on_mount(self) -> None:
        ol = self.query_one(OptionList)
        ol.highlighted = 0

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = event.option_index
        if 0 <= idx < len(self._SCOPE_OPTIONS):
            self.selected_scope = self._SCOPE_OPTIONS[idx][0]
        self.exit()

    def action_quit_app(self) -> None:
        self.selected_scope = None
        self.exit()
