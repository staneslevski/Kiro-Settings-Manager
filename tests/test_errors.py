"""Tests for enriched error classes.

Property 11: BundleNotFoundError contains name and all searched registries
Property 12: GitError contains URL and cleaned summary
"""

from hypothesis import given
from hypothesis import strategies as st

from ksm.errors import (
    BundleNotFoundError,
    GitError,
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
    # Formatted message should contain URL and a single-line
    # git summary (not the raw multi-line stderr)
    formatted = err.formatted_message()
    assert url in formatted
    # The "Git said:" line should be a single line
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
    # No URL suggestion when no URL was provided
    assert "Check that the URL" not in formatted


# --- format_error, format_warning, format_deprecation (Req 13) ---


class TestFormatError:
    """Tests for format_error helper (Req 13.1, 13.2, 13.3)."""

    def test_three_line_format(self) -> None:
        """format_error produces exactly three lines."""
        result = format_error(
            "Cache directory already exists",
            "Registry 'default' was previously cloned here.",
            "Use --force to replace the existing cache.",
        )
        lines = result.splitlines()
        assert len(lines) == 3

    def test_error_prefix(self) -> None:
        """format_error output starts with 'Error: '."""
        result = format_error("what", "why", "fix")
        assert result.startswith("Error: ")

    def test_contains_all_parts(self) -> None:
        """format_error includes what, why, and fix."""
        result = format_error(
            "Clone failed",
            "The previous cache was removed.",
            "Re-add the registry.",
        )
        assert "Clone failed" in result
        assert "The previous cache was removed." in result
        assert "Re-add the registry." in result

    def test_indentation(self) -> None:
        """Lines 2 and 3 are indented with two spaces."""
        result = format_error("what", "why", "fix")
        lines = result.splitlines()
        assert lines[1].startswith("  ")
        assert lines[2].startswith("  ")

    def test_first_line_structure(self) -> None:
        """First line is 'Error: {what}'."""
        result = format_error("something broke", "reason", "action")
        first_line = result.splitlines()[0]
        assert first_line == "Error: something broke"


class TestFormatWarning:
    """Tests for format_warning helper (Req 13.4)."""

    def test_two_line_format(self) -> None:
        """format_warning produces exactly two lines."""
        result = format_warning(
            "Could not remove cache",
            "Permission denied.",
        )
        lines = result.splitlines()
        assert len(lines) == 2

    def test_warning_prefix(self) -> None:
        """format_warning output starts with 'Warning: '."""
        result = format_warning("something", "detail")
        assert result.startswith("Warning: ")

    def test_contains_all_parts(self) -> None:
        """format_warning includes what and detail."""
        result = format_warning(
            "Could not remove cache",
            "Permission denied. Cache remains.",
        )
        assert "Could not remove cache" in result
        assert "Permission denied. Cache remains." in result

    def test_indentation(self) -> None:
        """Second line is indented with two spaces."""
        result = format_warning("what", "detail")
        lines = result.splitlines()
        assert lines[1].startswith("  ")

    def test_first_line_structure(self) -> None:
        """First line is 'Warning: {what}'."""
        result = format_warning("disk full", "detail")
        first_line = result.splitlines()[0]
        assert first_line == "Warning: disk full"


class TestFormatDeprecation:
    """Tests for format_deprecation helper (Req 13.5)."""

    def test_two_line_format(self) -> None:
        """format_deprecation produces exactly two lines."""
        result = format_deprecation(
            "--display",
            "-i/--interactive",
            "v0.2.0",
            "v1.0.0",
        )
        lines = result.splitlines()
        assert len(lines) == 2

    def test_deprecated_prefix(self) -> None:
        """format_deprecation starts with 'Deprecated: '."""
        result = format_deprecation("old", "new", "v0.1.0", "v0.2.0")
        assert result.startswith("Deprecated: ")

    def test_contains_old_and_new(self) -> None:
        """format_deprecation mentions old and new names."""
        result = format_deprecation(
            "--display",
            "-i/--interactive",
            "v0.2.0",
            "v1.0.0",
        )
        assert "--display" in result
        assert "-i/--interactive" in result

    def test_contains_version_strings(self) -> None:
        """format_deprecation includes since and removal versions."""
        result = format_deprecation(
            "ksm add-registry",
            "ksm registry add",
            "v0.2.0",
            "v1.0.0",
        )
        assert "v0.2.0" in result
        assert "v1.0.0" in result

    def test_indentation(self) -> None:
        """Second line is indented with two spaces."""
        result = format_deprecation("old", "new", "v0.1.0", "v0.2.0")
        lines = result.splitlines()
        assert lines[1].startswith("  ")

    def test_first_line_structure(self) -> None:
        """First line mentions deprecation with backtick-wrapped names."""
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

# Strategy for single-line printable text (no embedded newlines)
_single_line = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cc", "Cs", "Zl", "Zp"),
    ),
    min_size=1,
    max_size=100,
)


@given(what=_single_line, why=_single_line, fix=_single_line)
def test_format_error_property(what: str, why: str, fix: str) -> None:
    """Property 14: format_error starts with 'Error: ' and has
    three lines. (Req 13.1, 13.3)"""
    result = format_error(what, why, fix)
    assert result.startswith("Error: ")
    lines = result.splitlines()
    assert len(lines) == 3
    assert what in lines[0]
    assert why in lines[1]
    assert fix in lines[2]


@given(what=_single_line, detail=_single_line)
def test_format_warning_property(what: str, detail: str) -> None:
    """Property 14: format_warning starts with 'Warning: ' and
    has two lines. (Req 13.4)"""
    result = format_warning(what, detail)
    assert result.startswith("Warning: ")
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
    """Property 14: format_deprecation starts with 'Deprecated: '
    and contains both version strings. (Req 13.5)"""
    result = format_deprecation(old, new, since, removal)
    assert result.startswith("Deprecated: ")
    lines = result.splitlines()
    assert len(lines) == 2
    assert since in result
    assert removal in result
