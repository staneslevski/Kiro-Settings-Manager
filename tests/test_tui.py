"""Tests for ksm.tui Textual apps.

Uses Textual's run_test() / pilot harness for async interaction testing.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from ksm.manifest import ManifestEntry
from ksm.scanner import BundleInfo
from ksm.tui import BundleSelectorApp, RemovalSelectorApp, ScopeSelectorApp

from rich.text import Text
from textual.widgets import Input, OptionList


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
        assert app.selected_names == ["default/alpha"]

    @pytest.mark.asyncio
    async def test_navigate_down_and_select(self) -> None:
        """Down arrow then Enter selects second bundle."""
        bundles = _make_bundles("alpha", "beta", "gamma")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            await pilot.press("down")
            await pilot.press("enter")
        assert app.selected_names == ["default/beta"]

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
        assert app.selected_names == ["default/gamma"]

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
        assert set(app.selected_names) == {"default/alpha", "default/beta"}

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
        assert app.selected_names == ["default/beta"]

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
        assert app.selected_names == ["reg1/utils"]

    @pytest.mark.asyncio
    async def test_q_appends_to_filter_when_nonempty(self) -> None:
        """Property 12: q appends to filter when filter is non-empty."""
        bundles = _make_bundles("sql-queries", "alpha")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            input_widget = app.query_one(Input)
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
        assert app.selected_names == ["default/only-one"]


# ---------------------------------------------------------------
# Phase 5: KSM_THEME and app registration (Req 17.1, 17.2)
# ---------------------------------------------------------------


class TestKSMTheme:
    """Tests for KSM_THEME definition and registration."""

    def test_theme_name(self) -> None:
        """KSM_THEME has name 'ksm'."""
        from ksm.tui import KSM_THEME

        assert KSM_THEME.name == "ksm"

    def test_theme_one_dark_colors(self) -> None:
        """Theme colors match One Dark spec."""
        from ksm.tui import KSM_THEME

        assert KSM_THEME.primary == "#56b6c2"
        assert KSM_THEME.secondary == "#61afef"
        assert KSM_THEME.accent == "#56b6c2"
        assert KSM_THEME.success == "#98c379"
        assert KSM_THEME.warning == "#e5c07b"
        assert KSM_THEME.error == "#e06c75"
        assert KSM_THEME.surface == "#282c34"
        assert KSM_THEME.panel == "#21252b"

    @pytest.mark.asyncio
    async def test_bundle_selector_registers_ksm_theme(
        self,
    ) -> None:
        """BundleSelectorApp registers and activates KSM_THEME."""
        bundles = _make_bundles("alpha")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            assert app.theme == "ksm"
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_removal_selector_registers_ksm_theme(
        self,
    ) -> None:
        """RemovalSelectorApp registers and activates KSM_THEME."""
        entries = _make_entries(
            ("alpha", "local"),
        )
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            assert app.theme == "ksm"
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_scope_selector_registers_ksm_theme(
        self,
    ) -> None:
        """ScopeSelectorApp registers and activates KSM_THEME."""
        app = ScopeSelectorApp()
        async with app.run_test() as pilot:
            assert app.theme == "ksm"
            await pilot.press("escape")


# ---------------------------------------------------------------
# Phase 5: Container wrapping and footer bar (Req 18, 19)
# ---------------------------------------------------------------


class TestContainerAndFooter:
    """Tests for Container wrapping and footer bar."""

    @pytest.mark.asyncio
    async def test_bundle_selector_has_container(self) -> None:
        """BundleSelectorApp has Container#container."""
        bundles = _make_bundles("alpha")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            container = app.query_one("#container")
            assert container is not None
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_removal_selector_has_container(self) -> None:
        """RemovalSelectorApp has Container#container."""
        entries = _make_entries(
            ("alpha", "local"),
        )
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            container = app.query_one("#container")
            assert container is not None
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_scope_selector_has_scope_container(
        self,
    ) -> None:
        """ScopeSelectorApp has Container#scope-container."""
        app = ScopeSelectorApp()
        async with app.run_test() as pilot:
            container = app.query_one("#scope-container")
            assert container is not None
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_bundle_selector_has_footer_bar(self) -> None:
        """BundleSelectorApp has footer bar with key hints."""
        bundles = _make_bundles("alpha")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            footer = app.query_one("#footer-bar")
            assert footer is not None
            rendered = str(footer.render())
            assert "Navigate" in rendered
            assert "Toggle" in rendered
            assert "Confirm" in rendered
            assert "Cancel" in rendered
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_removal_selector_has_footer_bar(self) -> None:
        """RemovalSelectorApp has footer bar with key hints."""
        entries = _make_entries(
            ("alpha", "local"),
        )
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            footer = app.query_one("#footer-bar")
            assert footer is not None
            rendered = str(footer.render())
            assert "Navigate" in rendered
            await pilot.press("escape")


# ---------------------------------------------------------------
# Phase 5: CSS and OptionList styling (Req 20)
# ---------------------------------------------------------------


class TestCSSProperties:
    """Tests for CSS properties in all three apps."""

    def test_bundle_selector_css_has_transparent_bg(
        self,
    ) -> None:
        """BundleSelectorApp CSS sets OptionList transparent bg."""
        assert "background: transparent" in BundleSelectorApp.CSS

    def test_bundle_selector_css_has_no_border(self) -> None:
        """BundleSelectorApp CSS sets OptionList border: none."""
        assert "border: none" in BundleSelectorApp.CSS

    def test_bundle_selector_css_has_highlight_opacity(
        self,
    ) -> None:
        """BundleSelectorApp CSS has highlight bg opacity."""
        assert "$accent 15%" in BundleSelectorApp.CSS
        assert "$accent 25%" in BundleSelectorApp.CSS

    def test_bundle_selector_css_has_scrollbar_colors(
        self,
    ) -> None:
        """BundleSelectorApp CSS has scrollbar colors."""
        assert "scrollbar-color: $accent 30%" in (BundleSelectorApp.CSS)

    def test_bundle_selector_css_has_input_border(
        self,
    ) -> None:
        """BundleSelectorApp CSS has Input border states."""
        assert "Input:focus" in BundleSelectorApp.CSS
        assert "Input.-invalid" in BundleSelectorApp.CSS

    def test_removal_selector_css_matches_bundle(self) -> None:
        """RemovalSelectorApp CSS has same key properties."""
        assert "background: transparent" in RemovalSelectorApp.CSS
        assert "border: none" in RemovalSelectorApp.CSS
        assert "$accent 15%" in RemovalSelectorApp.CSS

    def test_scope_selector_css_has_width_40(self) -> None:
        """ScopeSelectorApp CSS has width: 40."""
        assert "width: 40" in ScopeSelectorApp.CSS

    def test_scope_selector_css_has_max_height_12(
        self,
    ) -> None:
        """ScopeSelectorApp CSS has max-height: 12."""
        assert "max-height: 12" in ScopeSelectorApp.CSS

    def test_scope_selector_css_centered(self) -> None:
        """ScopeSelectorApp CSS centers content."""
        assert "align: center middle" in ScopeSelectorApp.CSS


# ---------------------------------------------------------------
# Phase 5: Rich Text OptionList items (Req 21)
# ---------------------------------------------------------------


class TestRichTextOptions:
    """Tests for Rich Text formatting in OptionList items."""

    @pytest.mark.asyncio
    async def test_bundle_names_use_bold_cyan(self) -> None:
        """Bundle names use bold cyan Rich Text."""
        bundles = _make_bundles("alpha")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            ol = app.query_one(OptionList)
            # Index 0 is the separator; index 1 is the bundle
            option = ol.get_option_at_index(1)
            prompt = option.prompt
            assert isinstance(prompt, Text)
            assert "bold cyan" in str(prompt._spans)
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_installed_badge_uses_dim(self) -> None:
        """Installed badges use dim Rich Text."""
        bundles = _make_bundles("alpha")
        app = BundleSelectorApp(bundles, installed_names={"alpha"})
        async with app.run_test() as pilot:
            ol = app.query_one(OptionList)
            # Index 0 is the separator; index 1 is the bundle
            option = ol.get_option_at_index(1)
            prompt = option.prompt
            assert isinstance(prompt, Text)
            plain = prompt.plain
            assert "[installed]" in plain
            assert "dim" in str(prompt._spans)
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_removal_names_use_bold_cyan(self) -> None:
        """Removal selector bundle names use bold cyan."""
        entries = _make_entries(
            ("alpha", "local"),
        )
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            ol = app.query_one(OptionList)
            option = ol.get_option_at_index(0)
            prompt = option.prompt
            assert isinstance(prompt, Text)
            assert "bold cyan" in str(prompt._spans)
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_removal_scope_uses_dim(self) -> None:
        """Removal selector scope badge uses dim."""
        entries = _make_entries(
            ("alpha", "local"),
        )
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            ol = app.query_one(OptionList)
            option = ol.get_option_at_index(0)
            prompt = option.prompt
            assert isinstance(prompt, Text)
            assert "dim" in str(prompt._spans)
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_removal_registry_uses_dim(self) -> None:
        """Registry column uses dim styling.

        Validates: Requirements 2.3
        """
        entries = [
            ManifestEntry(
                bundle_name="alpha",
                source_registry="my-registry",
                scope="local",
                installed_files=[],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            ),
        ]
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            ol = app.query_one(OptionList)
            option = ol.get_option_at_index(0)
            prompt = option.prompt
            assert isinstance(prompt, Text)
            plain = prompt.plain
            assert "my-registry" in plain
            # Registry text must be styled dim
            reg_start = plain.index("my-registry")
            reg_end = reg_start + len("my-registry")
            spans_str = str(prompt._spans)
            assert "dim" in spans_str
            # Verify the dim span covers the registry
            found_dim_for_reg = False
            for span in prompt._spans:
                if (
                    "dim" in str(span.style)
                    and span.start <= reg_start
                    and span.end >= reg_end
                ):
                    found_dim_for_reg = True
                    break
            assert found_dim_for_reg, "Registry text not covered by dim span"
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_removal_three_column_label(self) -> None:
        """Option labels have all 3 segments styled.

        Validates: Requirements 2.1, 2.2, 2.3
        """
        entries = [
            ManifestEntry(
                bundle_name="mybundle",
                source_registry="corp-reg",
                scope="global",
                installed_files=[],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            ),
        ]
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            ol = app.query_one(OptionList)
            option = ol.get_option_at_index(0)
            prompt = option.prompt
            assert isinstance(prompt, Text)
            plain = prompt.plain
            # All three segments present
            assert "mybundle" in plain
            assert "[global]" in plain
            assert "corp-reg" in plain
            # Column order: name before scope before reg
            name_pos = plain.index("mybundle")
            scope_pos = plain.index("[global]")
            reg_pos = plain.index("corp-reg")
            assert name_pos < scope_pos < reg_pos
            # Check bold cyan on bundle name
            name_end = name_pos + len("mybundle")
            found_bold_cyan = False
            for span in prompt._spans:
                style_str = str(span.style)
                if (
                    "bold" in style_str
                    and "cyan" in style_str
                    and span.start <= name_pos
                    and span.end >= name_end
                ):
                    found_bold_cyan = True
                    break
            assert found_bold_cyan, "Bundle name not styled bold cyan"
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_removal_empty_registry_omitted(
        self,
    ) -> None:
        """Empty source_registry omits registry segment.

        Validates: Requirements 2.1, 2.3
        """
        entries = [
            ManifestEntry(
                bundle_name="alpha",
                source_registry="",
                scope="local",
                installed_files=[],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            ),
            ManifestEntry(
                bundle_name="beta",
                source_registry="some-reg",
                scope="global",
                installed_files=[],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            ),
        ]
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            ol = app.query_one(OptionList)
            # alpha has empty registry
            opt_alpha = ol.get_option_at_index(0)
            prompt_alpha = opt_alpha.prompt
            assert isinstance(prompt_alpha, Text)
            plain_alpha = prompt_alpha.plain
            assert "alpha" in plain_alpha
            assert "[local]" in plain_alpha
            # No registry text after scope
            scope_end = plain_alpha.index("[local]") + len("[local]")
            trailing = plain_alpha[scope_end:].strip()
            assert trailing == "", f"Expected no registry text, got: {trailing!r}"
            # beta has registry
            opt_beta = ol.get_option_at_index(1)
            prompt_beta = opt_beta.prompt
            assert isinstance(prompt_beta, Text)
            assert "some-reg" in prompt_beta.plain
            await pilot.press("escape")


# ---------------------------------------------------------------
# Coverage: BundleSelectorApp missing paths
# ---------------------------------------------------------------


class TestBundleSelectorCoverage:
    """Cover remaining BundleSelectorApp code paths."""

    @pytest.mark.asyncio
    async def test_no_match_filter_shows_message(self) -> None:
        """Filter with no matches shows disabled message."""
        bundles = _make_bundles("alpha", "beta")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            inp = app.query_one("Input")
            inp.focus()
            await pilot.press("z", "z", "z")
            ol = app.query_one(OptionList)
            assert ol.option_count == 1
            opt = ol.get_option_at_index(0)
            assert opt.disabled is True
            assert "No bundles match" in str(opt.prompt)
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_clear_filter_restores_all(self) -> None:
        """Clearing filter restores all items."""
        bundles = _make_bundles("alpha", "beta")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            inp = app.query_one("Input")
            inp.focus()
            await pilot.press("a")
            await pilot.press("backspace")
            ol = app.query_one(OptionList)
            # 1 separator + 2 bundles = 3 options
            assert ol.option_count == 3
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_enter_on_empty_filter_does_nothing(
        self,
    ) -> None:
        """Enter with no filtered items does nothing."""
        bundles = _make_bundles("alpha")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            inp = app.query_one("Input")
            inp.focus()
            await pilot.press("z", "z", "z")
            await pilot.press("enter")
            assert app.selected_names is None
            await pilot.press("escape")


# ---------------------------------------------------------------
# Coverage: RemovalSelectorApp missing paths
# ---------------------------------------------------------------


class TestRemovalSelectorCoverage:
    """Cover remaining RemovalSelectorApp code paths."""

    @pytest.mark.asyncio
    async def test_no_match_filter_shows_message(self) -> None:
        """Filter with no matches shows disabled message."""
        entries = _make_entries(("alpha", "local"), ("beta", "global"))
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            inp = app.query_one("Input")
            inp.focus()
            await pilot.press("z", "z", "z")
            ol = app.query_one(OptionList)
            assert ol.option_count == 1
            opt = ol.get_option_at_index(0)
            assert opt.disabled is True
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_clear_filter_restores_all(self) -> None:
        """Clearing filter restores all entries."""
        entries = _make_entries(("alpha", "local"), ("beta", "global"))
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            inp = app.query_one("Input")
            inp.focus()
            await pilot.press("a")
            await pilot.press("backspace")
            ol = app.query_one(OptionList)
            assert ol.option_count == 2
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_q_aborts_when_filter_empty(self) -> None:
        """q aborts RemovalSelectorApp when filter is empty."""
        entries = _make_entries(
            ("alpha", "local"),
        )
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            await pilot.press("q")
        assert app.selected_entries is None

    @pytest.mark.asyncio
    async def test_q_appends_when_filter_nonempty(
        self,
    ) -> None:
        """q appends to filter when filter is non-empty."""
        entries = _make_entries(("sql-queries", "local"), ("alpha", "local"))
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            inp = app.query_one(Input)
            inp.focus()
            await pilot.press("s")
            await pilot.press("q")
            assert inp.value == "sq"
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_enter_on_empty_filter_does_nothing(
        self,
    ) -> None:
        """Enter with no filtered entries does nothing."""
        entries = _make_entries(
            ("alpha", "local"),
        )
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            inp = app.query_one("Input")
            inp.focus()
            await pilot.press("z", "z", "z")
            await pilot.press("enter")
            assert app.selected_entries is None
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_space_toggles_in_removal(self) -> None:
        """Space toggles multi-select in RemovalSelectorApp."""
        entries = _make_entries(("alpha", "local"), ("beta", "global"))
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            await pilot.press("space")
            assert 0 in app.multi_selected
            await pilot.press("space")
            assert 0 not in app.multi_selected
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_registry_filter_matches_entry(
        self,
    ) -> None:
        """Filter by registry name keeps matching entry.

        Validates: Requirements 5.1, 5.2
        """
        entries = [
            ManifestEntry(
                bundle_name="alpha",
                source_registry="corp-reg",
                scope="local",
                installed_files=[],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            ),
            ManifestEntry(
                bundle_name="beta",
                source_registry="other-reg",
                scope="global",
                installed_files=[],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            ),
        ]
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            inp = app.query_one(Input)
            inp.focus()
            await pilot.press("c", "o", "r", "p")
            await pilot.press("enter")
        assert app.selected_entries is not None
        assert len(app.selected_entries) == 1
        assert app.selected_entries[0].bundle_name == "alpha"

    @pytest.mark.asyncio
    async def test_registry_filter_case_insensitive(
        self,
    ) -> None:
        """Filter by registry is case-insensitive.

        Validates: Requirements 5.1, 5.2
        """
        entries = [
            ManifestEntry(
                bundle_name="alpha",
                source_registry="CorpReg",
                scope="local",
                installed_files=[],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            ),
            ManifestEntry(
                bundle_name="beta",
                source_registry="other",
                scope="global",
                installed_files=[],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
            ),
        ]
        app = RemovalSelectorApp(entries)
        async with app.run_test() as pilot:
            inp = app.query_one(Input)
            inp.focus()
            # Type lowercase "corpreg" to match "CorpReg"
            for ch in "corpreg":
                await pilot.press(ch)
            await pilot.press("enter")
        assert app.selected_entries is not None
        assert len(app.selected_entries) == 1
        assert app.selected_entries[0].bundle_name == "alpha"


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
        assert app.selected_names == ["default/alpha"]


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


# ---------------------------------------------------------------
# Task 4.1.4: TUI grouped display tests
# ---------------------------------------------------------------


class TestTUIGroupedDisplay:
    """Tests for TUI grouped display with separator rows."""

    @pytest.mark.asyncio
    async def test_separator_rows_are_non_selectable(
        self,
    ) -> None:
        """Separator rows are disabled (non-selectable).

        Validates: Requirement 2.2
        """
        bundles = _make_bundles("alpha", "beta")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            ol = app.query_one(OptionList)
            # First option is the separator for "default"
            sep = ol.get_option_at_index(0)
            assert sep.disabled is True
            # Second option is a bundle (not disabled)
            bundle_opt = ol.get_option_at_index(1)
            assert bundle_opt.disabled is not True
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_multi_select_across_groups(
        self,
    ) -> None:
        """Multi-select across groups tracks correct indices.

        Validates: Requirement 5.2
        """
        b1 = BundleInfo(
            name="alpha",
            path=Path("/a"),
            subdirectories=["skills"],
            registry_name="reg1",
        )
        b2 = BundleInfo(
            name="beta",
            path=Path("/b"),
            subdirectories=["skills"],
            registry_name="reg2",
        )
        app = BundleSelectorApp([b1, b2], installed_names=set())
        async with app.run_test() as pilot:
            # Highlight starts on alpha (index 1)
            await pilot.press("space")  # toggle alpha
            # Down skips reg2 separator, lands on beta
            await pilot.press("down")
            await pilot.press("space")  # toggle beta
            await pilot.press("enter")
        assert app.selected_names is not None
        assert set(app.selected_names) == {
            "reg1/alpha",
            "reg2/beta",
        }

    @pytest.mark.asyncio
    async def test_filter_preserves_grouping_hides_empty(
        self,
    ) -> None:
        """Filter preserves grouping and hides empty groups.

        Validates: Requirement 2.4
        """
        b1 = BundleInfo(
            name="alpha",
            path=Path("/a"),
            subdirectories=["skills"],
            registry_name="reg1",
        )
        b2 = BundleInfo(
            name="beta",
            path=Path("/b"),
            subdirectories=["skills"],
            registry_name="reg2",
        )
        app = BundleSelectorApp([b1, b2], installed_names=set())
        async with app.run_test() as pilot:
            inp = app.query_one(Input)
            inp.focus()
            await pilot.press("a", "l", "p")
            ol = app.query_one(OptionList)
            # Should show: reg1 separator + alpha = 2
            assert ol.option_count == 2
            # First is separator
            sep = ol.get_option_at_index(0)
            assert sep.disabled is True
            await pilot.press("enter")
        assert app.selected_names == ["reg1/alpha"]

    @pytest.mark.asyncio
    async def test_single_registry_shows_separator(
        self,
    ) -> None:
        """Single registry shows separator header.

        Validates: Requirement 1.4
        """
        bundles = _make_bundles("alpha", "beta")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            ol = app.query_one(OptionList)
            # 1 separator + 2 bundles = 3 options
            assert ol.option_count == 3
            sep = ol.get_option_at_index(0)
            assert sep.disabled is True
            prompt_text = str(sep.prompt)
            assert "default" in prompt_text
            await pilot.press("escape")

    @pytest.mark.asyncio
    async def test_highlight_skips_separator_on_mount(
        self,
    ) -> None:
        """Initial highlight skips separator row."""
        bundles = _make_bundles("alpha")
        app = BundleSelectorApp(bundles, installed_names=set())
        async with app.run_test() as pilot:
            ol = app.query_one(OptionList)
            # Highlight should be on the first bundle,
            # not the separator
            assert ol.highlighted == 1
            await pilot.press("escape")
