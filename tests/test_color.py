"""Tests for ksm.color module."""

from io import StringIO
from unittest.mock import MagicMock, patch

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
        with patch.dict(
            "os.environ", {"TERM": "xterm-256color"}, clear=True
        ):
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
        with patch.dict(
            "os.environ", {"TERM": "dumb"}, clear=True
        ):
            assert _color_level(stream) == 0


# ---------------------------------------------------------------
# Task 1.1: _supports_unicode() and symbol constants
# ---------------------------------------------------------------


class TestSupportsUnicode:
    """Tests for _supports_unicode() — Req 3.1-3.5."""

    def test_term_dumb_returns_false(self) -> None:
        with patch.dict("os.environ", {"TERM": "dumb"}, clear=True):
            assert _supports_unicode() is False

    def test_non_utf8_returns_false(self) -> None:
        with patch(
            "locale.getpreferredencoding", return_value="ascii"
        ), patch.dict("os.environ", {"TERM": "xterm"}, clear=True):
            assert _supports_unicode() is False

    def test_utf8_returns_true(self) -> None:
        with patch(
            "locale.getpreferredencoding", return_value="UTF-8"
        ), patch.dict("os.environ", {"TERM": "xterm"}, clear=True):
            assert _supports_unicode() is True


class TestSymbolConstants:
    """Tests for symbol constants — Req 3.3-3.5."""

    def test_fixed_symbols(self) -> None:
        assert SYM_NEW == "+"
        assert SYM_UPDATED == "~"
        assert SYM_UNCHANGED == "="

    def test_sym_check_is_string(self) -> None:
        assert isinstance(SYM_CHECK, str) and len(SYM_CHECK) >= 1

    def test_sym_cross_is_string(self) -> None:
        assert isinstance(SYM_CROSS, str) and len(SYM_CROSS) >= 1

    def test_sym_arrow_is_string(self) -> None:
        assert isinstance(SYM_ARROW, str) and len(SYM_ARROW) >= 1

    def test_sym_dot_is_string(self) -> None:
        assert isinstance(SYM_DOT, str) and len(SYM_DOT) >= 1


# ---------------------------------------------------------------
# Task 1.2: Semantic color functions and style()
# ---------------------------------------------------------------


class TestSemanticColors:
    """Tests for semantic color functions — Req 1.1-1.4."""

    def test_success_code_92(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            assert "\033[92m" in success("ok", stream)

    def test_error_style_code_91(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            assert "\033[91m" in error_style("err", stream)

    def test_warning_style_code_93(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            assert "\033[93m" in warning_style("warn", stream)

    def test_accent_code_96(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            assert "\033[96m" in accent("hi", stream)

    def test_info_code_94(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            assert "\033[94m" in info("note", stream)

    def test_muted_code_2(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            assert "\033[2m" in muted("faded", stream)

    def test_subtle_code_2_3(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            assert "\033[2;3m" in subtle("hint", stream)

    def test_semantic_plain_on_non_tty(self) -> None:
        stream = _make_non_tty_stream()
        assert success("ok", stream) == "ok"
        assert error_style("err", stream) == "err"
        assert accent("hi", stream) == "hi"


class TestStyleFunction:
    """Tests for style() — Req 1.2."""

    def test_combines_codes(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = style("hello", "1", "96", stream=stream)
            assert "\033[1;96m" in result
            assert "hello" in result

    def test_plain_on_non_tty(self) -> None:
        stream = _make_non_tty_stream()
        assert style("hello", "1", "96", stream=stream) == "hello"


class TestBrightDowngrade:
    """Tests for bright downgrade at color level 1 — Req 1.4."""

    def test_bright_downgraded_to_standard(self) -> None:
        stream = _make_tty_stream()
        # Level 1: TTY, no higher indicators, no 256color, no COLORTERM
        # We need to mock _color_level to return 1
        with patch("ksm.color._color_level", return_value=1):
            result = success("ok", stream)
            # 92 should become 32
            assert "\033[32m" in result
            assert "\033[92m" not in result

    def test_compound_code_downgrade(self) -> None:
        with patch("ksm.color._color_level", return_value=1):
            stream = _make_tty_stream()
            result = subtle("hint", stream)
            # 2;3 has no bright codes, should stay as-is
            assert "\033[2;3m" in result


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


# ---------------------------------------------------------------
# Legacy function backward compatibility
# ---------------------------------------------------------------


class TestLegacyFunctions:
    """Existing green/red/yellow/dim/bold remain unchanged."""

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

    def test_green_wraps_ansi_tty(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = green("ok", stream)
            assert "\033[32m" in result

    def test_red_wraps_ansi_tty(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            assert "\033[31m" in red("err", stream)

    def test_yellow_wraps_ansi_tty(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            assert "\033[33m" in yellow("warn", stream)

    def test_dim_wraps_ansi_tty(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            assert "\033[2m" in dim("faded", stream)

    def test_bold_wraps_ansi_tty(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            assert "\033[1m" in bold("strong", stream)


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
