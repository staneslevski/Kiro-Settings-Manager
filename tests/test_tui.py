"""Tests for ksm.tui Textual apps.

Uses Textual's run_test() / pilot harness for async interaction testing.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from ksm.manifest import ManifestEntry
from ksm.scanner import BundleInfo
from ksm.tui import BundleSelectorApp, RemovalSelectorApp, ScopeSelectorApp

from textual.widgets import OptionList


def _make_bundles(*names: str, registry: str = "default") -> list[BundleInfo]:
    return [
        BundleInfo(
            name=n,
            path=Path(f"/{n}"),
            subdirectories=["skills"],
            registry_name=registry,
        )
        for n in names
    ]


def _make_entries(*specs: tuple[str, str]) -> list[ManifestEntry]:
    return [
        ManifestEntry(
            bundle_name=name,
            source_registry="default",
            scope=scope,
            installed_files=[],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        for name, scope in specs
    ]


# ---------------------------------------------------------------
# BundleSelectorApp tests
# ---------------------------------------------------------------


class TestBundleSelectorApp:
    """Tests for BundleSelectorApp."""

    @pytest.mark.asyncio
    async def test_enter_returns_highlighted_bundle(self) -> None:
        """Enter with no toggles returns the highlighted bundle."""
        bundles = _make_bundles("alpha", "beta", "gamma")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            await pilot.press("enter")
        assert app.selected_names == ["alpha"]

    @pytest.mark.asyncio
    async def test_navigate_down_and_select(self) -> None:
        """Down arrow then Enter selects second bundle."""
        bundles = _make_bundles("alpha", "beta", "gamma")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            await pilot.press("down")
            await pilot.press("enter")
        assert app.selected_names == ["beta"]

    @pytest.mark.asyncio
    async def test_escape_aborts(self) -> None:
        """Escape returns None."""
        bundles = _make_bundles("alpha")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            await pilot.press("escape")
        assert app.selected_names is None

    @pytest.mark.asyncio
    async def test_q_aborts_when_filter_empty(self) -> None:
        """q aborts when filter is empty."""
        bundles = _make_bundles("alpha")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            await pilot.press("q")
        assert app.selected_names is None

    @pytest.mark.asyncio
    async def test_home_end_navigation(self) -> None:
        """Home/End jump to first/last item."""
        bundles = _make_bundles("alpha", "beta", "gamma")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            await pilot.press("end")
            await pilot.press("enter")
        assert app.selected_names == ["gamma"]

    @pytest.mark.asyncio
    async def test_multi_select_with_space(self) -> None:
        """Space toggles multi-select, Enter returns all toggled."""
        bundles = _make_bundles("alpha", "beta", "gamma")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            await pilot.press("space")  # toggle alpha
            await pilot.press("down")
            await pilot.press("space")  # toggle beta
            await pilot.press("enter")
        assert app.selected_names is not None
        assert set(app.selected_names) == {"alpha", "beta"}

    @pytest.mark.asyncio
    async def test_filter_narrows_list(self) -> None:
        """Typing in filter narrows the option list."""
        bundles = _make_bundles("alpha", "beta", "gamma")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            # Focus the input and type
            input_widget = app.query_one("Input")
            input_widget.focus()
            await pilot.press("b", "e", "t")
            await pilot.press("enter")
        assert app.selected_names == ["beta"]

    @pytest.mark.asyncio
    async def test_filter_change_resets_highlight_and_toggles(self) -> None:
        """Property 4: Filter change resets highlight to 0 and clears toggles."""
        bundles = _make_bundles("alpha", "beta", "gamma")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            await pilot.press("space")  # toggle alpha
            input_widget = app.query_one("Input")
            input_widget.focus()
            await pilot.press("a")
            # After filter change, toggles should be cleared
            assert len(app.multi_selected) == 0

    @pytest.mark.asyncio
    async def test_selected_count_indicator(self) -> None:
        """Property 6: Selected count equals cardinality of toggled set."""
        bundles = _make_bundles("alpha", "beta", "gamma")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            await pilot.press("space")
            await pilot.press("down")
            await pilot.press("space")
            count_text = app.query_one("#selected-count").render()
            assert "2" in str(count_text)

    @pytest.mark.asyncio
    async def test_disambiguation_display(self) -> None:
        """Ambiguous names show registry/bundle format."""
        b1 = BundleInfo(
            name="utils",
            path=Path("/a"),
            subdirectories=["skills"],
            registry_name="reg1",
        )
        b2 = BundleInfo(
            name="utils",
            path=Path("/b"),
            subdirectories=["skills"],
            registry_name="reg2",
        )
        app = BundleSelectorApp([b1, b2], installed_names=set())
        async with app.run_test() as pilot:
            await pilot.press("enter")
        # Should return the bundle name (not qualified)
        assert app.selected_names == ["utils"]

    @pytest.mark.asyncio
    async def test_q_appends_to_filter_when_nonempty(self) -> None:
        """Property 12: q appends to filter when filter is non-empty."""
        bundles = _make_bundles("sql-queries", "alpha")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            input_widget = app.query_one("Input")
            input_widget.focus()
            await pilot.press("s")
            await pilot.press("q")
            # App should still be running (not aborted)
            assert app.selected_names is None  # not yet selected
            assert input_widget.value == "sq"


# ---------------------------------------------------------------
# RemovalSelectorApp tests
# ---------------------------------------------------------------


class TestRemovalSelectorApp:
    """Tests for RemovalSelectorApp."""

    @pytest.mark.asyncio
    async def test_enter_returns_entry(self) -> None:
        """Enter returns the highlighted ManifestEntry."""
        entries = _make_entries(("alpha", "local"), ("beta", "global"))
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            await pilot.press("enter")
        assert app.selected_entries is not None
        assert app.selected_entries[0].bundle_name == "alpha"

    @pytest.mark.asyncio
    async def test_escape_aborts(self) -> None:
        """Escape returns None."""
        entries = _make_entries(
            ("alpha", "local"),
        )
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            await pilot.press("escape")
        assert app.selected_entries is None

    @pytest.mark.asyncio
    async def test_multi_select(self) -> None:
        """Space toggles, Enter returns all toggled entries."""
        entries = _make_entries(("alpha", "local"), ("beta", "global"))
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            await pilot.press("space")
            await pilot.press("down")
            await pilot.press("space")
            await pilot.press("enter")
        assert app.selected_entries is not None
        names = {e.bundle_name for e in app.selected_entries}
        assert names == {"alpha", "beta"}

    @pytest.mark.asyncio
    async def test_filter_narrows_list(self) -> None:
        """Filter narrows removal list."""
        entries = _make_entries(("alpha", "local"), ("beta", "global"))
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            input_widget = app.query_one("Input")
            input_widget.focus()
            await pilot.press("b", "e", "t")
            await pilot.press("enter")
        assert app.selected_entries is not None
        assert app.selected_entries[0].bundle_name == "beta"

    @pytest.mark.asyncio
    async def test_scope_labels_displayed(self) -> None:
        """Scope labels appear in option text."""
        entries = _make_entries(("alpha", "local"), ("beta", "global"))
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            ol = app.query_one(OptionList)
            # Check that options contain scope labels
            option_0 = ol.get_option_at_index(0)
            option_1 = ol.get_option_at_index(1)
            assert "[local]" in str(option_0.prompt)
            assert "[global]" in str(option_1.prompt)
            await pilot.press("escape")


# ---------------------------------------------------------------
# ScopeSelectorApp tests
# ---------------------------------------------------------------


class TestScopeSelectorApp:
    """Tests for ScopeSelectorApp."""

    @pytest.mark.asyncio
    async def test_enter_returns_local_by_default(self) -> None:
        """Enter without navigation returns 'local'."""
        app = ScopeSelectorApp()
        async with app.run_test() as pilot:
            await pilot.press("enter")
        assert app.selected_scope == "local"

    @pytest.mark.asyncio
    async def test_navigate_to_global(self) -> None:
        """Down then Enter returns 'global'."""
        app = ScopeSelectorApp()
        async with app.run_test() as pilot:
            await pilot.press("down")
            await pilot.press("enter")
        assert app.selected_scope == "global"

    @pytest.mark.asyncio
    async def test_escape_aborts(self) -> None:
        """Escape returns None."""
        app = ScopeSelectorApp()
        async with app.run_test() as pilot:
            await pilot.press("escape")
        assert app.selected_scope is None

    @pytest.mark.asyncio
    async def test_q_aborts(self) -> None:
        """q always aborts (no filter)."""
        app = ScopeSelectorApp()
        async with app.run_test() as pilot:
            await pilot.press("q")
        assert app.selected_scope is None


# ---------------------------------------------------------------
# Edge cases (Req 16)
# ---------------------------------------------------------------


class TestEdgeCases:
    """Empty list and single-item edge cases."""

    def test_empty_bundle_list_returns_none(self) -> None:
        """interactive_select with empty list returns None without app."""
        from ksm.selector import interactive_select

        result = interactive_select([], set())
        assert result is None

    def test_empty_entry_list_returns_none(self) -> None:
        """interactive_removal_select with empty list returns None."""
        from ksm.selector import interactive_removal_select

        result = interactive_removal_select([])
        assert result is None

    @pytest.mark.asyncio
    async def test_single_bundle_shows_full_ui(self) -> None:
        """Single item still shows full UI (Req 16.3)."""
        bundles = _make_bundles("only-one")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            # Verify header is present
            header = app.query_one(".selector-header")
            assert header is not None
            await pilot.press("enter")
        assert app.selected_names == ["only-one"]


# ---------------------------------------------------------------
# NO_COLOR support (Req 10.5, 10.9)
# ---------------------------------------------------------------


class TestNoColor:
    """Verify Textual apps work with NO_COLOR."""

    @pytest.mark.asyncio
    async def test_bundle_selector_works_with_no_color(self) -> None:
        """App functions correctly when NO_COLOR is set."""
        bundles = _make_bundles("alpha", "beta")
        app = BundleSelectorApp(bundles, installed_names=set())
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("NO_COLOR", "1")
            async with app.run_test() as pilot:
                await pilot.press("enter")
        assert app.selected_names == ["alpha"]


# ---------------------------------------------------------------
# Color module coexistence (Req 13)
# ---------------------------------------------------------------


class TestColorCoexistence:
    """Verify color.py is still used by non-Textual modules."""

    def test_errors_uses_color_module(self) -> None:
        """errors.py imports from color module."""
        import inspect
        import ksm.errors as errors_mod

        source = inspect.getsource(errors_mod)
        assert "from ksm.color import" in source or "ksm.color" in source

    def test_copier_uses_color_module(self) -> None:
        """copier.py imports from color module."""
        import inspect
        import ksm.copier as copier_mod

        source = inspect.getsource(copier_mod)
        assert "from ksm.color import" in source or "ksm.color" in source

    def test_tui_does_not_use_color_module(self) -> None:
        """tui.py uses CSS styling, not color.py."""
        import inspect
        import ksm.tui as tui_mod

        source = inspect.getsource(tui_mod)
        assert "from ksm.color" not in source
