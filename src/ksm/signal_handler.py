"""SIGINT handler for graceful cleanup of temporary directories.

Registers a signal handler at CLI startup that tracks active temp
directories. On SIGINT (Ctrl+C), cleans up tracked dirs and exits 130.
"""

import shutil
import signal
import sys
from pathlib import Path
from types import FrameType

# Module-level set of temp directories to clean up on SIGINT
_active_temp_dirs: set[Path] = set()


def register_temp_dir(path: Path) -> None:
    """Track a temp directory for cleanup on SIGINT."""
    _active_temp_dirs.add(path)


def unregister_temp_dir(path: Path) -> None:
    """Stop tracking a temp directory (normal cleanup completed)."""
    _active_temp_dirs.discard(path)


def _sigint_handler(signum: int, frame: FrameType | None) -> None:
    """Clean up tracked temp dirs and exit 130."""
    for d in list(_active_temp_dirs):
        shutil.rmtree(d, ignore_errors=True)
    if _active_temp_dirs:
        print(
            "\nCancelled. Cleaned up temporary files.",
            file=sys.stderr,
        )
    _active_temp_dirs.clear()
    sys.exit(130)


def install_signal_handler() -> None:
    """Register the SIGINT handler. Called once at CLI startup."""
    signal.signal(signal.SIGINT, _sigint_handler)
