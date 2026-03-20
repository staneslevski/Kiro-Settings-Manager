"""Tests for enriched error classes.

Property 11: BundleNotFoundError contains name and all searched registries
Property 12: GitError contains URL and cleaned summary
"""

from hypothesis import given
from hypothesis import strategies as st

from ksm.errors import BundleNotFoundError, GitError

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
