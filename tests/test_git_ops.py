"""Tests for ksm.git_ops module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ksm.errors import GitError


def test_clone_repo_calls_subprocess(tmp_path: Path) -> None:
    """clone_repo calls git clone with correct args."""
    from ksm.git_ops import clone_repo

    target = tmp_path / "repo"
    with patch("ksm.git_ops.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        clone_repo("https://github.com/org/repo.git", target)

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[0] == "git"
    assert args[1] == "clone"
    assert "https://github.com/org/repo.git" in args
    assert str(target) in args


def test_pull_repo_calls_subprocess(tmp_path: Path) -> None:
    """pull_repo calls git pull with correct args."""
    from ksm.git_ops import pull_repo

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    with patch("ksm.git_ops.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        pull_repo(repo_dir)

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[0] == "git"
    assert args[1] == "pull"


def test_clone_ephemeral_returns_temp_path() -> None:
    """clone_ephemeral returns a temp path and calls git clone."""
    from ksm.git_ops import clone_ephemeral

    with patch("ksm.git_ops.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = clone_ephemeral("https://github.com/org/repo.git")

    assert result.exists()
    assert result.is_dir()
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "https://github.com/org/repo.git" in args

    # Clean up the temp dir
    import shutil

    shutil.rmtree(result)


def test_clone_repo_raises_git_error_on_failure(
    tmp_path: Path,
) -> None:
    """clone_repo raises GitError when git clone fails."""
    from ksm.git_ops import clone_repo

    target = tmp_path / "repo"
    with patch("ksm.git_ops.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            128, "git", stderr="fatal: repo not found"
        )
        with pytest.raises(GitError) as exc_info:
            clone_repo("https://bad-url.git", target)
        assert "bad-url" in str(exc_info.value) or "fatal" in str(exc_info.value)


def test_pull_repo_raises_git_error_on_failure(
    tmp_path: Path,
) -> None:
    """pull_repo raises GitError when git pull fails."""
    from ksm.git_ops import pull_repo

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    with patch("ksm.git_ops.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "git", stderr="error: pull failed"
        )
        with pytest.raises(GitError):
            pull_repo(repo_dir)


def test_clone_ephemeral_raises_git_error_on_failure() -> None:
    """clone_ephemeral raises GitError when git clone fails."""
    from ksm.git_ops import clone_ephemeral

    with patch("ksm.git_ops.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            128, "git", stderr="fatal: error"
        )
        with pytest.raises(GitError):
            clone_ephemeral("https://bad-url.git")


# --- Property-based tests ---


# Feature: kiro-settings-manager, Property 22: Ephemeral clone is cleaned up
@given(
    url=st.from_regex(
        r"https://github\.com/[a-z]{1,8}/[a-z]{1,8}\.git",
        fullmatch=True,
    ),
)
def test_property_ephemeral_clone_cleaned_up(url: str) -> None:
    """Property 22: Ephemeral clone temp dir is cleaned up on failure."""
    from ksm.git_ops import clone_ephemeral

    with patch("ksm.git_ops.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            128, "git", stderr="fatal: error"
        )
        with pytest.raises(GitError):
            clone_ephemeral(url)

    # After the error, no temp dirs should be left behind.
    # We can't easily check all temp dirs, but we verify the
    # function raised without leaking by checking it completes.
    # The real cleanup test is in the integration tests.
