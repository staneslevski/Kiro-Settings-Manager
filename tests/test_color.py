"""Tests for ksm.color module."""

from io import StringIO
from unittest.mock import MagicMock, patch

from ksm.color import (
    _color_enabled,
    bold,
    dim,
    green,
    red,
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


def test_color_disabled_no_color_env() -> None:
    """Color disabled when NO_COLOR is set."""
    with patch.dict("os.environ", {"NO_COLOR": "1"}):
        assert not _color_enabled()


def test_color_disabled_term_dumb() -> None:
    """Color disabled when TERM=dumb."""
    with patch.dict("os.environ", {"TERM": "dumb"}, clear=True):
        assert not _color_enabled()


def test_color_disabled_non_tty() -> None:
    """Color disabled for non-TTY stream."""
    stream = _make_non_tty_stream()
    assert not _color_enabled(stream)


def test_color_enabled_tty() -> None:
    """Color enabled for TTY stream without NO_COLOR."""
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        assert _color_enabled(stream)


def test_green_returns_plain_non_tty() -> None:
    """green() returns plain text for non-TTY."""
    stream = _make_non_tty_stream()
    assert green("hello", stream) == "hello"


def test_red_returns_plain_non_tty() -> None:
    """red() returns plain text for non-TTY."""
    stream = _make_non_tty_stream()
    assert red("hello", stream) == "hello"


def test_yellow_returns_plain_non_tty() -> None:
    """yellow() returns plain text for non-TTY."""
    stream = _make_non_tty_stream()
    assert yellow("hello", stream) == "hello"


def test_dim_returns_plain_non_tty() -> None:
    """dim() returns plain text for non-TTY."""
    stream = _make_non_tty_stream()
    assert dim("hello", stream) == "hello"


def test_bold_returns_plain_non_tty() -> None:
    """bold() returns plain text for non-TTY."""
    stream = _make_non_tty_stream()
    assert bold("hello", stream) == "hello"


def test_green_wraps_ansi_tty() -> None:
    """green() wraps with ANSI when TTY."""
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        result = green("ok", stream)
        assert "\033[32m" in result
        assert "ok" in result
        assert "\033[0m" in result


def test_red_wraps_ansi_tty() -> None:
    """red() wraps with ANSI when TTY."""
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        result = red("err", stream)
        assert "\033[31m" in result


def test_yellow_wraps_ansi_tty() -> None:
    """yellow() wraps with ANSI when TTY."""
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        result = yellow("warn", stream)
        assert "\033[33m" in result


def test_dim_wraps_ansi_tty() -> None:
    """dim() wraps with ANSI when TTY."""
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        result = dim("faded", stream)
        assert "\033[2m" in result


def test_bold_wraps_ansi_tty() -> None:
    """bold() wraps with ANSI when TTY."""
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        result = bold("strong", stream)
        assert "\033[1m" in result


def test_color_no_isatty_attribute() -> None:
    """Color disabled when stream has no isatty attribute."""

    class NoIsatty:
        pass

    result = _color_enabled(NoIsatty())  # type: ignore[arg-type]
    assert not result
