"""Tests for ksm.color module."""

from io import StringIO
from unittest.mock import MagicMock, patch

from hypothesis import given
from hypothesis import strategies as st

from ksm.color import (
    SYM_ARROW,
    SYM_CHECK,
    SYM_CROSS,
    SYM_DOT,
    SYM_NEW,
    SYM_UNCHANGED,
    SYM_UPDATED,
    _align_columns,
    _color_enabled,
    _color_level,
    _strip_ansi,
    _supports_unicode,
    accent,
    bold,
    dim,
    error_style,
    green,
    info,
    muted,
    red,
    style,
    subtle,
    success,
    warning_style,
    yellow,
)


def _make_tty_stream() -> MagicMock:
    """Create a mock stream that reports as a TTY."""
    stream = MagicMock(spec=StringIO)
    stream.isatty.return_value = True
    return stream


def _make_non_tty_stream() -> StringIO:
    """Create a non-TTY stream."""
    return StringIO()


def _clean_env() -> dict[str, str]:
    """Env dict with NO_COLOR removed and TERM set."""
    return {"TERM": "xterm-256color"}


# ---------------------------------------------------------------
# Task 1.1: _color_level() detection logic
# ---------------------------------------------------------------


class TestColorLevel:
    """Tests for _color_level() — Req 2.1-2.7."""

    def test_no_color_returns_0(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            assert _color_level(stream) == 0

    def test_term_dumb_returns_0(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"TERM": "dumb"}, clear=True):
            assert _color_level(stream) == 0

    def test_non_tty_returns_0(self) -> None:
        stream = _make_non_tty_stream()
        assert _color_level(stream) == 0

    def test_colorterm_truecolor_returns_4(self) -> None:
        stream = _make_tty_stream()
        with patch.dict(
            "os.environ",
            {"TERM": "xterm", "COLORTERM": "truecolor"},
            clear=True,
        ):
            assert _color_level(stream) == 4

    def test_colorterm_24bit_returns_4(self) -> None:
        stream = _make_tty_stream()
        with patch.dict(
            "os.environ",
            {"TERM": "xterm", "COLORTERM": "24bit"},
            clear=True,
        ):
            assert _color_level(stream) == 4

    def test_term_256color_returns_3(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"TERM": "xterm-256color"}, clear=True):
            assert _color_level(stream) == 3

    def test_default_tty_returns_2(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"TERM": "xterm"}, clear=True):
            assert _color_level(stream) == 2

    def test_no_color_takes_priority_over_truecolor(self) -> None:
        stream = _make_tty_stream()
        with patch.dict(
            "os.environ",
            {"NO_COLOR": "", "COLORTERM": "truecolor"},
            clear=True,
        ):
            assert _color_level(stream) == 0

    def test_term_dumb_takes_priority_over_256color(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"TERM": "dumb"}, clear=True):
            assert _color_level(stream) == 0

    def test_no_color_empty_string_returns_0(self) -> None:
        """NO_COLOR="" (set but empty) still disables color."""
        stream = _make_tty_stream()
        with patch.dict(
            "os.environ",
            {"NO_COLOR": "", "TERM": "xterm-256color"},
            clear=True,
        ):
            assert _color_level(stream) == 0

    def test_non_tty_overrides_colorterm(self) -> None:
        """Non-TTY stream returns 0 even with COLORTERM set."""
        stream = _make_non_tty_stream()
        with patch.dict(
            "os.environ",
            {"COLORTERM": "truecolor", "TERM": "xterm"},
            clear=True,
        ):
            assert _color_level(stream) == 0

    def test_none_stream_defaults_to_stdout(self) -> None:
        """None stream falls back to sys.stdout."""
        mock_stdout = _make_tty_stream()
        with (
            patch("ksm.color.sys.stdout", mock_stdout),
            patch.dict("os.environ", {"TERM": "xterm"}, clear=True),
        ):
            assert _color_level(None) == 2

    def test_stream_without_isatty_returns_0(self) -> None:
        """Stream missing isatty attribute returns 0."""

        class NoIsatty:
            pass

        with patch.dict("os.environ", {"TERM": "xterm"}, clear=True):
            result = _color_level(NoIsatty())  # type: ignore[arg-type]
            assert result == 0

    def test_colorterm_case_insensitive(self) -> None:
        """COLORTERM matching is case-insensitive."""
        stream = _make_tty_stream()
        with patch.dict(
            "os.environ",
            {"TERM": "xterm", "COLORTERM": "TrueColor"},
            clear=True,
        ):
            assert _color_level(stream) == 4

    def test_term_256color_substring_match(self) -> None:
        """TERM like 'screen-256color' also returns 3."""
        stream = _make_tty_stream()
        with patch.dict(
            "os.environ",
            {"TERM": "screen-256color"},
            clear=True,
        ):
            assert _color_level(stream) == 3


# ---------------------------------------------------------------
# Task 1.1: _supports_unicode() and symbol constants
# ---------------------------------------------------------------


class TestSupportsUnicode:
    """Tests for _supports_unicode() — Req 3.1, 3.4."""

    def test_term_dumb_returns_false(self) -> None:
        """TERM=dumb disables Unicode — Req 3.4."""
        with patch.dict("os.environ", {"TERM": "dumb"}, clear=True):
            assert _supports_unicode() is False

    def test_non_utf8_encoding_returns_false(self) -> None:
        """Non-UTF-8 preferred encoding → False — Req 3.1."""
        with (
            patch(
                "locale.getpreferredencoding",
                return_value="ascii",
            ),
            patch.dict("os.environ", {"TERM": "xterm"}, clear=True),
        ):
            assert _supports_unicode() is False

    def test_latin1_encoding_returns_false(self) -> None:
        """Latin-1 encoding is not UTF-8 — Req 3.1."""
        with (
            patch(
                "locale.getpreferredencoding",
                return_value="ISO-8859-1",
            ),
            patch.dict("os.environ", {"TERM": "xterm"}, clear=True),
        ):
            assert _supports_unicode() is False

    def test_utf8_encoding_returns_true(self) -> None:
        """UTF-8 encoding with normal TERM → True — Req 3.1."""
        with (
            patch(
                "locale.getpreferredencoding",
                return_value="UTF-8",
            ),
            patch.dict("os.environ", {"TERM": "xterm"}, clear=True),
        ):
            assert _supports_unicode() is True

    def test_utf8_lowercase_returns_true(self) -> None:
        """Encoding comparison is case-insensitive — Req 3.1."""
        with (
            patch(
                "locale.getpreferredencoding",
                return_value="utf-8",
            ),
            patch.dict("os.environ", {"TERM": "xterm"}, clear=True),
        ):
            assert _supports_unicode() is True

    def test_utf8_no_hyphen_returns_true(self) -> None:
        """'utf8' (no hyphen) is also valid — Req 3.1."""
        with (
            patch(
                "locale.getpreferredencoding",
                return_value="utf8",
            ),
            patch.dict("os.environ", {"TERM": "xterm"}, clear=True),
        ):
            assert _supports_unicode() is True

    def test_encoding_exception_returns_false(self) -> None:
        """Exception in getpreferredencoding → False — Req 3.1."""
        with (
            patch(
                "locale.getpreferredencoding",
                side_effect=Exception("boom"),
            ),
            patch.dict("os.environ", {"TERM": "xterm"}, clear=True),
        ):
            assert _supports_unicode() is False

    def test_term_dumb_overrides_utf8(self) -> None:
        """TERM=dumb returns False even with UTF-8 — Req 3.4."""
        with (
            patch(
                "locale.getpreferredencoding",
                return_value="UTF-8",
            ),
            patch.dict("os.environ", {"TERM": "dumb"}, clear=True),
        ):
            assert _supports_unicode() is False


class TestSymbolConstants:
    """Tests for symbol constants — Req 3.2, 3.3, 3.5."""

    def test_fixed_symbols_never_change(self) -> None:
        """SYM_NEW/UPDATED/UNCHANGED are fixed — Req 3.5."""
        assert SYM_NEW == "+"
        assert SYM_UPDATED == "~"
        assert SYM_UNCHANGED == "="

    def test_unicode_symbols_when_supported(self) -> None:
        """Unicode glyphs used when supported — Req 3.2."""
        with (
            patch(
                "locale.getpreferredencoding",
                return_value="UTF-8",
            ),
            patch.dict("os.environ", {"TERM": "xterm"}, clear=True),
        ):
            import importlib
            import ksm.color as color_mod

            importlib.reload(color_mod)
            assert color_mod.SYM_CHECK == "✓"
            assert color_mod.SYM_CROSS == "✗"
            assert color_mod.SYM_ARROW == "→"
            assert color_mod.SYM_DOT == "·"

    def test_ascii_fallback_when_not_supported(self) -> None:
        """ASCII fallbacks used when Unicode unsupported — Req 3.3."""
        with (
            patch(
                "locale.getpreferredencoding",
                return_value="ascii",
            ),
            patch.dict("os.environ", {"TERM": "xterm"}, clear=True),
        ):
            import importlib
            import ksm.color as color_mod

            importlib.reload(color_mod)
            assert color_mod.SYM_CHECK == "*"
            assert color_mod.SYM_CROSS == "x"
            assert color_mod.SYM_ARROW == "->"
            assert color_mod.SYM_DOT == "-"

    def test_ascii_fallback_term_dumb(self) -> None:
        """TERM=dumb triggers ASCII fallback — Req 3.3, 3.4."""
        with patch.dict("os.environ", {"TERM": "dumb"}, clear=True):
            import importlib
            import ksm.color as color_mod

            importlib.reload(color_mod)
            assert color_mod.SYM_CHECK == "*"
            assert color_mod.SYM_CROSS == "x"
            assert color_mod.SYM_ARROW == "->"
            assert color_mod.SYM_DOT == "-"

    def test_fixed_symbols_unchanged_after_reload(self) -> None:
        """Fixed symbols stay the same regardless — Req 3.5."""
        with (
            patch(
                "locale.getpreferredencoding",
                return_value="ascii",
            ),
            patch.dict("os.environ", {"TERM": "xterm"}, clear=True),
        ):
            import importlib
            import ksm.color as color_mod

            importlib.reload(color_mod)
            assert color_mod.SYM_NEW == "+"
            assert color_mod.SYM_UPDATED == "~"
            assert color_mod.SYM_UNCHANGED == "="

    def test_sym_check_is_nonempty_string(self) -> None:
        """SYM_CHECK is always a non-empty string."""
        assert isinstance(SYM_CHECK, str) and len(SYM_CHECK) >= 1

    def test_sym_cross_is_nonempty_string(self) -> None:
        """SYM_CROSS is always a non-empty string."""
        assert isinstance(SYM_CROSS, str) and len(SYM_CROSS) >= 1

    def test_sym_arrow_is_nonempty_string(self) -> None:
        """SYM_ARROW is always a non-empty string."""
        assert isinstance(SYM_ARROW, str) and len(SYM_ARROW) >= 1

    def test_sym_dot_is_nonempty_string(self) -> None:
        """SYM_DOT is always a non-empty string."""
        assert isinstance(SYM_DOT, str) and len(SYM_DOT) >= 1


# ---------------------------------------------------------------
# Task 1.2: Semantic color functions and style()
# ---------------------------------------------------------------


class TestSemanticColors:
    """Tests for semantic color functions — Req 1.1-1.4."""

    def test_success_code_92(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = success("ok", stream)
            assert "\033[92m" in result
            assert "ok" in result

    def test_error_style_code_91(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = error_style("err", stream)
            assert "\033[91m" in result
            assert "err" in result

    def test_warning_style_code_93(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = warning_style("warn", stream)
            assert "\033[93m" in result
            assert "warn" in result

    def test_accent_code_96(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = accent("hi", stream)
            assert "\033[96m" in result
            assert "hi" in result

    def test_info_code_94(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = info("note", stream)
            assert "\033[94m" in result
            assert "note" in result

    def test_muted_code_2(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = muted("faded", stream)
            assert "\033[2m" in result
            assert "faded" in result

    def test_subtle_code_2_3(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = subtle("hint", stream)
            assert "\033[2;3m" in result
            assert "hint" in result

    def test_semantic_plain_on_non_tty(self) -> None:
        stream = _make_non_tty_stream()
        assert success("ok", stream) == "ok"
        assert error_style("err", stream) == "err"
        assert warning_style("warn", stream) == "warn"
        assert accent("hi", stream) == "hi"
        assert info("note", stream) == "note"
        assert muted("faded", stream) == "faded"
        assert subtle("hint", stream) == "hint"

    def test_semantic_plain_when_no_color(self) -> None:
        """NO_COLOR disables all semantic colors — Req 1.1."""
        stream = _make_tty_stream()
        env = {"NO_COLOR": "1", "TERM": "xterm-256color"}
        with patch.dict("os.environ", env, clear=True):
            assert success("ok", stream) == "ok"
            assert error_style("err", stream) == "err"
            assert accent("hi", stream) == "hi"

    def test_all_semantic_include_reset(self) -> None:
        """All semantic functions include reset sequence."""
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            for fn in (
                success,
                error_style,
                warning_style,
                accent,
                info,
                muted,
                subtle,
            ):
                assert "\033[0m" in fn("x", stream)

    def test_muted_is_alias_for_dim(self) -> None:
        """muted() uses same code as dim() — Req 1.1."""
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            assert muted("x", stream) == dim("x", stream)


class TestStyleFunction:
    """Tests for style() — Req 1.2."""

    def test_combines_codes(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = style("hello", "1", "96", stream=stream)
            assert "\033[1;96m" in result
            assert "hello" in result

    def test_single_code(self) -> None:
        """style() with one code works like _wrap()."""
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = style("hi", "92", stream=stream)
            assert "\033[92m" in result
            assert "hi" in result

    def test_three_codes_joined(self) -> None:
        """style() joins three codes with semicolons."""
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = style("x", "1", "2", "96", stream=stream)
            assert "\033[1;2;96m" in result

    def test_includes_reset(self) -> None:
        """style() output includes reset sequence."""
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = style("x", "1", "96", stream=stream)
            assert "\033[0m" in result

    def test_plain_on_non_tty(self) -> None:
        stream = _make_non_tty_stream()
        assert style("hello", "1", "96", stream=stream) == "hello"

    def test_plain_when_no_color(self) -> None:
        """NO_COLOR disables style() output."""
        stream = _make_tty_stream()
        env = {"NO_COLOR": "", "TERM": "xterm-256color"}
        with patch.dict("os.environ", env, clear=True):
            assert style("hi", "1", "96", stream=stream) == "hi"


class TestBrightDowngrade:
    """Tests for bright downgrade at color level 1 — Req 1.4."""

    def test_success_92_to_32(self) -> None:
        """success (92) downgrades to green (32) at level 1."""
        stream = _make_tty_stream()
        with patch("ksm.color._color_level", return_value=1):
            result = success("ok", stream)
            assert "\033[32m" in result
            assert "\033[92m" not in result

    def test_error_style_91_to_31(self) -> None:
        """error_style (91) downgrades to red (31) at level 1."""
        stream = _make_tty_stream()
        with patch("ksm.color._color_level", return_value=1):
            result = error_style("err", stream)
            assert "\033[31m" in result
            assert "\033[91m" not in result

    def test_warning_style_93_to_33(self) -> None:
        """warning_style (93) downgrades to yellow (33)."""
        stream = _make_tty_stream()
        with patch("ksm.color._color_level", return_value=1):
            result = warning_style("warn", stream)
            assert "\033[33m" in result
            assert "\033[93m" not in result

    def test_accent_96_to_36(self) -> None:
        """accent (96) downgrades to cyan (36) at level 1."""
        stream = _make_tty_stream()
        with patch("ksm.color._color_level", return_value=1):
            result = accent("hi", stream)
            assert "\033[36m" in result
            assert "\033[96m" not in result

    def test_info_94_to_34(self) -> None:
        """info (94) downgrades to blue (34) at level 1."""
        stream = _make_tty_stream()
        with patch("ksm.color._color_level", return_value=1):
            result = info("note", stream)
            assert "\033[34m" in result
            assert "\033[94m" not in result

    def test_non_bright_codes_unchanged(self) -> None:
        """Non-bright codes (< 90) stay unchanged at level 1."""
        stream = _make_tty_stream()
        with patch("ksm.color._color_level", return_value=1):
            result = green("ok", stream)
            assert "\033[32m" in result

    def test_compound_code_downgrade(self) -> None:
        """Compound codes without bright range stay as-is."""
        with patch("ksm.color._color_level", return_value=1):
            stream = _make_tty_stream()
            result = subtle("hint", stream)
            # 2;3 has no bright codes, should stay as-is
            assert "\033[2;3m" in result

    def test_style_bright_downgrade(self) -> None:
        """style() also downgrades bright codes at level 1."""
        stream = _make_tty_stream()
        with patch("ksm.color._color_level", return_value=1):
            result = style("x", "1", "96", stream=stream)
            # 96 → 36, 1 stays
            assert "\033[1;36m" in result
            assert "\033[96m" not in result

    def test_text_preserved_after_downgrade(self) -> None:
        """Original text is preserved after downgrade."""
        stream = _make_tty_stream()
        with patch("ksm.color._color_level", return_value=1):
            result = success("hello world", stream)
            assert "hello world" in result


# ---------------------------------------------------------------
# Task 1.2: _strip_ansi() and _align_columns()
# ---------------------------------------------------------------


class TestStripAnsi:
    """Tests for _strip_ansi() — Req 1.5."""

    def test_removes_ansi(self) -> None:
        assert _strip_ansi("\033[32mhello\033[0m") == "hello"

    def test_preserves_plain(self) -> None:
        assert _strip_ansi("plain text") == "plain text"

    def test_empty_string(self) -> None:
        assert _strip_ansi("") == ""

    def test_multiple_codes(self) -> None:
        s = "\033[1m\033[96mbold cyan\033[0m"
        assert _strip_ansi(s) == "bold cyan"

    def test_nested_adjacent_ansi_codes(self) -> None:
        """Multiple adjacent/nested ANSI codes all stripped."""
        s = "\033[1m\033[4m\033[96mstacked\033[0m\033[0m\033[0m"
        assert _strip_ansi(s) == "stacked"

    def test_compound_code(self) -> None:
        """Compound codes like \\033[1;96m are stripped."""
        s = "\033[1;96mbold cyan\033[0m"
        assert _strip_ansi(s) == "bold cyan"

    def test_only_ansi_codes_returns_empty(self) -> None:
        """String containing only ANSI codes returns empty."""
        s = "\033[1m\033[96m\033[0m"
        assert _strip_ansi(s) == ""

    def test_interleaved_text_and_codes(self) -> None:
        """Text interleaved with multiple ANSI sequences."""
        s = "\033[91merr\033[0m: \033[2mdetail\033[0m"
        assert _strip_ansi(s) == "err: detail"


class TestAlignColumns:
    """Tests for _align_columns() — Req 4.1-4.4."""

    def test_empty_input(self) -> None:
        assert _align_columns([]) == []

    def test_single_row(self) -> None:
        result = _align_columns([("a", "b")])
        assert result == ["a  b"]

    def test_alignment_with_ansi(self) -> None:
        rows = [
            ("\033[96mshort\033[0m", "val1"),
            ("\033[96mlonger-name\033[0m", "val2"),
        ]
        result = _align_columns(rows)
        # Both lines should have val at same position
        stripped = [_strip_ansi(line) for line in result]
        pos1 = stripped[0].index("val1")
        pos2 = stripped[1].index("val2")
        assert pos1 == pos2

    def test_last_column_no_trailing_padding(self) -> None:
        rows = [("a", "b"), ("cc", "d")]
        result = _align_columns(rows)
        # Last column should not have trailing spaces
        for line in result:
            assert not line.endswith(" ")

    def test_varying_column_counts(self) -> None:
        """Shorter rows are handled; longer rows set widths."""
        rows = [("a", "b", "c"), ("dd",)]
        result = _align_columns(rows)
        assert len(result) == 2
        # First row has all three columns
        stripped_0 = _strip_ansi(result[0])
        assert "a" in stripped_0 and "b" in stripped_0
        # Second row has only one column, no crash
        stripped_1 = _strip_ansi(result[1])
        assert "dd" in stripped_1

    def test_custom_gap(self) -> None:
        """Custom gap parameter controls inter-column spacing."""
        rows = [("a", "b"), ("cc", "d")]
        result = _align_columns(rows, gap=4)
        stripped = [_strip_ansi(line) for line in result]
        # "cc" is widest col0 (2 chars), so "a" gets 2+4=6 pad
        pos_b = stripped[0].index("b")
        pos_d = stripped[1].index("d")
        assert pos_b == pos_d
        # Gap of 4 means col1 starts at width(2) + gap(4) = 6
        assert pos_b == 6

    def test_three_columns_alignment(self) -> None:
        """Three columns align correctly across rows."""
        rows = [
            ("name", "registry", "2d ago"),
            ("longer-name", "reg", "5m ago"),
        ]
        result = _align_columns(rows)
        stripped = [_strip_ansi(line) for line in result]
        # Column 1 starts at same position in both rows
        pos_reg_0 = stripped[0].index("registry")
        pos_reg_1 = stripped[1].index("reg")
        assert pos_reg_0 == pos_reg_1
        # Column 2 starts at same position in both rows
        pos_time_0 = stripped[0].index("2d ago")
        pos_time_1 = stripped[1].index("5m ago")
        assert pos_time_0 == pos_time_1

    def test_ansi_cells_consistent_visible_positions(self) -> None:
        """ANSI-colored cells produce consistent visible positions."""
        rows = [
            (
                "\033[96mfoo\033[0m",
                "\033[2mdefault\033[0m",
                "\033[2m2d\033[0m",
            ),
            (
                "\033[96mlonger-name\033[0m",
                "\033[2mreg\033[0m",
                "\033[2m5m\033[0m",
            ),
        ]
        result = _align_columns(rows)
        stripped = [_strip_ansi(line) for line in result]
        # Verify col1 and col2 visible positions match
        pos_c1_r0 = stripped[0].index("default")
        pos_c1_r1 = stripped[1].index("reg")
        assert pos_c1_r0 == pos_c1_r1
        pos_c2_r0 = stripped[0].index("2d")
        pos_c2_r1 = stripped[1].index("5m")
        assert pos_c2_r0 == pos_c2_r1

    def test_last_column_no_padding_three_cols(self) -> None:
        """Last column has no trailing padding with 3+ columns."""
        rows = [
            ("short", "mid", "end"),
            ("longer-name", "m", "e"),
        ]
        result = _align_columns(rows)
        for line in result:
            assert not line.endswith(" ")


# ---------------------------------------------------------------
# Legacy function backward compatibility
# ---------------------------------------------------------------


class TestLegacyFunctions:
    """Existing green/red/yellow/dim/bold remain unchanged — Req 1.3."""

    def test_green_returns_plain_non_tty(self) -> None:
        stream = _make_non_tty_stream()
        assert green("hello", stream) == "hello"

    def test_red_returns_plain_non_tty(self) -> None:
        stream = _make_non_tty_stream()
        assert red("hello", stream) == "hello"

    def test_yellow_returns_plain_non_tty(self) -> None:
        stream = _make_non_tty_stream()
        assert yellow("hello", stream) == "hello"

    def test_dim_returns_plain_non_tty(self) -> None:
        stream = _make_non_tty_stream()
        assert dim("hello", stream) == "hello"

    def test_bold_returns_plain_non_tty(self) -> None:
        stream = _make_non_tty_stream()
        assert bold("hello", stream) == "hello"

    def test_green_wraps_code_32(self) -> None:
        """green uses code 32 — Req 1.3."""
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = green("ok", stream)
            assert "\033[32m" in result
            assert "ok" in result

    def test_red_wraps_code_31(self) -> None:
        """red uses code 31 — Req 1.3."""
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = red("err", stream)
            assert "\033[31m" in result
            assert "err" in result

    def test_yellow_wraps_code_33(self) -> None:
        """yellow uses code 33 — Req 1.3."""
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = yellow("warn", stream)
            assert "\033[33m" in result
            assert "warn" in result

    def test_dim_wraps_code_2(self) -> None:
        """dim uses code 2 — Req 1.3."""
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = dim("faded", stream)
            assert "\033[2m" in result
            assert "faded" in result

    def test_bold_wraps_code_1(self) -> None:
        """bold uses code 1 — Req 1.3."""
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = bold("strong", stream)
            assert "\033[1m" in result
            assert "strong" in result

    def test_legacy_codes_not_bright(self) -> None:
        """Legacy functions use standard codes, not bright."""
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            assert "\033[92m" not in green("x", stream)
            assert "\033[91m" not in red("x", stream)
            assert "\033[93m" not in yellow("x", stream)


# ---------------------------------------------------------------
# _color_enabled backward compatibility
# ---------------------------------------------------------------


class TestColorEnabled:
    """_color_enabled still works as before."""

    def test_disabled_no_color_env(self) -> None:
        with patch.dict("os.environ", {"NO_COLOR": "1"}):
            assert not _color_enabled()

    def test_disabled_term_dumb(self) -> None:
        with patch.dict("os.environ", {"TERM": "dumb"}, clear=True):
            assert not _color_enabled()

    def test_disabled_non_tty(self) -> None:
        assert not _color_enabled(_make_non_tty_stream())

    def test_enabled_tty(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            assert _color_enabled(stream)

    def test_no_isatty_attribute(self) -> None:
        class NoIsatty:
            pass

        assert not _color_enabled(NoIsatty())  # type: ignore[arg-type]


# ---------------------------------------------------------------
# Task 1.1.5: Property-based test for _color_level()
# Feature: ux-visual-overhaul, Property 5: _color_level() returns
# valid level respecting environment priority
# ---------------------------------------------------------------

# Strategies for environment variable combinations
_no_color_st = st.one_of(
    st.none(),
    st.text(
        alphabet=st.characters(blacklist_characters="\x00"),
        min_size=0,
        max_size=5,
    ),
)
_term_st = st.sampled_from(
    [
        None,
        "dumb",
        "xterm",
        "xterm-256color",
        "screen-256color",
        "linux",
        "vt100",
        "screen",
    ]
)
_colorterm_st = st.one_of(
    st.none(),
    st.sampled_from(["truecolor", "24bit", "TrueColor", "24BIT", ""]),
)
_is_tty_st = st.booleans()


def _build_env(
    no_color: str | None,
    term: str | None,
    colorterm: str | None,
) -> dict[str, str]:
    """Build an env dict from optional values."""
    env: dict[str, str] = {}
    if no_color is not None:
        env["NO_COLOR"] = no_color
    if term is not None:
        env["TERM"] = term
    if colorterm is not None:
        env["COLORTERM"] = colorterm
    return env


@given(
    no_color=_no_color_st,
    term=_term_st,
    colorterm=_colorterm_st,
    is_tty=_is_tty_st,
)
def test_color_level_valid_and_priority(
    no_color: str | None,
    term: str | None,
    colorterm: str | None,
    is_tty: bool,
) -> None:
    """**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7**

    For any combination of NO_COLOR, TERM, COLORTERM, and TTY
    state, _color_level() returns a value in {0,1,2,3,4} and
    respects the documented priority ordering.
    """
    env = _build_env(no_color, term, colorterm)

    if is_tty:
        stream = _make_tty_stream()
    else:
        stream = _make_non_tty_stream()

    with patch.dict("os.environ", env, clear=True):
        level = _color_level(stream)

    # 1. Return value always in valid set
    assert level in {0, 1, 2, 3, 4}

    # 2. Priority rules
    if no_color is not None:
        # NO_COLOR set (any value including "") → 0
        assert level == 0, (
            f"NO_COLOR={no_color!r} should force level 0, " f"got {level}"
        )
    elif term == "dumb":
        # TERM=dumb → 0
        assert level == 0, f"TERM=dumb should force level 0, got {level}"
    elif not is_tty:
        # Non-TTY → 0
        assert level == 0, f"Non-TTY should force level 0, got {level}"
    elif colorterm is not None and colorterm.lower() in ("truecolor", "24bit"):
        # COLORTERM=truecolor|24bit on TTY → 4
        assert level == 4, (
            f"COLORTERM={colorterm!r} on TTY should give 4, " f"got {level}"
        )
    elif term is not None and "256color" in term:
        # TERM contains 256color on TTY → 3
        assert level == 3, f"TERM={term!r} on TTY should give 3, " f"got {level}"
    else:
        # Default TTY → 2
        assert level == 2, (
            f"Default TTY should give 2, got {level} "
            f"(term={term!r}, colorterm={colorterm!r})"
        )


# ---------------------------------------------------------------
# Task 1.2.5: Property-based tests for color functions
# (Properties 1-4)
# ---------------------------------------------------------------

# Mapping of color functions to their expected ANSI codes.
_COLOR_FN_CODES: list[tuple[object, str]] = [
    (success, "92"),
    (error_style, "91"),
    (warning_style, "93"),
    (accent, "96"),
    (info, "94"),
    (muted, "2"),
    (subtle, "2;3"),
    (green, "32"),
    (red, "31"),
    (yellow, "33"),
    (dim, "2"),
    (bold, "1"),
]

_color_fn_st = st.sampled_from(_COLOR_FN_CODES)

# Strategy for printable text that won't contain ANSI escapes.
_plain_text_st = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        blacklist_characters="\x1b",
    ),
    min_size=1,
    max_size=50,
)


# Feature: ux-visual-overhaul, Property 1: Color functions
# produce correct ANSI codes
@given(text=_plain_text_st, fn_code=_color_fn_st)
def test_color_functions_produce_correct_ansi_codes(
    text: str,
    fn_code: tuple[object, str],
) -> None:
    """**Validates: Requirements 1.1, 1.3**

    For any input string and any semantic/legacy color
    function, when called with a TTY stream at color
    level >= 2, the output contains the expected ANSI
    escape code and the original text.
    """
    fn, code = fn_code
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        result = fn(text, stream)  # type: ignore[operator]
    assert f"\033[{code}m" in result
    assert text in result
    assert "\033[0m" in result


# Feature: ux-visual-overhaul, Property 2: style() combines
# multiple ANSI codes
_ansi_code_st = st.sampled_from(
    ["1", "2", "3", "4", "31", "32", "33", "91", "92", "93", "96"]
)


@given(
    text=_plain_text_st,
    codes=st.lists(_ansi_code_st, min_size=1, max_size=5),
)
def test_style_combines_multiple_ansi_codes(
    text: str,
    codes: list[str],
) -> None:
    """**Validates: Requirements 1.2**

    For any input string and any set of valid ANSI code
    strings, style(text, *codes) on a TTY stream at color
    level >= 2 produces a string containing a single escape
    sequence with all codes joined by semicolons.
    """
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        result = style(text, *codes, stream=stream)
    combined = ";".join(codes)
    assert f"\033[{combined}m" in result
    assert text in result
    assert "\033[0m" in result


# Feature: ux-visual-overhaul, Property 3: Bright variant
# downgrade on 8-color terminals
_bright_code_st = st.integers(min_value=90, max_value=97)


@given(text=_plain_text_st, bright_code=_bright_code_st)
def test_bright_variant_downgrade_on_8_color(
    text: str,
    bright_code: int,
) -> None:
    """**Validates: Requirements 1.4**

    For any bright ANSI code in range 90-97 and any input
    string, when _wrap() is called with a stream at color
    level 1, the output contains the corresponding standard
    code (code - 60).
    """
    from ksm.color import _wrap

    stream = _make_tty_stream()
    with patch("ksm.color._color_level", return_value=1):
        result = _wrap(text, str(bright_code), stream)
    standard = bright_code - 60
    assert f"\033[{standard}m" in result
    assert f"\033[{bright_code}m" not in result
    assert text in result


# Feature: ux-visual-overhaul, Property 4: strip_ansi round
# trip
@given(text=_plain_text_st, fn_code=_color_fn_st)
def test_strip_ansi_round_trip(
    text: str,
    fn_code: tuple[object, str],
) -> None:
    """**Validates: Requirements 1.5**

    For any plain string (no ANSI sequences), wrapping with
    any color function then calling _strip_ansi() returns
    the original string.
    """
    fn, _code = fn_code
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        wrapped = fn(text, stream)  # type: ignore[operator]
    assert _strip_ansi(wrapped) == text


# ---------------------------------------------------------------
# Task 1.2.6: Property-based test for _align_columns()
# Feature: ux-visual-overhaul, Property 6: _align_columns()
# produces ANSI-aware aligned output with no last-column padding
# ---------------------------------------------------------------

# ANSI color wrappers for generating colored cells.
_ANSI_WRAPPERS = [
    lambda t: f"\033[92m{t}\033[0m",  # success
    lambda t: f"\033[91m{t}\033[0m",  # error
    lambda t: f"\033[96m{t}\033[0m",  # accent
    lambda t: f"\033[2m{t}\033[0m",  # muted
    lambda t: f"\033[1;96m{t}\033[0m",  # bold accent
]

_ansi_wrapper_st = st.sampled_from(_ANSI_WRAPPERS)


def _cell_strategy() -> st.SearchStrategy[str]:
    """Strategy producing plain or ANSI-wrapped cell text."""
    plain = st.text(
        alphabet=st.characters(
            whitelist_categories=("L", "N"),
            blacklist_characters="\x1b",
        ),
        min_size=1,
        max_size=15,
    )
    colored = plain.flatmap(lambda txt: _ansi_wrapper_st.map(lambda wrap: wrap(txt)))
    return st.one_of(plain, colored)


def _row_strategy(
    num_cols: int,
) -> st.SearchStrategy[tuple[str, ...]]:
    """Strategy producing a row tuple with a fixed column count."""
    return st.tuples(*[_cell_strategy() for _ in range(num_cols)])


_rows_st = st.integers(min_value=1, max_value=5).flatmap(
    lambda num_cols: st.tuples(
        st.just(num_cols),
        st.lists(
            _row_strategy(num_cols),
            min_size=1,
            max_size=5,
        ),
    )
)


@given(data=_rows_st)
def test_align_columns_ansi_aware_alignment(
    data: tuple[int, list[tuple[str, ...]]],
) -> None:
    """**Validates: Requirements 4.2, 4.3**

    For any non-empty list of row tuples (potentially
    containing ANSI escape sequences), _align_columns()
    produces lines where the visible (ANSI-stripped) start
    position of each column is consistent across all rows,
    and the last column has no trailing padding spaces.
    """
    num_cols, rows = data
    result = _align_columns(rows)

    # Output length equals input length
    assert len(result) == len(rows)

    # Strip ANSI from each output line for visible analysis
    stripped = [_strip_ansi(line) for line in result]

    # Compute expected column widths and start positions
    # from the input rows, mirroring _align_columns() logic.
    widths = [0] * num_cols
    for row in rows:
        for i, cell in enumerate(row):
            w = len(_strip_ansi(cell))
            if w > widths[i]:
                widths[i] = w

    gap = 2  # default gap
    # Expected start position for each column
    col_starts = [0] * num_cols
    for c in range(1, num_cols):
        col_starts[c] = col_starts[c - 1] + widths[c - 1] + gap

    # Verify each row's column content appears at the
    # expected start position in the stripped output.
    for row_idx, row in enumerate(rows):
        for col_idx, cell in enumerate(row):
            cell_visible = _strip_ansi(cell)
            if not cell_visible:
                continue
            expected_pos = col_starts[col_idx]
            actual = stripped[row_idx][expected_pos : expected_pos + len(cell_visible)]
            assert actual == cell_visible, (
                f"Row {row_idx}, col {col_idx}: "
                f"expected {cell_visible!r} at pos "
                f"{expected_pos}, got {actual!r}"
            )

    # Last column has no trailing padding spaces
    for line in result:
        assert not line.endswith(" "), f"Line has trailing spaces: {line!r}"


def test_align_columns_empty_input_returns_empty() -> None:
    """**Validates: Requirements 4.2, 4.3**

    Empty input returns empty list.
    """
    assert _align_columns([]) == []
