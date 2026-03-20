"""Tests for signal_handler module.

Property 39: SIGINT handler cleans up temp directories
Test no-op when no active dirs (exits 130 immediately)
Validates: Requirements 34.1, 34.2, 34.3, 34.4
"""

from pathlib import Path

import pytest

from ksm.signal_handler import (
    _active_temp_dirs,
    _sigint_handler,
    install_signal_handler,
    register_temp_dir,
    unregister_temp_dir,
)


class TestSignalHandler:
    """Tests for SIGINT handler cleanup."""

    def setup_method(self) -> None:
        """Clear active temp dirs before each test."""
        _active_temp_dirs.clear()

    def teardown_method(self) -> None:
        """Clear active temp dirs after each test."""
        _active_temp_dirs.clear()

    def test_register_and_unregister(self, tmp_path: Path) -> None:
        d = tmp_path / "tmp1"
        register_temp_dir(d)
        assert d in _active_temp_dirs
        unregister_temp_dir(d)
        assert d not in _active_temp_dirs

    def test_unregister_nonexistent_is_noop(self, tmp_path: Path) -> None:
        d = tmp_path / "nope"
        unregister_temp_dir(d)
        assert d not in _active_temp_dirs

    def test_sigint_handler_no_dirs_exits_130(self) -> None:
        """No active dirs: exits 130 immediately."""
        with pytest.raises(SystemExit, match="130"):
            _sigint_handler(2, None)

    def test_sigint_handler_cleans_up_dirs(self, tmp_path: Path) -> None:
        """Handler removes tracked temp dirs."""
        d1 = tmp_path / "t1"
        d1.mkdir()
        (d1 / "file.txt").write_text("data")
        d2 = tmp_path / "t2"
        d2.mkdir()

        register_temp_dir(d1)
        register_temp_dir(d2)

        with pytest.raises(SystemExit, match="130"):
            _sigint_handler(2, None)

        assert not d1.exists()
        assert not d2.exists()
        assert len(_active_temp_dirs) == 0

    def test_sigint_handler_prints_to_stderr(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Handler prints cleanup message to stderr."""
        d = tmp_path / "t"
        d.mkdir()
        register_temp_dir(d)

        with pytest.raises(SystemExit, match="130"):
            _sigint_handler(2, None)

        captured = capsys.readouterr()
        assert "interrupted" in captured.err.lower()
        assert "cleaned up" in captured.err.lower()

    def test_sigint_handler_tolerates_missing_dir(self, tmp_path: Path) -> None:
        """Handler doesn't crash if dir already gone."""
        d = tmp_path / "gone"
        register_temp_dir(d)

        with pytest.raises(SystemExit, match="130"):
            _sigint_handler(2, None)

        assert len(_active_temp_dirs) == 0

    def test_install_signal_handler_sets_handler(
        self,
    ) -> None:
        """install_signal_handler registers the handler."""
        import signal

        install_signal_handler()
        assert signal.getsignal(signal.SIGINT) is _sigint_handler

    def test_sigint_handler_rmtree_exception_is_caught(self, tmp_path: Path) -> None:
        """Handler catches exceptions from rmtree."""
        from unittest.mock import patch as mp

        d = tmp_path / "bad"
        d.mkdir()
        register_temp_dir(d)

        with mp(
            "ksm.signal_handler.shutil.rmtree",
            side_effect=OSError("permission denied"),
        ):
            with pytest.raises(SystemExit, match="130"):
                _sigint_handler(2, None)

        assert len(_active_temp_dirs) == 0
