"""Tests for enriched error classes.

Property 11: BundleNotFoundError contains name and all searched registries
Property 12: GitError contains URL and cleaned summary
"""

from io import StringIO
from unittest.mock import MagicMock, patch

from hypothesis import given
from hypothesis import strategies as st

from ksm.errors import (
    BundleNotFoundError,
    GitError,
    InvalidSubdirectoryError,
    MutualExclusionError,
    format_deprecation,
    format_error,
    format_warning,
)

# --- Property 11 ---


@given(
    bundle_name=st.text(min_size=1, max_size=50),
    registry_names=st.lists(st.text(min_size=1, max_size=30), min_size=0, max_size=10),
)
def test_bundle_not_found_contains_name_and_registries(
    bundle_name: str,
    registry_names: list[str],
) -> None:
    """Feature: ux-review-fixes, Property 11: BundleNotFoundError
    message contains name and all searched registries."""
    err = BundleNotFoundError(bundle_name, searched_registries=registry_names)
    msg = str(err)
    assert bundle_name in msg
    for reg in registry_names:
        assert reg in msg


def test_bundle_not_found_backward_compat() -> None:
    """BundleNotFoundError still works with just a name."""
    err = BundleNotFoundError("my-bundle")
    msg = str(err)
    assert "my-bundle" in msg


def test_bundle_not_found_includes_suggestions() -> None:
    """BundleNotFoundError includes actionable suggestions."""
    err = BundleNotFoundError("foo", searched_registries=["default", "my-reg"])
    msg = str(err)
    assert "foo" in msg
    assert "default" in msg
    assert "my-reg" in msg
    assert "ksm registry ls" in msg
    assert "--from" in msg
    assert "2 registries" in msg


def test_bundle_not_found_single_registry() -> None:
    """BundleNotFoundError uses singular 'registry' for one."""
    err = BundleNotFoundError("bar", searched_registries=["default"])
    msg = str(err)
    assert "1 registry" in msg


def test_bundle_not_found_empty_registries() -> None:
    """BundleNotFoundError with no registries searched."""
    err = BundleNotFoundError("bar", searched_registries=[])
    msg = str(err)
    assert "bar" in msg


def test_bundle_not_found_attrs() -> None:
    """BundleNotFoundError stores bundle_name and registries."""
    err = BundleNotFoundError("test-bundle", searched_registries=["r1", "r2"])
    assert err.bundle_name == "test-bundle"
    assert err.searched_registries == ["r1", "r2"]


# --- Property 12 ---


@given(
    url=st.from_regex(r"https://[a-z0-9.]+/[a-z0-9]+\.git", fullmatch=True),
    stderr_output=st.text(min_size=0, max_size=500),
)
def test_git_error_contains_url_and_cleaned_summary(
    url: str,
    stderr_output: str,
) -> None:
    """Feature: ux-review-fixes, Property 12: GitError message
    contains URL and cleaned single-line summary."""
    err = GitError(
        "Failed to clone repository",
        url=url,
        stderr_output=stderr_output,
    )
    msg = str(err)
    assert url in msg
    formatted = err.formatted_message()
    assert url in formatted
    for line in formatted.splitlines():
        if line.strip().startswith("Git said:"):
            git_said = line.strip()[len("Git said:") :].strip()
            assert "\n" not in git_said


def test_git_error_backward_compat() -> None:
    """GitError still works with just a message string."""
    err = GitError("something failed")
    msg = str(err)
    assert "something failed" in msg


def test_git_error_cleans_multiline_stderr() -> None:
    """GitError extracts meaningful line from multi-line stderr."""
    raw_stderr = (
        "Cloning into '/tmp/ksm-ephemeral-abc'...\n"
        "fatal: repository 'https://bad.git/' not found\n"
    )
    err = GitError(
        "Failed to clone repository",
        url="https://bad.git/",
        stderr_output=raw_stderr,
    )
    formatted = err.formatted_message()
    assert "https://bad.git/" in formatted
    assert "repository" in formatted.lower()


def test_git_error_attrs() -> None:
    """GitError stores url and stderr_output."""
    err = GitError(
        "clone failed",
        url="https://example.com/repo.git",
        stderr_output="fatal: not found",
    )
    assert err.url == "https://example.com/repo.git"
    assert err.stderr_output == "fatal: not found"


def test_git_error_suggestion() -> None:
    """GitError formatted message includes a suggestion."""
    err = GitError(
        "Failed to clone",
        url="https://example.com/repo.git",
        stderr_output="fatal: repo not found",
    )
    formatted = err.formatted_message()
    assert "url" in formatted.lower() or "access" in formatted.lower()


def test_git_error_empty_stderr() -> None:
    """GitError with empty stderr omits 'Git said' line."""
    err = GitError(
        "Failed to clone",
        url="https://example.com/repo.git",
        stderr_output="",
    )
    formatted = err.formatted_message()
    assert "Git said" not in formatted
    assert "https://example.com/repo.git" in formatted


def test_git_error_whitespace_only_stderr() -> None:
    """GitError with whitespace-only stderr omits 'Git said'."""
    err = GitError(
        "Failed to clone",
        url="https://example.com/repo.git",
        stderr_output="   \n  \n  ",
    )
    formatted = err.formatted_message()
    assert "Git said" not in formatted


def test_git_error_stderr_with_error_prefix() -> None:
    """GitError cleans stderr lines starting with 'error:'."""
    err = GitError(
        "Failed to pull",
        url="https://example.com/repo.git",
        stderr_output="error: cannot pull with rebase\n",
    )
    formatted = err.formatted_message()
    assert "cannot pull with rebase" in formatted


def test_git_error_stderr_fallback_last_line() -> None:
    """GitError falls back to last non-empty line."""
    err = GitError(
        "Failed to clone",
        url="https://example.com/repo.git",
        stderr_output="Cloning into '/tmp/foo'...\nsome other info\n",
    )
    formatted = err.formatted_message()
    assert "some other info" in formatted


def test_git_error_no_url_no_stderr() -> None:
    """GitError formatted_message works with no url or stderr."""
    err = GitError("something broke")
    formatted = err.formatted_message()
    assert "something broke" in formatted
    assert "Check that the URL" not in formatted


# --- format_error, format_warning, format_deprecation ---
# Updated for lowercase prefixes (Req 5.1-5.6)


class TestFormatError:
    """Tests for format_error helper (Req 5.1-5.6)."""

    def test_three_line_format(self) -> None:
        result = format_error(
            "Cache directory already exists",
            "Registry 'default' was previously cloned here.",
            "Use --force to replace the existing cache.",
        )
        lines = result.splitlines()
        assert len(lines) == 3

    def test_error_prefix_lowercase(self) -> None:
        result = format_error("what", "why", "fix")
        assert result.startswith("error: ")

    def test_contains_all_parts(self) -> None:
        result = format_error(
            "Clone failed",
            "The previous cache was removed.",
            "Re-add the registry.",
        )
        assert "Clone failed" in result
        assert "The previous cache was removed." in result
        assert "Re-add the registry." in result

    def test_indentation(self) -> None:
        result = format_error("what", "why", "fix")
        lines = result.splitlines()
        assert lines[1].startswith("  ")
        assert lines[2].startswith("  ")

    def test_first_line_structure(self) -> None:
        result = format_error("something broke", "reason", "action")
        first_line = result.splitlines()[0]
        assert first_line == "error: something broke"


class TestFormatWarning:
    """Tests for format_warning helper (Req 5.2)."""

    def test_two_line_format(self) -> None:
        result = format_warning(
            "Could not remove cache",
            "Permission denied.",
        )
        lines = result.splitlines()
        assert len(lines) == 2

    def test_warning_prefix_lowercase(self) -> None:
        result = format_warning("something", "detail")
        assert result.startswith("warning: ")

    def test_contains_all_parts(self) -> None:
        result = format_warning(
            "Could not remove cache",
            "Permission denied. Cache remains.",
        )
        assert "Could not remove cache" in result
        assert "Permission denied. Cache remains." in result

    def test_indentation(self) -> None:
        result = format_warning("what", "detail")
        lines = result.splitlines()
        assert lines[1].startswith("  ")

    def test_first_line_structure(self) -> None:
        result = format_warning("disk full", "detail")
        first_line = result.splitlines()[0]
        assert first_line == "warning: disk full"


class TestFormatDeprecation:
    """Tests for format_deprecation helper (Req 5.3)."""

    def test_two_line_format(self) -> None:
        result = format_deprecation(
            "--display",
            "-i/--interactive",
            "v0.2.0",
            "v1.0.0",
        )
        lines = result.splitlines()
        assert len(lines) == 2

    def test_deprecated_prefix_lowercase(self) -> None:
        result = format_deprecation("old", "new", "v0.1.0", "v0.2.0")
        assert result.startswith("deprecated: ")

    def test_contains_old_and_new(self) -> None:
        result = format_deprecation(
            "--display",
            "-i/--interactive",
            "v0.2.0",
            "v1.0.0",
        )
        assert "--display" in result
        assert "-i/--interactive" in result

    def test_contains_version_strings(self) -> None:
        result = format_deprecation(
            "ksm add-registry",
            "ksm registry add",
            "v0.2.0",
            "v1.0.0",
        )
        assert "v0.2.0" in result
        assert "v1.0.0" in result

    def test_indentation(self) -> None:
        result = format_deprecation("old", "new", "v0.1.0", "v0.2.0")
        lines = result.splitlines()
        assert lines[1].startswith("  ")

    def test_first_line_structure(self) -> None:
        result = format_deprecation(
            "--display",
            "-i/--interactive",
            "v0.2.0",
            "v1.0.0",
        )
        first_line = result.splitlines()[0]
        assert "`--display`" in first_line
        assert "`-i/--interactive`" in first_line
        assert "deprecated" in first_line.lower()


# --- Property 14: Message formatters produce correctly prefixed output ---

_single_line = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cc", "Cs", "Zl", "Zp"),
    ),
    min_size=1,
    max_size=100,
)


@given(what=_single_line, why=_single_line, fix=_single_line)
def test_format_error_property(what: str, why: str, fix: str) -> None:
    """Property 14: format_error starts with 'error: ' and has three lines."""
    result = format_error(what, why, fix)
    assert result.startswith("error: ")
    lines = result.splitlines()
    assert len(lines) == 3
    assert what in lines[0]
    assert why in lines[1]
    assert fix in lines[2]


@given(what=_single_line, detail=_single_line)
def test_format_warning_property(what: str, detail: str) -> None:
    """Property 14: format_warning starts with 'warning: ' and has two lines."""
    result = format_warning(what, detail)
    assert result.startswith("warning: ")
    lines = result.splitlines()
    assert len(lines) == 2
    assert what in lines[0]
    assert detail in lines[1]


@given(
    old=_single_line,
    new=_single_line,
    since=st.from_regex(r"v[0-9]+\.[0-9]+\.[0-9]+", fullmatch=True),
    removal=st.from_regex(r"v[0-9]+\.[0-9]+\.[0-9]+", fullmatch=True),
)
def test_format_deprecation_property(
    old: str, new: str, since: str, removal: str
) -> None:
    """Property 14: format_deprecation starts with 'deprecated: '."""
    result = format_deprecation(old, new, since, removal)
    assert result.startswith("deprecated: ")
    lines = result.splitlines()
    assert len(lines) == 2
    assert since in result
    assert removal in result


# ------------------------------------------------------------------
# Colorized formatter tests — stream parameter
# ------------------------------------------------------------------


def _make_tty_stream() -> MagicMock:
    stream = MagicMock(spec=StringIO)
    stream.isatty.return_value = True
    return stream


def _make_non_tty_stream() -> StringIO:
    return StringIO()


def _clean_env() -> dict[str, str]:
    return {"TERM": "xterm-256color"}


# ANSI escape code constants (updated for semantic colors)
_ERROR_STYLE = "\033[91m"  # bright red
_WARNING_STYLE = "\033[93m"  # bright yellow
_MUTED = "\033[2m"  # dim
_SUBTLE = "\033[2;3m"  # dim italic
_RESET = "\033[0m"


class TestFormatErrorColor:
    """Validates: Req 5.1, 5.4, 5.5."""

    def test_error_prefix_styled_on_tty(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = format_error("what", "why", "fix", stream=stream)
        assert f"{_ERROR_STYLE}error:{_RESET}" in result

    def test_why_line_muted(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = format_error("what", "why", "fix", stream=stream)
        assert f"{_MUTED}why{_RESET}" in result

    def test_fix_line_subtle(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = format_error("what", "why", "fix", stream=stream)
        assert f"{_SUBTLE}fix{_RESET}" in result


class TestFormatWarningColor:
    """Validates: Req 5.2."""

    def test_warning_prefix_styled_on_tty(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = format_warning("something", "detail", stream=stream)
        assert f"{_WARNING_STYLE}warning:{_RESET}" in result

    def test_detail_muted(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = format_warning("what", "detail", stream=stream)
        assert f"{_MUTED}detail{_RESET}" in result


class TestFormatDeprecationColor:
    """Validates: Req 5.3."""

    def test_deprecation_prefix_styled_on_tty(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = format_deprecation("old", "new", "v0.1.0", "v0.2.0", stream=stream)
        assert f"{_WARNING_STYLE}deprecated:{_RESET}" in result

    def test_timeline_subtle(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = format_deprecation("old", "new", "v0.1.0", "v0.2.0", stream=stream)
        assert _SUBTLE in result
        assert "v0.1.0" in result


class TestFormattersNoColor:
    """Validates: plain text when NO_COLOR set."""

    def test_error_plain_when_no_color(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            result = format_error("what", "why", "fix", stream=stream)
        assert "\033[" not in result
        assert result.startswith("error: ")

    def test_warning_plain_when_no_color(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            result = format_warning("what", "detail", stream=stream)
        assert "\033[" not in result
        assert result.startswith("warning: ")

    def test_deprecation_plain_when_no_color(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            result = format_deprecation("old", "new", "v0.1.0", "v0.2.0", stream=stream)
        assert "\033[" not in result
        assert result.startswith("deprecated: ")


class TestFormattersNonTTY:
    """Validates: plain text on non-TTY."""

    def test_error_plain_when_non_tty(self) -> None:
        stream = _make_non_tty_stream()
        result = format_error("what", "why", "fix", stream=stream)
        assert "\033[" not in result
        assert result.startswith("error: ")

    def test_warning_plain_when_non_tty(self) -> None:
        stream = _make_non_tty_stream()
        result = format_warning("what", "detail", stream=stream)
        assert "\033[" not in result
        assert result.startswith("warning: ")

    def test_deprecation_plain_when_non_tty(self) -> None:
        stream = _make_non_tty_stream()
        result = format_deprecation("old", "new", "v0.1.0", "v0.2.0", stream=stream)
        assert "\033[" not in result
        assert result.startswith("deprecated: ")


class TestFormattersPreserveStructure:
    """Validates: structure preserved with stream."""

    def test_error_three_lines_with_stream(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = format_error("what", "why", "fix", stream=stream)
        lines = result.splitlines()
        assert len(lines) == 3
        assert "what" in lines[0]
        assert "why" in lines[1]
        assert "fix" in lines[2]

    def test_warning_two_lines_with_stream(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = format_warning("what", "detail", stream=stream)
        lines = result.splitlines()
        assert len(lines) == 2

    def test_deprecation_two_lines_with_stream(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = format_deprecation("old", "new", "v0.1.0", "v0.2.0", stream=stream)
        lines = result.splitlines()
        assert len(lines) == 2

    def test_error_indentation_preserved(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = format_error("what", "why", "fix", stream=stream)
        lines = result.splitlines()
        assert lines[1].startswith("  ")
        assert lines[2].startswith("  ")

    def test_warning_indentation_preserved(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = format_warning("what", "detail", stream=stream)
        lines = result.splitlines()
        assert lines[1].startswith("  ")

    def test_deprecation_indentation_preserved(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            result = format_deprecation("old", "new", "v0.1.0", "v0.2.0", stream=stream)
        lines = result.splitlines()
        assert lines[1].startswith("  ")


class TestFormatterTermDumb:
    """Validates: plain text on TERM=dumb."""

    def test_error_plain_when_term_dumb(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"TERM": "dumb"}, clear=True):
            result = format_error("what", "why", "fix", stream=stream)
        assert "\033[" not in result
        assert result.startswith("error: ")

    def test_warning_plain_when_term_dumb(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"TERM": "dumb"}, clear=True):
            result = format_warning("what", "detail", stream=stream)
        assert "\033[" not in result
        assert result.startswith("warning: ")

    def test_deprecation_plain_when_term_dumb(self) -> None:
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"TERM": "dumb"}, clear=True):
            result = format_deprecation("old", "new", "v0.1.0", "v0.2.0", stream=stream)
        assert "\033[" not in result
        assert result.startswith("deprecated: ")


# --- Property-based tests for colorized formatters ---


class TestBundleNameAccent:
    """Tests for bundle name accent styling — Req 5.6."""

    _ACCENT = "\033[96m"
    _RESET = "\033[0m"

    def test_accent_styled_name_preserved_in_what(self) -> None:
        """Pre-styled accent bundle name appears in output."""
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            from ksm.color import accent as _accent

            styled_name = _accent("my-bundle", stream=stream)
            result = format_error(
                f"Bundle {styled_name} not found",
                "Check the registry.",
                "Run ksm search.",
                stream=stream,
            )
        assert self._ACCENT in result
        assert "my-bundle" in result

    def test_accent_code_present_for_bundle_name(self) -> None:
        """Accent ANSI code wraps the bundle name."""
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            from ksm.color import accent as _accent

            styled = _accent("test-bundle", stream=stream)
            result = format_error(
                f"{styled} is broken",
                "reason",
                "fix it",
                stream=stream,
            )
        assert f"{self._ACCENT}test-bundle{self._RESET}" in result

    def test_accent_absent_on_non_tty(self) -> None:
        """No accent ANSI on non-TTY stream."""
        stream = _make_non_tty_stream()
        from ksm.color import accent as _accent

        styled = _accent("my-bundle", stream=stream)
        result = format_error(
            f"Bundle {styled} not found",
            "why",
            "fix",
            stream=stream,
        )
        assert "\033[96m" not in result
        assert "my-bundle" in result

    def test_accent_absent_when_no_color(self) -> None:
        """No accent ANSI when NO_COLOR is set."""
        stream = _make_tty_stream()
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            from ksm.color import accent as _accent

            styled = _accent("pkg", stream=stream)
            result = format_error(
                f"Bundle {styled} missing",
                "why",
                "fix",
                stream=stream,
            )
        assert "\033[96m" not in result
        assert "pkg" in result

    def test_multiple_accent_names_preserved(self) -> None:
        """Multiple accent-styled names in what are preserved."""
        stream = _make_tty_stream()
        with patch.dict("os.environ", _clean_env(), clear=True):
            from ksm.color import accent as _accent

            a = _accent("bundle-a", stream=stream)
            b = _accent("bundle-b", stream=stream)
            result = format_error(
                f"{a} conflicts with {b}",
                "why",
                "fix",
                stream=stream,
            )
        assert "bundle-a" in result
        assert "bundle-b" in result
        # Both should have accent codes
        count = result.count(self._ACCENT)
        assert count >= 2


# --- Property-based tests for colorized formatters ---


@given(what=_single_line, why=_single_line, fix=_single_line)
def test_format_error_color_property(what: str, why: str, fix: str) -> None:
    """Property 1 (PBT): format_error wraps 'error:' in error_style on TTY."""
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        result = format_error(what, why, fix, stream=stream)
    assert _ERROR_STYLE in result
    assert _RESET in result
    assert what in result
    assert why in result
    assert fix in result
    lines = result.splitlines()
    assert len(lines) == 3


@given(what=_single_line, detail=_single_line)
def test_format_warning_color_property(what: str, detail: str) -> None:
    """Property 2 (PBT): format_warning wraps 'warning:' in warning_style."""
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        result = format_warning(what, detail, stream=stream)
    assert _WARNING_STYLE in result
    assert _RESET in result
    assert what in result
    assert detail in result
    lines = result.splitlines()
    assert len(lines) == 2


@given(
    old=_single_line,
    new=_single_line,
    since=st.from_regex(r"v[0-9]+\.[0-9]+\.[0-9]+", fullmatch=True),
    removal=st.from_regex(r"v[0-9]+\.[0-9]+\.[0-9]+", fullmatch=True),
)
def test_format_deprecation_color_property(
    old: str, new: str, since: str, removal: str
) -> None:
    """Property 3 (PBT): format_deprecation wraps 'deprecated:' in warning_style."""
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        result = format_deprecation(old, new, since, removal, stream=stream)
    assert _WARNING_STYLE in result
    assert _RESET in result
    assert since in result
    assert removal in result
    lines = result.splitlines()
    assert len(lines) == 2


@given(what=_single_line, why=_single_line, fix=_single_line)
def test_format_error_no_color_property(what: str, why: str, fix: str) -> None:
    """Property 4 (PBT): format_error returns plain text when NO_COLOR set."""
    stream = _make_tty_stream()
    with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
        result = format_error(what, why, fix, stream=stream)
    assert "\033[" not in result
    assert what in result


@given(what=_single_line, detail=_single_line)
def test_format_warning_no_color_property(what: str, detail: str) -> None:
    """Property 4 (PBT): format_warning returns plain text when NO_COLOR set."""
    stream = _make_tty_stream()
    with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
        result = format_warning(what, detail, stream=stream)
    assert "\033[" not in result
    assert what in result


@given(what=_single_line, why=_single_line, fix=_single_line)
def test_format_error_non_tty_property(what: str, why: str, fix: str) -> None:
    """Property 5 (PBT): format_error returns plain text on non-TTY."""
    stream = _make_non_tty_stream()
    result = format_error(what, why, fix, stream=stream)
    assert "\033[" not in result
    assert what in result
    assert result.splitlines()[0].startswith("error: ")


@given(what=_single_line, detail=_single_line)
def test_format_warning_non_tty_property(what: str, detail: str) -> None:
    """Property 5 (PBT): format_warning returns plain text on non-TTY."""
    stream = _make_non_tty_stream()
    result = format_warning(what, detail, stream=stream)
    assert "\033[" not in result
    assert what in result
    assert result.splitlines()[0].startswith("warning: ")


# --- Property 7: Error/warning/deprecation prefixes and styles ---
# Feature: ux-visual-overhaul, Property 7: Error/warning/deprecation
# uses correct prefixes and semantic styles
# **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**


@given(what=_single_line, why=_single_line, fix=_single_line)
def test_format_error_semantic_styles_property(what: str, why: str, fix: str) -> None:
    """Feature: ux-visual-overhaul, Property 7:
    format_error uses error_style prefix, muted why,
    subtle fix on TTY."""
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        result = format_error(what, why, fix, stream=stream)
    lines = result.splitlines()
    assert len(lines) == 3
    # Line 0: error_style prefix wrapping "error:"
    assert f"{_ERROR_STYLE}error:{_RESET}" in lines[0]
    assert what in lines[0]
    # Line 1: why wrapped in muted
    assert f"{_MUTED}{why}{_RESET}" in lines[1]
    # Line 2: fix wrapped in subtle
    assert f"{_SUBTLE}{fix}{_RESET}" in lines[2]


@given(what=_single_line, detail=_single_line)
def test_format_warning_semantic_styles_property(what: str, detail: str) -> None:
    """Feature: ux-visual-overhaul, Property 7:
    format_warning uses warning_style prefix, muted detail
    on TTY."""
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        result = format_warning(what, detail, stream=stream)
    lines = result.splitlines()
    assert len(lines) == 2
    # Line 0: warning_style prefix wrapping "warning:"
    assert f"{_WARNING_STYLE}warning:{_RESET}" in lines[0]
    assert what in lines[0]
    # Line 1: detail wrapped in muted
    assert f"{_MUTED}{detail}{_RESET}" in lines[1]


@given(
    old=_single_line,
    new=_single_line,
    since=st.from_regex(r"v[0-9]+\.[0-9]+\.[0-9]+", fullmatch=True),
    removal=st.from_regex(r"v[0-9]+\.[0-9]+\.[0-9]+", fullmatch=True),
)
def test_format_deprecation_semantic_styles_property(
    old: str, new: str, since: str, removal: str
) -> None:
    """Feature: ux-visual-overhaul, Property 7:
    format_deprecation uses warning_style prefix, subtle
    timeline on TTY."""
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        result = format_deprecation(old, new, since, removal, stream=stream)
    lines = result.splitlines()
    assert len(lines) == 2
    # Line 0: warning_style prefix wrapping "deprecated:"
    assert f"{_WARNING_STYLE}deprecated:{_RESET}" in lines[0]
    # Line 1: timeline wrapped in subtle
    assert _SUBTLE in lines[1]
    assert since in lines[1]
    assert removal in lines[1]


# --- Property 8: Error messages style bundle names with accent ---
# Feature: ux-visual-overhaul, Property 8: Error messages style
# bundle names with accent
# **Validates: Requirements 5.6**

_ACCENT = "\033[96m"

_bundle_name_st = st.from_regex(r"[a-z][a-z0-9\-]{0,29}", fullmatch=True)


@given(bundle_name=_bundle_name_st)
def test_error_bundle_name_accent_property(
    bundle_name: str,
) -> None:
    """Feature: ux-visual-overhaul, Property 8:
    Bundle names in error what are styled with accent."""
    stream = _make_tty_stream()
    with patch.dict("os.environ", _clean_env(), clear=True):
        from ksm.color import accent as _accent_fn

        styled = _accent_fn(bundle_name, stream=stream)
        result = format_error(
            f"Bundle {styled} not found",
            "Check the registry.",
            "Run ksm search.",
            stream=stream,
        )
    # The accent code must wrap the bundle name
    assert f"{_ACCENT}{bundle_name}{_RESET}" in result
    # The bundle name must appear on the first line
    assert bundle_name in result.splitlines()[0]


# --- InvalidSubdirectoryError ---


def test_invalid_subdirectory_error_message() -> None:
    """InvalidSubdirectoryError includes subdirectory and valid types."""
    err = InvalidSubdirectoryError("bad", ["skills", "steering"])
    msg = str(err)
    assert "bad" in msg
    assert "skills" in msg
    assert "steering" in msg


def test_invalid_subdirectory_error_attrs() -> None:
    """InvalidSubdirectoryError stores subdirectory and valid list."""
    err = InvalidSubdirectoryError("hooks", ["skills", "steering"])
    assert err.subdirectory == "hooks"
    assert err.valid == ["skills", "steering"]


# --- MutualExclusionError ---


def test_mutual_exclusion_error_message() -> None:
    """MutualExclusionError includes both option names."""
    err = MutualExclusionError("--force", "--dry-run")
    msg = str(err)
    assert "--force" in msg
    assert "--dry-run" in msg
    assert "mutually exclusive" in msg


def test_mutual_exclusion_error_attrs() -> None:
    """MutualExclusionError stores option_a and option_b."""
    err = MutualExclusionError("--local", "--global")
    assert err.option_a == "--local"
    assert err.option_b == "--global"
