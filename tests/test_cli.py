"""Tests for ksm.cli — CLI entry point.

Requirements: 8.2, 8.3, 8.4, 8.5
"""

from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ksm import __version__
from ksm.cli import main


class TestHelp:
    """Test --help displays help with all commands listed."""

    def test_help_flag_exits_zero(self, capsys: pytest.CaptureFixture) -> None:
        """--help exits with SystemExit(0)."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "--help"]):
                main()
        assert exc_info.value.code == 0

    def test_help_lists_all_commands(self, capsys: pytest.CaptureFixture) -> None:
        """--help output contains all five subcommands."""
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "--help"]):
                main()
        captured = capsys.readouterr()
        for cmd in ("add", "ls", "sync", "add-registry", "rm"):
            assert cmd in captured.out


class TestVersion:
    """Test --version displays version string."""

    def test_version_flag_prints_version(self, capsys: pytest.CaptureFixture) -> None:
        """--version prints the version and exits 0."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "--version"]):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert __version__ in captured.out


class TestUnknownCommand:
    """Test unknown command exits with non-zero status."""

    def test_unknown_command_exits_nonzero(self, capsys: pytest.CaptureFixture) -> None:
        """An unrecognised subcommand exits with non-zero."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "bogus-cmd"]):
                main()
        assert exc_info.value.code != 0

    def test_unknown_command_lists_valid_commands(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Error output for unknown command lists valid commands."""
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "bogus-cmd"]):
                main()
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        for cmd in ("add", "ls", "sync", "add-registry", "rm"):
            assert cmd in combined


class TestSubcommandDispatch:
    """Test each subcommand dispatches to correct handler."""

    @patch("ksm.cli._dispatch_add")
    def test_add_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm add mybundle' dispatches to add handler."""
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "add", "mybundle"]):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()

    @patch("ksm.cli._dispatch_ls")
    def test_ls_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm ls' dispatches to ls handler."""
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "ls"]):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()

    @patch("ksm.cli._dispatch_sync")
    def test_sync_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm sync --all --yes' dispatches to sync handler."""
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "sync", "--all", "--yes"]):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()

    @patch("ksm.cli._dispatch_add_registry")
    def test_add_registry_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm add-registry <url>' dispatches to add-registry handler."""
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["ksm", "add-registry", "https://example.com/repo.git"],
            ):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()

    @patch("ksm.cli._dispatch_rm")
    def test_rm_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm rm mybundle' dispatches to rm handler."""
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "rm", "mybundle"]):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()


class TestAddSubcommandFlags:
    """Test that add subcommand accepts all expected flags."""

    @patch("ksm.cli._dispatch_add")
    def test_add_global_flag(self, mock_dispatch: MagicMock) -> None:
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "add", "-g", "mybundle"]):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.global_ is True

    @patch("ksm.cli._dispatch_add")
    def test_add_local_flag(self, mock_dispatch: MagicMock) -> None:
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "add", "-l", "mybundle"]):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.local is True

    @patch("ksm.cli._dispatch_add")
    def test_add_display_flag(self, mock_dispatch: MagicMock) -> None:
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "add", "--display"]):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.display is True

    @patch("ksm.cli._dispatch_add")
    def test_add_from_flag(self, mock_dispatch: MagicMock) -> None:
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch(
                "sys.argv",
                [
                    "ksm",
                    "add",
                    "--from",
                    "https://x.com/r.git",
                    "mybundle",
                ],
            ):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.from_url == "https://x.com/r.git"

    @patch("ksm.cli._dispatch_add")
    def test_add_filter_flags(self, mock_dispatch: MagicMock) -> None:
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch(
                "sys.argv",
                [
                    "ksm",
                    "add",
                    "--skills-only",
                    "--hooks-only",
                    "mybundle",
                ],
            ):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.skills_only is True
        assert args.hooks_only is True


class TestSyncSubcommandFlags:
    """Test that sync subcommand accepts expected flags."""

    @patch("ksm.cli._dispatch_sync")
    def test_sync_yes_flag(self, mock_dispatch: MagicMock) -> None:
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "sync", "--yes", "--all"]):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.yes is True

    @patch("ksm.cli._dispatch_sync")
    def test_sync_all_flag(self, mock_dispatch: MagicMock) -> None:
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "sync", "--all"]):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.all is True

    @patch("ksm.cli._dispatch_sync")
    def test_sync_bundle_names(self, mock_dispatch: MagicMock) -> None:
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "sync", "a", "b", "--yes"]):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.bundle_names == ["a", "b"]


class TestRmSubcommandFlags:
    """Test that rm subcommand accepts expected flags."""

    @patch("ksm.cli._dispatch_rm")
    def test_rm_display_flag(self, mock_dispatch: MagicMock) -> None:
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "rm", "--display"]):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.display is True

    @patch("ksm.cli._dispatch_rm")
    def test_rm_global_flag(self, mock_dispatch: MagicMock) -> None:
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "rm", "-g", "mybundle"]):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.global_ is True


# Feature: kiro-settings-manager, Property 20: Unknown CLI command produces error
class TestProperty20:
    """Property 20: Unknown CLI command produces error.

    For any string that is not one of the recognised commands,
    the CLI shall exit with a non-zero status code and the output
    shall list the valid commands.

    Validates: Requirements 8.5
    """

    @given(
        cmd=st.text(
            alphabet=st.characters(
                whitelist_categories=("Ll", "Lu", "Nd"),
            ),
            min_size=1,
            max_size=20,
        ).filter(lambda s: s not in ("add", "ls", "sync", "add-registry", "rm"))
    )
    def test_unknown_command_produces_error(self, cmd: str) -> None:
        import io
        from contextlib import redirect_stderr, redirect_stdout

        out = io.StringIO()
        err = io.StringIO()
        with pytest.raises(SystemExit) as exc_info:
            with redirect_stdout(out), redirect_stderr(err):
                with patch("sys.argv", ["ksm", cmd]):
                    main()
        assert exc_info.value.code != 0
        combined = out.getvalue() + err.getvalue()
        for valid_cmd in (
            "add",
            "ls",
            "sync",
            "add-registry",
            "rm",
        ):
            assert valid_cmd in combined


class TestDispatchIntegration:
    """Test that dispatch functions wire up correctly to commands.

    These tests exercise the real _dispatch_* functions (not mocked)
    by mocking the underlying command handlers and persistence.
    """

    @patch("ksm.cli.load_manifest")
    @patch("ksm.cli.load_registry_index")
    @patch("ksm.cli.ensure_ksm_dir")
    @patch("ksm.commands.add.run_add", return_value=0)
    def test_dispatch_add_wires_correctly(
        self,
        mock_run_add: MagicMock,
        mock_ensure: MagicMock,
        mock_load_reg: MagicMock,
        mock_load_man: MagicMock,
    ) -> None:
        from ksm.manifest import Manifest
        from ksm.registry import RegistryIndex

        mock_load_reg.return_value = RegistryIndex(registries=[])
        mock_load_man.return_value = Manifest(entries=[])

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "add", "mybundle"]):
                main()
        assert exc_info.value.code == 0
        mock_ensure.assert_called_once()
        mock_run_add.assert_called_once()

    @patch("ksm.cli.load_manifest")
    @patch("ksm.commands.ls.run_ls", return_value=0)
    def test_dispatch_ls_wires_correctly(
        self,
        mock_run_ls: MagicMock,
        mock_load_man: MagicMock,
    ) -> None:
        from ksm.manifest import Manifest

        mock_load_man.return_value = Manifest(entries=[])

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "ls"]):
                main()
        assert exc_info.value.code == 0
        mock_run_ls.assert_called_once()

    @patch("ksm.cli.load_manifest")
    @patch("ksm.cli.load_registry_index")
    @patch("ksm.cli.ensure_ksm_dir")
    @patch("ksm.commands.sync.run_sync", return_value=0)
    def test_dispatch_sync_wires_correctly(
        self,
        mock_run_sync: MagicMock,
        mock_ensure: MagicMock,
        mock_load_reg: MagicMock,
        mock_load_man: MagicMock,
    ) -> None:
        from ksm.manifest import Manifest
        from ksm.registry import RegistryIndex

        mock_load_reg.return_value = RegistryIndex(registries=[])
        mock_load_man.return_value = Manifest(entries=[])

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "sync", "--all", "--yes"]):
                main()
        assert exc_info.value.code == 0
        mock_ensure.assert_called_once()
        mock_run_sync.assert_called_once()

    @patch("ksm.cli.load_registry_index")
    @patch("ksm.cli.ensure_ksm_dir")
    @patch(
        "ksm.commands.add_registry.run_add_registry",
        return_value=0,
    )
    def test_dispatch_add_registry_wires_correctly(
        self,
        mock_run_ar: MagicMock,
        mock_ensure: MagicMock,
        mock_load_reg: MagicMock,
    ) -> None:
        from ksm.registry import RegistryIndex

        mock_load_reg.return_value = RegistryIndex(registries=[])

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["ksm", "add-registry", "https://x.com/r.git"],
            ):
                main()
        assert exc_info.value.code == 0
        mock_ensure.assert_called_once()
        mock_run_ar.assert_called_once()

    @patch("ksm.cli.load_manifest")
    @patch("ksm.cli.ensure_ksm_dir")
    @patch("ksm.commands.rm.run_rm", return_value=0)
    def test_dispatch_rm_wires_correctly(
        self,
        mock_run_rm: MagicMock,
        mock_ensure: MagicMock,
        mock_load_man: MagicMock,
    ) -> None:
        from ksm.manifest import Manifest

        mock_load_man.return_value = Manifest(entries=[])

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "rm", "mybundle"]):
                main()
        assert exc_info.value.code == 0
        mock_ensure.assert_called_once()
        mock_run_rm.assert_called_once()

    def test_no_command_prints_help_exits_2(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Running ksm with no command prints help and exits 2."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm"]):
                main()
        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "add" in captured.out


class TestErrorClasses:
    """Test custom exception classes for coverage."""

    def test_mutual_exclusion_error(self) -> None:
        from ksm.errors import MutualExclusionError

        err = MutualExclusionError("--foo", "--bar")
        assert err.option_a == "--foo"
        assert err.option_b == "--bar"
        assert "--foo" in str(err)
        assert "--bar" in str(err)
        assert "mutually exclusive" in str(err)
