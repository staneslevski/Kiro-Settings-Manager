"""Git operations for ksm.

Wraps git clone and git pull via subprocess calls to the
system git binary.
"""

import subprocess
import tempfile
from pathlib import Path

from ksm.errors import GitError
from ksm.signal_handler import register_temp_dir, unregister_temp_dir


def clone_repo(url: str, target_dir: Path) -> None:
    """Clone a git repo to target_dir.

    Raises GitError on failure.
    """
    try:
        subprocess.run(
            ["git", "clone", url, str(target_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise GitError(f"Failed to clone {url}: {e.stderr}") from e


def pull_repo(repo_dir: Path) -> None:
    """Pull latest changes in an existing repo.

    Raises GitError on failure.
    """
    try:
        subprocess.run(
            ["git", "pull"],
            cwd=str(repo_dir),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise GitError(f"Failed to pull in {repo_dir}: {e.stderr}") from e


def clone_ephemeral(url: str) -> Path:
    """Clone a git repo to a temporary directory.

    Returns the path to the clone. Caller is responsible for
    deleting the directory when done.
    Raises GitError on failure (temp dir is cleaned up on error).
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="ksm-ephemeral-"))
    register_temp_dir(tmp_dir)
    try:
        clone_repo(url, tmp_dir)
    except GitError:
        import shutil

        shutil.rmtree(tmp_dir, ignore_errors=True)
        unregister_temp_dir(tmp_dir)
        raise
    return tmp_dir


def list_versions(repo_dir: Path) -> list[str]:
    """List git tags in a repository, sorted newest first.

    Returns a list of tag names. Raises GitError on failure.
    """
    try:
        result = subprocess.run(
            ["git", "tag", "--sort=-creatordate"],
            cwd=str(repo_dir),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise GitError(f"Failed to list tags in {repo_dir}: {e.stderr}") from e

    tags = [t.strip() for t in result.stdout.splitlines() if t.strip()]
    return tags


def checkout_version(repo_dir: Path, version: str) -> None:
    """Checkout a specific tag/version in a repository.

    Raises GitError if the version does not exist.
    """
    try:
        subprocess.run(
            ["git", "checkout", version],
            cwd=str(repo_dir),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise GitError(f"Version '{version}' not found: {e.stderr}") from e
