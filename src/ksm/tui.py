"""Textual TUI apps for ksm interactive selectors.

Contains BundleSelectorApp, RemovalSelectorApp, and ScopeSelectorApp.
These are lazily imported by selector.py only when Textual is available.
"""

from __future__ import annotations

from typing import ClassVar, Union

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.theme import Theme
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from rich.text import Text

from ksm.manifest import ManifestEntry
from ksm.scanner import BundleInfo

BindingType = Union[Binding, tuple[str, str], tuple[str, str, str]]

KSM_THEME = Theme(
    name="ksm",
    primary="#56b6c2",
    secondary="#61afef",
    accent="#56b6c2",
    success="#98c379",
    warning="#e5c07b",
    error="#e06c75",
    surface="#282c34",
    panel="#21252b",
)


class BundleSelectorApp(App[None]):
    """Interactive bundle selector using Textual."""

    CSS: ClassVar[str] = """
    Screen { background: $surface; layout: vertical; }

    #container {
        border: round $accent;
        border-title-color: $accent;
        border-title-style: bold;
        padding: 0 1;
        margin: 1 2;
        height: 1fr;
    }

    Input {
        dock: top;
        margin: 0 0 1 0;
        border: tall $accent 30%;
        background: $surface-darken-1;
    }
    Input:focus { border: tall $accent; }
    Input.-invalid { border: tall $error; }

    OptionList {
        height: 1fr;
        background: transparent;
        border: none;
        scrollbar-color: $accent 30%;
        scrollbar-color-hover: $accent 60%;
        scrollbar-color-active: $accent;
    }
    OptionList > .option-list--option-highlighted {
        background: $accent 15%;
        text-style: bold;
    }
    OptionList > .option-list--option-hover {
        background: $accent 8%;
    }
    OptionList:focus > .option-list--option-highlighted {
        background: $accent 25%;
    }

    #selected-count {
        dock: bottom;
        text-style: bold;
        color: $accent;
        text-align: right;
    }

    #footer-bar {
        dock: bottom;
        height: 1;
        background: $accent 15%;
        color: $text-muted;
        padding: 0 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "quit_app", "Quit", show=False),
    ]

    def __init__(
        self,
        bundles: list[BundleInfo],
        installed_names: set[str],
    ) -> None:
        super().__init__()
        self.register_theme(KSM_THEME)
        self.theme = "ksm"
        self.bundles = bundles
        self.installed_names = installed_names
        self.selected_names: list[str] | None = None
        self.multi_selected: set[int] = set()
        self.display_items: list[tuple[str, BundleInfo]] = []
        self.filtered_items: list[tuple[str, BundleInfo]] = []
        self._build_display_items()

    def _build_display_items(self) -> None:
        sorted_bundles = sorted(
            self.bundles,
            key=lambda b: (b.name.lower(), b.registry_name.lower()),
        )
        self.display_items = [(b.name, b) for b in sorted_bundles]
        self.filtered_items = list(self.display_items)

    def compose(self) -> ComposeResult:
        with Container(id="container"):
            yield Static(
                "Select a bundle to install",
                classes="selector-header",
            )
            yield Input(placeholder="Type to filter...")
            yield OptionList()
            yield Static("", id="selected-count")
        yield Static(
            " [bold $accent]↑↓[/] Navigate  "
            "[bold $accent]Space[/] Toggle  "
            "[bold $accent]Enter[/] Confirm  "
            "[bold $accent]Esc[/] Cancel",
            id="footer-bar",
        )

    def on_mount(self) -> None:
        self._refresh_options()
        self.query_one(OptionList).focus()

    def _refresh_options(self) -> None:
        ol = self.query_one(OptionList)
        ol.clear_options()
        max_name = max(
            (len(name) for name, _ in self.filtered_items),
            default=0,
        )
        for i, (display, bundle) in enumerate(self.filtered_items):
            check = (
                "[✓] "
                if i in self.multi_selected
                else "[ ] " if self.multi_selected else ""
            )
            installed = bundle.name in self.installed_names
            badge = " [installed]" if installed else ""
            label = Text()
            label.append(check)
            label.append(display.ljust(max_name), style="bold cyan")
            if badge:
                label.append(badge, style="dim")
            if bundle.registry_name:
                label.append(f"  {bundle.registry_name}", style="dim")
            ol.add_option(Option(label, id=str(i)))
        if not self.filtered_items:
            fv = self.query_one(Input).value
            ol.add_option(
                Option(
                    f"No bundles match '{fv}'",
                    disabled=True,
                )
            )
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
                item
                for item in self.display_items
                if ft in item[0].lower() or ft in item[1].registry_name.lower()
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

    @staticmethod
    def _qualified_name(bundle: BundleInfo) -> str:
        """Build qualified name from a BundleInfo."""
        if bundle.registry_name:
            return f"{bundle.registry_name}/{bundle.name}"
        return bundle.name

    def _confirm_selection(self) -> None:
        if not self.filtered_items:
            return
        ol = self.query_one(OptionList)
        if self.multi_selected:
            self.selected_names = [
                self._qualified_name(self.filtered_items[i][1])
                for i in sorted(self.multi_selected)
                if i < len(self.filtered_items)
            ]
        else:
            idx = ol.highlighted if ol.highlighted is not None else 0
            if idx < len(self.filtered_items):
                self.selected_names = [
                    self._qualified_name(self.filtered_items[idx][1])
                ]
        self.exit()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self._confirm_selection()

    def action_quit_app(self) -> None:
        self.selected_names = None
        self.exit()


class RemovalSelectorApp(App[None]):
    """Interactive removal selector using Textual."""

    CSS: ClassVar[str] = """
    Screen { background: $surface; layout: vertical; }

    #container {
        border: round $accent;
        border-title-color: $accent;
        border-title-style: bold;
        padding: 0 1;
        margin: 1 2;
        height: 1fr;
    }

    Input {
        dock: top;
        margin: 0 0 1 0;
        border: tall $accent 30%;
        background: $surface-darken-1;
    }
    Input:focus { border: tall $accent; }
    Input.-invalid { border: tall $error; }

    OptionList {
        height: 1fr;
        background: transparent;
        border: none;
        scrollbar-color: $accent 30%;
        scrollbar-color-hover: $accent 60%;
        scrollbar-color-active: $accent;
    }
    OptionList > .option-list--option-highlighted {
        background: $accent 15%;
        text-style: bold;
    }
    OptionList > .option-list--option-hover {
        background: $accent 8%;
    }
    OptionList:focus > .option-list--option-highlighted {
        background: $accent 25%;
    }

    #selected-count {
        dock: bottom;
        text-style: bold;
        color: $accent;
        text-align: right;
    }

    #footer-bar {
        dock: bottom;
        height: 1;
        background: $accent 15%;
        color: $text-muted;
        padding: 0 1;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "quit_app", "Quit", show=False),
    ]

    def __init__(self, entries: list[ManifestEntry]) -> None:
        super().__init__()
        self.register_theme(KSM_THEME)
        self.theme = "ksm"
        self.entries = sorted(entries, key=lambda e: e.bundle_name.lower())
        self.filtered_entries: list[ManifestEntry] = list(self.entries)
        self.selected_entries: list[ManifestEntry] | None = None
        self.multi_selected: set[int] = set()

    def compose(self) -> ComposeResult:
        with Container(id="container"):
            yield Static(
                "Select a bundle to remove",
                classes="selector-header",
            )
            yield Input(placeholder="Type to filter...")
            yield OptionList()
            yield Static("", id="selected-count")
        yield Static(
            " [bold $accent]↑↓[/] Navigate  "
            "[bold $accent]Space[/] Toggle  "
            "[bold $accent]Enter[/] Confirm  "
            "[bold $accent]Esc[/] Cancel",
            id="footer-bar",
        )

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
            label = Text()
            label.append(check)
            label.append(entry.bundle_name, style="bold cyan")
            label.append(f" [{entry.scope}]", style="dim")
            ol.add_option(Option(label, id=str(i)))
        if not self.filtered_entries:
            fv = self.query_one(Input).value
            ol.add_option(
                Option(
                    f"No bundles match '{fv}'",
                    disabled=True,
                )
            )
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
    Screen { background: $surface; align: center middle; }

    #scope-container {
        border: round $accent;
        border-title-color: $accent;
        border-title-style: bold;
        padding: 1 2;
        width: 40;
        height: auto;
        max-height: 12;
    }

    OptionList {
        height: auto;
        max-height: 4;
        background: transparent;
        border: none;
    }
    OptionList > .option-list--option-highlighted {
        background: $accent 20%;
        text-style: bold;
    }
    OptionList:focus > .option-list--option-highlighted {
        background: $accent 30%;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "quit_app", "Quit", show=False),
        Binding("q", "quit_app", "Quit", show=False),
    ]

    _SCOPE_OPTIONS: ClassVar[list[tuple[str, str]]] = [
        ("local", "Local (.kiro/)"),
        ("global", "Global (~/.kiro/)"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.register_theme(KSM_THEME)
        self.theme = "ksm"
        self.selected_scope: str | None = None

    def compose(self) -> ComposeResult:
        with Container(id="scope-container"):
            yield Static(
                "Select installation scope:",
                classes="selector-header",
            )
            yield OptionList(
                *[Option(label, id=key) for key, label in self._SCOPE_OPTIONS]
            )

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
