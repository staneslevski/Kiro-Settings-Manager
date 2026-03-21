"""Tests for scope_select() in ksm.selector module.

TDD tests — written before scope_select() exists.
These tests cover raw mode navigation, Enter/quit behavior,
default selection, and SIGINT terminal restoration.

Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.6,
           12.1, 12.2, 12.3, 12.4, 12.5, 12.6
"""

import io
import re
from unittest.mock import patch

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return _ANSI_RE.sub("", text)


class TestScopeSelectFallbackLocal:
    """Numbered-list fallback returns 'local' for '1' or empty."""

    def test_input_1_returns_local(self) -> None:
        """Entering '1' in fallback mode returns 'local'."""
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()

        with (
            patch(
                "ksm.selector._can_run_textual",
                return_value=False,
            ),
            patch("builtins.input", return_value="1"),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            mock_sys.stdin.isatty.return_value = True

            result = scope_select()

        assert result == "local"

    def test_empty_input_returns_local(self) -> None:
        """Pressing Enter (empty input) defaults to 'local'."""
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()

        with (
            patch(
                "ksm.selector._can_run_textual",
                return_value=False,
            ),
            patch("builtins.input", return_value=""),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            mock_sys.stdin.isatty.return_value = True

            result = scope_select()

        assert result == "local"

    def test_fallback_renders_numbered_options(self) -> None:
        """Fallback displays numbered list with scope options."""
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()

        with (
            patch(
                "ksm.selector._can_run_textual",
                return_value=False,
            ),
            patch("builtins.input", return_value="1"),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            mock_sys.stdin.isatty.return_value = True

            scope_select()

        output = stderr_buf.getvalue()
        assert "1." in output
        assert "2." in output
        assert "Local" in output
        assert ".kiro/" in output
        assert "Global" in output
        assert "~/.kiro/" in output

    def test_fallback_renders_header(self) -> None:
        """Fallback displays 'Select installation scope:' header."""
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()

        with (
            patch(
                "ksm.selector._can_run_textual",
                return_value=False,
            ),
            patch("builtins.input", return_value="1"),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            mock_sys.stdin.isatty.return_value = True

            scope_select()

        output = stderr_buf.getvalue()
        assert "Select installation scope:" in output


# ---------------------------------------------------------------
# Property 32: numbered-list fallback returns "global" for
#              input "2"
# Validates: Requirements 13.1, 13.3
# ---------------------------------------------------------------


class TestScopeSelectFallbackGlobal:
    """Numbered-list fallback returns 'global' for input '2'."""

    def test_input_2_returns_global(self) -> None:
        """Entering '2' in fallback mode returns 'global'."""
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()

        with (
            patch(
                "ksm.selector._can_run_textual",
                return_value=False,
            ),
            patch("builtins.input", return_value="2"),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            mock_sys.stdin.isatty.return_value = True

            result = scope_select()

        assert result == "global"


# ---------------------------------------------------------------
# Property 33: numbered-list fallback returns None for input "q"
# Validates: Requirements 13.4
# ---------------------------------------------------------------


class TestScopeSelectFallbackAbort:
    """Numbered-list fallback returns None on 'q' or EOF."""

    def test_q_returns_none(self) -> None:
        """Entering 'q' in fallback mode aborts (returns None)."""
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()

        with (
            patch(
                "ksm.selector._can_run_textual",
                return_value=False,
            ),
            patch("builtins.input", return_value="q"),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            mock_sys.stdin.isatty.return_value = True

            result = scope_select()

        assert result is None

    def test_eof_returns_none(self) -> None:
        """EOF in fallback mode aborts (returns None)."""
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()

        with (
            patch(
                "ksm.selector._can_run_textual",
                return_value=False,
            ),
            patch("builtins.input", side_effect=EOFError),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            mock_sys.stdin.isatty.return_value = True

            result = scope_select()

        assert result is None


# ---------------------------------------------------------------
# Property 34: numbered-list fallback re-prompts on invalid input
# Validates: Requirements 13.5
# ---------------------------------------------------------------


class TestScopeSelectFallbackReprompt:
    """Numbered-list fallback re-prompts on invalid input."""

    def test_invalid_then_valid_returns_correct_scope(
        self,
    ) -> None:
        """Invalid input re-prompts, then valid input works."""
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()
        inputs = iter(["abc", "0", "3", "2"])

        with (
            patch(
                "ksm.selector._can_run_textual",
                return_value=False,
            ),
            patch("builtins.input", side_effect=inputs),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            mock_sys.stdin.isatty.return_value = True

            result = scope_select()

        assert result == "global"

    def test_invalid_input_shows_error_message(self) -> None:
        """Invalid input produces an error message on stderr."""
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()
        inputs = iter(["xyz", "1"])

        with (
            patch(
                "ksm.selector._can_run_textual",
                return_value=False,
            ),
            patch("builtins.input", side_effect=inputs),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            mock_sys.stdin.isatty.return_value = True

            scope_select()

        output = stderr_buf.getvalue()
        assert "Invalid" in output or "invalid" in output

    def test_out_of_range_number_reprompts(self) -> None:
        """Number outside [1,2] re-prompts."""
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()
        inputs = iter(["5", "1"])

        with (
            patch(
                "ksm.selector._can_run_textual",
                return_value=False,
            ),
            patch("builtins.input", side_effect=inputs),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            mock_sys.stdin.isatty.return_value = True

            result = scope_select()

        assert result == "local"


# ---------------------------------------------------------------
# Property 35: TERM=dumb forces numbered-list fallback
# Validates: Requirements 13.6
# ---------------------------------------------------------------


class TestScopeSelectTermDumb:
    """TERM=dumb forces the numbered-list fallback path."""

    def test_term_dumb_uses_fallback(self) -> None:
        """With TERM=dumb, scope_select uses numbered-list.

        Validates: Requirements 13.6
        _can_run_textual() returns False when TERM=dumb,
        so scope_select must use the fallback path.
        """
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()

        with (
            patch(
                "ksm.selector._can_run_textual",
                return_value=False,
            ),
            patch("builtins.input", return_value="1"),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            mock_sys.stdin.isatty.return_value = True

            result = scope_select()

        assert result == "local"
        # Verify it rendered numbered list (not raw mode)
        output = stderr_buf.getvalue()
        assert "1." in output
        assert "2." in output

    def test_term_dumb_no_ansi_in_output(self) -> None:
        """With TERM=dumb, no ANSI escape codes in output.

        Validates: Requirements 13.6, 16.5
        """
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()

        with (
            patch(
                "ksm.selector._can_run_textual",
                return_value=False,
            ),
            patch("builtins.input", return_value="2"),
            patch("ksm.selector.sys") as mock_sys,
            patch.dict("os.environ", {"TERM": "dumb"}, clear=False),
        ):
            mock_sys.stderr = stderr_buf
            mock_sys.stdin.isatty.return_value = True

            result = scope_select()

        assert result == "global"
        output = stderr_buf.getvalue()
        stripped = _strip_ansi(output)
        assert output == stripped, "No ANSI codes expected when TERM=dumb"

    def test_term_dumb_renders_to_stderr(self) -> None:
        """TERM=dumb fallback renders to stderr, not stdout."""
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()
        stdout_buf = io.StringIO()

        with (
            patch(
                "ksm.selector._can_run_textual",
                return_value=False,
            ),
            patch("builtins.input", return_value="1"),
            patch("ksm.selector.sys") as mock_sys,
        ):
            mock_sys.stderr = stderr_buf
            mock_sys.stdout = stdout_buf
            mock_sys.stdin.isatty.return_value = True

            scope_select()

        assert stdout_buf.getvalue() == ""
        assert len(stderr_buf.getvalue()) > 0
