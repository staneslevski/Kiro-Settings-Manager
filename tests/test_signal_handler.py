"""Tests for ksm.signal_handler module.

Property 39: SIGINT handler cleans up temp directories.
"""

import signal
from pathlib import Path

import pytest

from ksm.signal_handler import (
    _active_temp_dirs,
    _sigint_handler,
    install_signal_handler,
    register_temp_dir,
    unregister_temp_dir,
)


@pytest.fixture(autouse=True)
def _clear_temp_dirs() -> None:
    """Ensure _active_temp_dirs is empty before each test."""
    _active_temp_dirs.clear()


def test_register_and_unregister(tmp_path: Path) -> None:
    """register/unregister adds and removes paths."""
    d = tmp_path / "work"
    d.mkdir()
    register_temp_dir(d)
    assert d in _active_temp_dirs
    unregister_temp_dir(d)
    assert d not in _active_temp_dirs


def test_unregister_missing_path_is_noop(tmp_path: Path) -> None:
    """unregister on a path not tracked does not raise."""
    unregister_temp_dir(tmp_path / "nonexistent")
    assert len(_active_temp_dirs) == 0


def test_sigint_handler_cleans_up_dirs(tmp_path: Path) -> None:
    """Property 39: SIGINT handler cleans up temp directories."""
    dirs = [tmp_path / f"tmp_{i}" for i in range(3)]
    for d in dirs:
        d.mkdir()
        (d / "file.txt").write_text("data")
        register_temp_dir(d)

    with pytest.raises(SystemExit) as exc_info:
        _sigint_handler(signal.SIGINT, None)

    assert exc_info.value.code == 130
    for d in dirs:
        assert not d.exists()
    assert len(_active_temp_dirs) == 0


def test_sigint_handler_no_active_dirs_exits_130() -> None:
    """No-op when no active dirs — exits 130 immediately."""
    assert len(_active_temp_dirs) == 0
    with pytest.raises(SystemExit) as exc_info:
        _sigint_handler(signal.SIGINT, None)
    assert exc_info.value.code == 130


def test_sigint_handler_prints_message_to_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Handler prints cancellation message to stderr."""
    d = tmp_path / "work"
    d.mkdir()
    register_temp_dir(d)

    with pytest.raises(SystemExit):
        _sigint_handler(signal.SIGINT, None)

    captured = capsys.readouterr()
    assert "Cancelled" in captured.err
    assert "temporary files" in captured.err
    assert captured.out == ""


def test_sigint_handler_no_message_when_empty(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No message printed when no dirs were tracked."""
    with pytest.raises(SystemExit):
        _sigint_handler(signal.SIGINT, None)

    captured = capsys.readouterr()
    assert captured.err == ""


def test_sigint_handler_ignores_already_removed(
    tmp_path: Path,
) -> None:
    """Handler tolerates dirs that were already removed."""
    d = tmp_path / "gone"
    register_temp_dir(d)  # never created on disk

    with pytest.raises(SystemExit) as exc_info:
        _sigint_handler(signal.SIGINT, None)

    assert exc_info.value.code == 130
    assert len(_active_temp_dirs) == 0


def test_install_signal_handler_registers() -> None:
    """install_signal_handler sets SIGINT to our handler."""
    install_signal_handler()
    current = signal.getsignal(signal.SIGINT)
    assert current is _sigint_handler
    # Restore default handler
    signal.signal(signal.SIGINT, signal.default_int_handler)
