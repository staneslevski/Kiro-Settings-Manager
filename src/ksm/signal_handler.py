"""Signal handler for graceful SIGINT cleanup.

Tracks temporary directories created during git operations and
cleans them up if the user presses Ctrl-C.

Requirements: 34.1, 34.2, 34.3, 34.4
"""

import shutil
import signal
import sys
from pathlib import Path
from types import FrameType

_active_temp_dirs: set[Path] = set()


def register_temp_dir(path: Path) -> None:
    """Register a temporary directory for cleanup on SIGINT."""
    _active_temp_dirs.add(path)


def unregister_temp_dir(path: Path) -> None:
    """Unregister a temporary directory after successful cleanup."""
    _active_temp_dirs.discard(path)


def _sigint_handler(signum: int, frame: FrameType | None) -> None:
    """Handle SIGINT by cleaning up tracked temp dirs."""
    for tmp in list(_active_temp_dirs):
        try:
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass
    if _active_temp_dirs:
        print(
            "\nInterrupted — cleaned up temporary files.",
            file=sys.stderr,
        )
    _active_temp_dirs.clear()
    raise SystemExit(130)


def install_signal_handler() -> None:
    """Install the SIGINT handler for temp-dir cleanup."""
    signal.signal(signal.SIGINT, _sigint_handler)
