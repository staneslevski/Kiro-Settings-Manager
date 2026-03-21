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


# ---------------------------------------------------------------
# Property 27: scope_select returns "local" when Enter pressed
#              without navigation (default selection)
# Validates: Requirements 11.2, 11.3, 12.2
# ---------------------------------------------------------------


class TestScopeSelectDefaultLocal:
    """scope_select returns 'local' when Enter pressed immediately."""

    def test_enter_without_navigation_returns_local(self) -> None:
        """Pressing Enter immediately returns 'local' (default)."""
        from ksm.selector import scope_select

        with (
            patch("ksm.selector.termios") as mock_termios,
            patch("ksm.selector.tty"),
            patch("ksm.selector.sys") as mock_sys,
            patch("ksm.selector._can_run_textual", return_value=True),
        ):
            mock_sys.stdin.fileno.return_value = 0
            mock_termios.tcgetattr.return_value = []
            mock_sys.stdin.buffer.read.return_value = b"\r"
            mock_sys.stderr = io.StringIO()

            result = scope_select()

        assert result == "local"

    def test_newline_key_returns_local(self) -> None:
        """Pressing newline (\\n) also returns 'local'."""
        from ksm.selector import scope_select

        with (
            patch("ksm.selector.termios") as mock_termios,
            patch("ksm.selector.tty"),
            patch("ksm.selector.sys") as mock_sys,
            patch("ksm.selector._can_run_textual", return_value=True),
        ):
            mock_sys.stdin.fileno.return_value = 0
            mock_termios.tcgetattr.return_value = []
            mock_sys.stdin.buffer.read.return_value = b"\n"
            mock_sys.stderr = io.StringIO()

            result = scope_select()

        assert result == "local"


# ---------------------------------------------------------------
# Property 28: scope_select returns "global" when user navigates
#              to second option and presses Enter
# Validates: Requirements 11.4, 12.1, 12.2
# ---------------------------------------------------------------


class TestScopeSelectNavigateToGlobal:
    """scope_select returns 'global' after navigating down."""

    def test_down_arrow_then_enter_returns_global(self) -> None:
        """Down arrow then Enter returns 'global'."""
        from ksm.selector import scope_select

        call_count = 0

        def fake_read(n: int) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return b"\x1b"  # Start of down arrow
            if call_count == 2:
                return b"[B"  # Rest of down arrow
            return b"\r"  # Enter

        with (
            patch("ksm.selector.termios") as mock_termios,
            patch("ksm.selector.tty"),
            patch("ksm.selector.sys") as mock_sys,
            patch("ksm.selector._can_run_textual", return_value=True),
        ):
            mock_sys.stdin.fileno.return_value = 0
            mock_termios.tcgetattr.return_value = []
            mock_sys.stdin.buffer.read.side_effect = fake_read
            mock_sys.stderr = io.StringIO()

            result = scope_select()

        assert result == "global"

    def test_down_then_up_then_enter_returns_local(self) -> None:
        """Down then up then Enter returns 'local' (back to first)."""
        from ksm.selector import scope_select

        call_count = 0

        def fake_read(n: int) -> bytes:
            nonlocal call_count
            call_count += 1
            # Down arrow: bytes 1-2
            if call_count == 1:
                return b"\x1b"
            if call_count == 2:
                return b"[B"
            # Up arrow: bytes 3-4
            if call_count == 3:
                return b"\x1b"
            if call_count == 4:
                return b"[A"
            # Enter
            return b"\r"

        with (
            patch("ksm.selector.termios") as mock_termios,
            patch("ksm.selector.tty"),
            patch("ksm.selector.sys") as mock_sys,
            patch("ksm.selector._can_run_textual", return_value=True),
        ):
            mock_sys.stdin.fileno.return_value = 0
            mock_termios.tcgetattr.return_value = []
            mock_sys.stdin.buffer.read.side_effect = fake_read
            mock_sys.stderr = io.StringIO()

            result = scope_select()

        assert result == "local"

    def test_multiple_down_clamps_at_global(self) -> None:
        """Multiple down arrows clamp at 'global' (index 1)."""
        from ksm.selector import scope_select

        call_count = 0

        def fake_read(n: int) -> bytes:
            nonlocal call_count
            call_count += 1
            # Down arrow x3 (only 2 options, should clamp)
            if call_count in (1, 3, 5):
                return b"\x1b"
            if call_count in (2, 4, 6):
                return b"[B"
            return b"\r"  # Enter

        with (
            patch("ksm.selector.termios") as mock_termios,
            patch("ksm.selector.tty"),
            patch("ksm.selector.sys") as mock_sys,
            patch("ksm.selector._can_run_textual", return_value=True),
        ):
            mock_sys.stdin.fileno.return_value = 0
            mock_termios.tcgetattr.return_value = []
            mock_sys.stdin.buffer.read.side_effect = fake_read
            mock_sys.stderr = io.StringIO()

            result = scope_select()

        assert result == "global"


# ---------------------------------------------------------------
# Property 29: scope_select returns None when user presses q
#              or Escape
# Validates: Requirements 11.6
# ---------------------------------------------------------------


class TestScopeSelectAbort:
    """scope_select returns None on q or Escape."""

    def test_q_returns_none(self) -> None:
        """Pressing q aborts and returns None."""
        from ksm.selector import scope_select

        with (
            patch("ksm.selector.termios") as mock_termios,
            patch("ksm.selector.tty"),
            patch("ksm.selector.sys") as mock_sys,
            patch("ksm.selector._can_run_textual", return_value=True),
        ):
            mock_sys.stdin.fileno.return_value = 0
            mock_termios.tcgetattr.return_value = []
            mock_sys.stdin.buffer.read.return_value = b"q"
            mock_sys.stderr = io.StringIO()

            result = scope_select()

        assert result is None

    def test_escape_returns_none(self) -> None:
        """Pressing Escape aborts and returns None."""
        from ksm.selector import scope_select

        call_count = 0

        def fake_read(n: int) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return b"\x1b"  # Escape byte
            # _read_key reads 2 more bytes for escape seq;
            # return non-bracket to signal bare Escape
            return b""

        with (
            patch("ksm.selector.termios") as mock_termios,
            patch("ksm.selector.tty"),
            patch("ksm.selector.sys") as mock_sys,
            patch("ksm.selector._can_run_textual", return_value=True),
        ):
            mock_sys.stdin.fileno.return_value = 0
            mock_termios.tcgetattr.return_value = []
            mock_sys.stdin.buffer.read.side_effect = fake_read
            mock_sys.stderr = io.StringIO()

            result = scope_select()

        assert result is None

    def test_q_after_navigation_returns_none(self) -> None:
        """Navigating down then pressing q still aborts."""
        from ksm.selector import scope_select

        call_count = 0

        def fake_read(n: int) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return b"\x1b"  # Down arrow start
            if call_count == 2:
                return b"[B"  # Down arrow end
            return b"q"  # Quit

        with (
            patch("ksm.selector.termios") as mock_termios,
            patch("ksm.selector.tty"),
            patch("ksm.selector.sys") as mock_sys,
            patch("ksm.selector._can_run_textual", return_value=True),
        ):
            mock_sys.stdin.fileno.return_value = 0
            mock_termios.tcgetattr.return_value = []
            mock_sys.stdin.buffer.read.side_effect = fake_read
            mock_sys.stderr = io.StringIO()

            result = scope_select()

        assert result is None


# ---------------------------------------------------------------
# Property 30: scope_select restores terminal settings on SIGINT
# Validates: Requirements 12.6
# ---------------------------------------------------------------


class TestScopeSelectSIGINT:
    """scope_select restores terminal on SIGINT (Ctrl+C)."""

    def test_sigint_restores_terminal_and_returns_none(
        self,
    ) -> None:
        """KeyboardInterrupt restores terminal settings."""
        from ksm.selector import scope_select

        with (
            patch("ksm.selector.termios") as mock_termios,
            patch("ksm.selector.tty"),
            patch("ksm.selector.sys") as mock_sys,
            patch("ksm.selector._can_run_textual", return_value=True),
        ):
            mock_sys.stdin.fileno.return_value = 0
            old_settings = [1, 2, 3]  # Fake saved settings
            mock_termios.tcgetattr.return_value = old_settings
            mock_termios.TCSADRAIN = 1
            mock_sys.stdin.buffer.read.side_effect = KeyboardInterrupt
            mock_sys.stderr = io.StringIO()

            result = scope_select()

        assert result is None
        # Verify terminal settings were restored
        mock_termios.tcsetattr.assert_called_with(0, 1, old_settings)

    def test_sigint_after_navigation_restores_terminal(
        self,
    ) -> None:
        """SIGINT after navigating still restores terminal."""
        from ksm.selector import scope_select

        call_count = 0

        def fake_read(n: int) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return b"\x1b"  # Down arrow start
            if call_count == 2:
                return b"[B"  # Down arrow end
            raise KeyboardInterrupt

        with (
            patch("ksm.selector.termios") as mock_termios,
            patch("ksm.selector.tty"),
            patch("ksm.selector.sys") as mock_sys,
            patch("ksm.selector._can_run_textual", return_value=True),
        ):
            mock_sys.stdin.fileno.return_value = 0
            old_settings = [4, 5, 6]
            mock_termios.tcgetattr.return_value = old_settings
            mock_termios.TCSADRAIN = 1
            mock_sys.stdin.buffer.read.side_effect = fake_read
            mock_sys.stderr = io.StringIO()

            result = scope_select()

        assert result is None
        mock_termios.tcsetattr.assert_called_with(0, 1, old_settings)


# ---------------------------------------------------------------
# Rendering tests — stderr output, inline (no alt screen buffer),
# header/instructions content
# Validates: Requirements 12.3, 12.4, 12.5
# ---------------------------------------------------------------


class TestScopeSelectRendering:
    """scope_select renders correctly to stderr."""

    def test_renders_to_stderr_not_stdout(self) -> None:
        """All output goes to stderr, nothing to stdout."""
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()
        stdout_buf = io.StringIO()

        with (
            patch("ksm.selector.termios") as mock_termios,
            patch("ksm.selector.tty"),
            patch("ksm.selector.sys") as mock_sys,
            patch("ksm.selector._can_run_textual", return_value=True),
        ):
            mock_sys.stdin.fileno.return_value = 0
            mock_termios.tcgetattr.return_value = []
            mock_sys.stdin.buffer.read.return_value = b"\r"
            mock_sys.stderr = stderr_buf
            mock_sys.stdout = stdout_buf

            scope_select()

        assert stdout_buf.getvalue() == ""
        assert len(stderr_buf.getvalue()) > 0

    def test_renders_header_text(self) -> None:
        """Output contains 'Select installation scope:' header."""
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()

        with (
            patch("ksm.selector.termios") as mock_termios,
            patch("ksm.selector.tty"),
            patch("ksm.selector.sys") as mock_sys,
            patch("ksm.selector._can_run_textual", return_value=True),
        ):
            mock_sys.stdin.fileno.return_value = 0
            mock_termios.tcgetattr.return_value = []
            mock_sys.stdin.buffer.read.return_value = b"\r"
            mock_sys.stderr = stderr_buf

            scope_select()

        output = _strip_ansi(stderr_buf.getvalue())
        assert "Select installation scope:" in output

    def test_renders_instructions(self) -> None:
        """Output contains navigation instructions."""
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()

        with (
            patch("ksm.selector.termios") as mock_termios,
            patch("ksm.selector.tty"),
            patch("ksm.selector.sys") as mock_sys,
            patch("ksm.selector._can_run_textual", return_value=True),
        ):
            mock_sys.stdin.fileno.return_value = 0
            mock_termios.tcgetattr.return_value = []
            mock_sys.stdin.buffer.read.return_value = b"\r"
            mock_sys.stderr = stderr_buf

            scope_select()

        output = _strip_ansi(stderr_buf.getvalue())
        assert "navigate" in output
        assert "Enter" in output or "select" in output
        assert "quit" in output or "q" in output

    def test_renders_both_scope_options(self) -> None:
        """Output contains both Local and Global options."""
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()

        with (
            patch("ksm.selector.termios") as mock_termios,
            patch("ksm.selector.tty"),
            patch("ksm.selector.sys") as mock_sys,
            patch("ksm.selector._can_run_textual", return_value=True),
        ):
            mock_sys.stdin.fileno.return_value = 0
            mock_termios.tcgetattr.return_value = []
            mock_sys.stdin.buffer.read.return_value = b"\r"
            mock_sys.stderr = stderr_buf

            scope_select()

        output = _strip_ansi(stderr_buf.getvalue())
        assert "Local" in output
        assert ".kiro/" in output
        assert "Global" in output
        assert "~/.kiro/" in output

    def test_no_alternate_screen_buffer(self) -> None:
        """Scope selector does NOT use alternate screen buffer.

        Req 12.5: renders inline since only 2 options.
        """
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()

        with (
            patch("ksm.selector.termios") as mock_termios,
            patch("ksm.selector.tty"),
            patch("ksm.selector.sys") as mock_sys,
            patch("ksm.selector._can_run_textual", return_value=True),
        ):
            mock_sys.stdin.fileno.return_value = 0
            mock_termios.tcgetattr.return_value = []
            mock_sys.stdin.buffer.read.return_value = b"\r"
            mock_sys.stderr = stderr_buf

            scope_select()

        output = stderr_buf.getvalue()
        assert "\033[?1049h" not in output, "Must NOT use alternate screen buffer"
        assert "\033[?1049l" not in output, "Must NOT use alternate screen buffer"

    def test_highlighted_option_has_arrow_prefix(self) -> None:
        """The highlighted option has a '>' prefix."""
        from ksm.selector import scope_select

        stderr_buf = io.StringIO()

        with (
            patch("ksm.selector.termios") as mock_termios,
            patch("ksm.selector.tty"),
            patch("ksm.selector.sys") as mock_sys,
            patch("ksm.selector._can_run_textual", return_value=True),
        ):
            mock_sys.stdin.fileno.return_value = 0
            mock_termios.tcgetattr.return_value = []
            mock_sys.stdin.buffer.read.return_value = b"\r"
            mock_sys.stderr = stderr_buf

            scope_select()

        output = _strip_ansi(stderr_buf.getvalue())
        # Default selection is Local, should have > prefix
        assert "> Local" in output or ">Local" in output


# ---------------------------------------------------------------
# Property 31: numbered-list fallback returns "local" for input
#              "1" or empty
# Validates: Requirements 13.1, 13.2
# ---------------------------------------------------------------


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
