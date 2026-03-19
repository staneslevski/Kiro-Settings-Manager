"""Git operations for ksm.

Wraps git clone and git pull via subprocess calls to the
system git binary.
"""

import subprocess
import tempfile
from pathlib import Path

from ksm.errors import GitError


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
    try:
        clone_repo(url, tmp_dir)
    except GitError:
        import shutil

        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    return tmp_dir
