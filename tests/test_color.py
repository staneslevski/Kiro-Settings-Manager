"""Tests for ksm.color module.

Property-based tests validating color output behavior
under various terminal/environment conditions.
"""

import io

from hypothesis import given
from hypothesis import strategies as st

from ksm.color import (
    _color_enabled_for_stream,
    bold,
    dim,
    green,
    red,
    yellow,
)

COLOR_FUNCS = [green, red, yellow, dim, bold]


class _FakeTTY(io.StringIO):
    """StringIO that reports as a TTY."""

    def isatty(self) -> bool:
        return True


class _FakeNonTTY(io.StringIO):
    """StringIO that reports as not a TTY."""

    def isatty(self) -> bool:
        return False


# ------------------------------------------------------------------
# Property 13: Color disabled returns plain text
# ------------------------------------------------------------------


@given(text=st.text())
def test_color_disabled_no_color_env(text: str) -> None:
    """Property 13: Color disabled returns plain text (NO_COLOR)."""
    import pytest

    mp = pytest.MonkeyPatch()
    mp.setenv("NO_COLOR", "1")
    try:
        stream = _FakeTTY()
        for fn in COLOR_FUNCS:
            assert fn(text, stream=stream) == text
    finally:
        mp.undo()


@given(text=st.text())
def test_color_disabled_non_tty(text: str) -> None:
    """Property 13: Color disabled returns plain text (non-TTY)."""
    stream = _FakeNonTTY()
    for fn in COLOR_FUNCS:
        assert fn(text, stream=stream) == text


@given(text=st.text())
def test_color_disabled_term_dumb(text: str) -> None:
    """Property 13: Color disabled returns plain text (TERM=dumb)."""
    import pytest

    mp = pytest.MonkeyPatch()
    mp.setenv("TERM", "dumb")
    mp.delenv("NO_COLOR", raising=False)
    try:
        stream = _FakeTTY()
        for fn in COLOR_FUNCS:
            assert fn(text, stream=stream) == text
    finally:
        mp.undo()


# ------------------------------------------------------------------
# Property 14: Color enabled wraps with ANSI codes
# ------------------------------------------------------------------


@given(text=st.text(min_size=1))
def test_color_enabled_wraps_ansi(text: str) -> None:
    """Property 14: Color enabled wraps with ANSI codes."""
    import pytest

    mp = pytest.MonkeyPatch()
    mp.delenv("NO_COLOR", raising=False)
    mp.delenv("TERM", raising=False)
    try:
        stream = _FakeTTY()
        for fn in COLOR_FUNCS:
            result = fn(text, stream=stream)
            assert result.startswith("\033[")
            assert result.endswith("\033[0m")
            assert text in result
    finally:
        mp.undo()


# ------------------------------------------------------------------
# Property 14b: Color checks correct stream TTY status
# ------------------------------------------------------------------


@given(text=st.text(min_size=1))
def test_color_checks_stream_tty(text: str) -> None:
    """Property 14b: Color checks correct stream TTY status."""
    import pytest

    mp = pytest.MonkeyPatch()
    mp.delenv("NO_COLOR", raising=False)
    mp.delenv("TERM", raising=False)
    try:
        tty_stream = _FakeTTY()
        non_tty_stream = _FakeNonTTY()

        # TTY stream should get ANSI codes
        for fn in COLOR_FUNCS:
            result = fn(text, stream=tty_stream)
            assert "\033[" in result

        # Non-TTY stream should get plain text
        for fn in COLOR_FUNCS:
            result = fn(text, stream=non_tty_stream)
            assert result == text
    finally:
        mp.undo()


# ------------------------------------------------------------------
# _color_enabled_for_stream edge cases
# ------------------------------------------------------------------


def test_color_enabled_no_isatty() -> None:
    """Stream without isatty attribute returns False."""
    obj = object()
    assert _color_enabled_for_stream(obj) is False  # type: ignore[arg-type]


# ------------------------------------------------------------------
# Coverage: _color_enabled(), _color_enabled_stderr(), _wrap no-stream
# ------------------------------------------------------------------


def test_color_enabled_delegates_to_stdout() -> None:
    """_color_enabled() checks sys.stdout TTY status."""
    import sys

    import pytest

    from ksm.color import _color_enabled

    mp = pytest.MonkeyPatch()
    mp.delenv("NO_COLOR", raising=False)
    mp.delenv("TERM", raising=False)
    fake = _FakeTTY()
    mp.setattr(sys, "stdout", fake)
    try:
        assert _color_enabled() is True
    finally:
        mp.undo()


def test_color_enabled_stderr_delegates() -> None:
    """_color_enabled_stderr() checks sys.stderr TTY status."""
    import sys

    import pytest

    from ksm.color import _color_enabled_stderr

    mp = pytest.MonkeyPatch()
    mp.delenv("NO_COLOR", raising=False)
    mp.delenv("TERM", raising=False)
    fake = _FakeTTY()
    mp.setattr(sys, "stderr", fake)
    try:
        assert _color_enabled_stderr() is True
    finally:
        mp.undo()


def test_wrap_no_stream_uses_stdout() -> None:
    """_wrap with no stream argument falls back to _color_enabled()."""
    import sys

    import pytest

    mp = pytest.MonkeyPatch()
    mp.delenv("NO_COLOR", raising=False)
    mp.delenv("TERM", raising=False)
    fake = _FakeTTY()
    mp.setattr(sys, "stdout", fake)
    try:
        result = green("hello")
        assert result.startswith("\033[")
        assert "hello" in result
    finally:
        mp.undo()
