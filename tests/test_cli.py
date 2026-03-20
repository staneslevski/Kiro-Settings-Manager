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
        """--help output contains all subcommands."""
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "--help"]):
                main()
        captured = capsys.readouterr()
        for cmd in (
            "add",
            "list",
            "sync",
            "add-registry",
            "remove",
            "registry",
            "init",
            "info",
            "search",
            "completions",
        ):
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
        for cmd in (
            "add",
            "list",
            "sync",
            "add-registry",
            "remove",
            "registry",
            "init",
            "info",
            "search",
            "completions",
        ):
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

    @patch("ksm.cli._dispatch_ls")
    def test_list_dispatches_to_ls_handler(self, mock_dispatch: MagicMock) -> None:
        """'ksm list' dispatches to same handler as 'ksm ls'.

        Req 9.1, 9.5: list is an alias for ls with identical
        behaviour.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "list"]):
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

    @patch("ksm.cli._dispatch_rm")
    def test_remove_dispatches_to_rm_handler(self, mock_dispatch: MagicMock) -> None:
        """'ksm remove mybundle' dispatches to same handler as rm.

        Req 9.2, 9.6: remove is an alias for rm with identical
        behaviour.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "remove", "mybundle"]):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()

    @patch("ksm.cli._dispatch_init")
    def test_init_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm init' dispatches to init handler."""
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "init"]):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()

    @patch("ksm.cli._dispatch_info")
    def test_info_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm info mybundle' dispatches to info handler."""
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "info", "mybundle"]):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()

    @patch("ksm.cli._dispatch_search")
    def test_search_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm search query' dispatches to search handler."""
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "search", "myquery"]):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()

    @patch("ksm.cli._dispatch_completions")
    def test_completions_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm completions bash' dispatches to completions."""
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "completions", "bash"]):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()

    @patch("ksm.cli._dispatch_registry")
    def test_registry_ls_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm registry ls' dispatches to registry handler."""
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "registry", "ls"]):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()

    @patch("ksm.cli._dispatch_registry")
    def test_registry_rm_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm registry rm myname' dispatches to registry."""
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["ksm", "registry", "rm", "myname"],
            ):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()

    @patch("ksm.cli._dispatch_registry")
    def test_registry_inspect_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm registry inspect myname' dispatches."""
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["ksm", "registry", "inspect", "myname"],
            ):
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
        ).filter(
            lambda s: s
            not in (
                "add",
                "ls",
                "list",
                "sync",
                "add-registry",
                "rm",
                "remove",
                "registry",
                "init",
                "info",
                "search",
                "completions",
            )
        )
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
            "list",
            "sync",
            "add-registry",
            "remove",
            "registry",
            "init",
            "info",
            "search",
            "completions",
        ):
            assert valid_cmd in combined


class TestProperty9:
    """Property 9: Full-word and short aliases produce identical dispatch.

    For any valid argument list, parsing with the full-word command
    (list, remove) and the short alias (ls, rm) should dispatch to
    the same handler function.

    Validates: Requirements 9.5, 9.6
    """

    @given(
        verbose=st.booleans(),
        scope=st.sampled_from([None, "local", "global"]),
        fmt=st.sampled_from(["text", "json"]),
    )
    def test_list_ls_dispatch_equivalence(
        self,
        verbose: bool,
        scope: str | None,
        fmt: str,
    ) -> None:
        """list and ls produce identical dispatch for any flags."""
        base_args = ["ksm"]
        flags: list[str] = []
        if verbose:
            flags.append("-v")
        if scope:
            flags.extend(["--scope", scope])
        flags.extend(["--format", fmt])

        for cmd in ("list", "ls"):
            argv = base_args + [cmd] + flags
            with patch("ksm.cli._dispatch_ls") as mock_d:
                mock_d.return_value = 0
                with pytest.raises(SystemExit):
                    with patch("sys.argv", argv):
                        main()
                mock_d.assert_called_once()

    @given(
        bundle=st.from_regex(r"[a-z][a-z0-9\-]{0,19}", fullmatch=True),
        global_flag=st.booleans(),
    )
    def test_remove_rm_dispatch_equivalence(
        self,
        bundle: str,
        global_flag: bool,
    ) -> None:
        """remove and rm produce identical dispatch for any flags."""
        base_args = ["ksm"]
        flags: list[str] = []
        if global_flag:
            flags.append("-g")

        for cmd in ("remove", "rm"):
            argv = base_args + [cmd] + flags + [bundle]
            with patch("ksm.cli._dispatch_rm") as mock_d:
                mock_d.return_value = 0
                with pytest.raises(SystemExit):
                    with patch("sys.argv", argv):
                        main()
                mock_d.assert_called_once()


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

    @patch("ksm.commands.init.run_init", return_value=0)
    @patch("ksm.cli.load_manifest")
    @patch("ksm.cli.load_registry_index")
    def test_dispatch_init_wires_correctly(
        self,
        mock_load_reg: MagicMock,
        mock_load_man: MagicMock,
        mock_run_init: MagicMock,
    ) -> None:
        from ksm.manifest import Manifest
        from ksm.registry import RegistryIndex

        mock_load_reg.return_value = RegistryIndex(registries=[])
        mock_load_man.return_value = Manifest(entries=[])

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "init"]):
                main()
        assert exc_info.value.code == 0
        mock_run_init.assert_called_once()

    @patch("ksm.cli.load_manifest")
    @patch("ksm.cli.load_registry_index")
    @patch("ksm.commands.info.run_info", return_value=0)
    def test_dispatch_info_wires_correctly(
        self,
        mock_run_info: MagicMock,
        mock_load_reg: MagicMock,
        mock_load_man: MagicMock,
    ) -> None:
        from ksm.manifest import Manifest
        from ksm.registry import RegistryIndex

        mock_load_reg.return_value = RegistryIndex(registries=[])
        mock_load_man.return_value = Manifest(entries=[])

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "info", "mybundle"]):
                main()
        assert exc_info.value.code == 0
        mock_run_info.assert_called_once()

    @patch("ksm.cli.load_registry_index")
    @patch("ksm.commands.search.run_search", return_value=0)
    def test_dispatch_search_wires_correctly(
        self,
        mock_run_search: MagicMock,
        mock_load_reg: MagicMock,
    ) -> None:
        from ksm.registry import RegistryIndex

        mock_load_reg.return_value = RegistryIndex(registries=[])

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "search", "myquery"]):
                main()
        assert exc_info.value.code == 0
        mock_run_search.assert_called_once()

    @patch(
        "ksm.commands.completions.run_completions",
        return_value=0,
    )
    def test_dispatch_completions_wires_correctly(
        self,
        mock_run_comp: MagicMock,
    ) -> None:
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "completions", "bash"]):
                main()
        assert exc_info.value.code == 0
        mock_run_comp.assert_called_once()

    @patch("ksm.cli.load_registry_index")
    @patch("ksm.cli.ensure_ksm_dir")
    @patch(
        "ksm.commands.registry_ls.run_registry_ls",
        return_value=0,
    )
    def test_dispatch_registry_ls_wires_correctly(
        self,
        mock_run_rls: MagicMock,
        mock_ensure: MagicMock,
        mock_load_reg: MagicMock,
    ) -> None:
        from ksm.registry import RegistryIndex

        mock_load_reg.return_value = RegistryIndex(registries=[])

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "registry", "ls"]):
                main()
        assert exc_info.value.code == 0
        mock_ensure.assert_called_once()
        mock_run_rls.assert_called_once()

    @patch("ksm.cli.load_registry_index")
    @patch("ksm.cli.ensure_ksm_dir")
    @patch(
        "ksm.commands.registry_rm.run_registry_rm",
        return_value=0,
    )
    def test_dispatch_registry_rm_wires_correctly(
        self,
        mock_run_rrm: MagicMock,
        mock_ensure: MagicMock,
        mock_load_reg: MagicMock,
    ) -> None:
        from ksm.registry import RegistryIndex

        mock_load_reg.return_value = RegistryIndex(registries=[])

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["ksm", "registry", "rm", "myname"],
            ):
                main()
        assert exc_info.value.code == 0
        mock_ensure.assert_called_once()
        mock_run_rrm.assert_called_once()

    @patch("ksm.cli.load_registry_index")
    @patch("ksm.cli.ensure_ksm_dir")
    @patch(
        "ksm.commands.registry_inspect.run_registry_inspect",
        return_value=0,
    )
    def test_dispatch_registry_inspect_wires_correctly(
        self,
        mock_run_ri: MagicMock,
        mock_ensure: MagicMock,
        mock_load_reg: MagicMock,
    ) -> None:
        from ksm.registry import RegistryIndex

        mock_load_reg.return_value = RegistryIndex(registries=[])

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["ksm", "registry", "inspect", "myname"],
            ):
                main()
        assert exc_info.value.code == 0
        mock_ensure.assert_called_once()
        mock_run_ri.assert_called_once()

    def test_registry_no_subcommand_exits_2(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """'ksm registry' with no subcommand exits 2."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "registry"]):
                main()
        assert exc_info.value.code == 2

    @patch("ksm.cli.load_registry_index")
    @patch("ksm.cli.ensure_ksm_dir")
    @patch(
        "ksm.commands.registry_add.run_registry_add",
        return_value=0,
    )
    def test_dispatch_registry_add_wires_correctly(
        self,
        mock_run_ra: MagicMock,
        mock_ensure: MagicMock,
        mock_load_reg: MagicMock,
    ) -> None:
        from ksm.registry import RegistryIndex

        mock_load_reg.return_value = RegistryIndex(registries=[])

        with pytest.raises(SystemExit):
            with patch(
                "sys.argv",
                [
                    "ksm",
                    "registry",
                    "add",
                    "https://x.com/r.git",
                ],
            ):
                main()
        mock_ensure.assert_called_once()

    @patch("ksm.commands.init.run_init", return_value=0)
    @patch(
        "ksm.cli.load_manifest",
        side_effect=Exception("no manifest"),
    )
    @patch(
        "ksm.cli.load_registry_index",
        side_effect=FileNotFoundError("no reg"),
    )
    def test_dispatch_init_handles_missing_files(
        self,
        mock_load_reg: MagicMock,
        mock_load_man: MagicMock,
        mock_run_init: MagicMock,
    ) -> None:
        """Init works even when registry/manifest don't exist."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "init"]):
                main()
        assert exc_info.value.code == 0
        mock_run_init.assert_called_once()
        # Verify None was passed for both
        call_kwargs = mock_run_init.call_args[1]
        assert call_kwargs["registry_index"] is None
        assert call_kwargs["manifest"] is None


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


class TestFullWordAliases:
    """Test full-word top-level command aliases.

    Req 9.1–9.7: list/ls and remove/rm aliases dispatch
    identically, help shows full-word primary with short alias.
    """

    def test_help_shows_list_as_primary(self, capsys: pytest.CaptureFixture) -> None:
        """Help text shows 'list' as primary with '(ls)' noted.

        Req 9.7: Full-word form is primary, short form in
        parentheses as a single entry.
        """
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "--help"]):
                main()
        captured = capsys.readouterr()
        assert "list" in captured.out
        # Short alias should NOT appear as a separate top-level
        # entry — it should be noted alongside the primary.
        # We check that 'ls' appears only in the context of
        # the list entry (e.g. "list (ls)").
        lines = captured.out.splitlines()
        ls_standalone = any(
            line.strip().startswith("ls") and "list" not in line for line in lines
        )
        assert not ls_standalone, "'ls' should not appear as a standalone help entry"

    def test_help_shows_remove_as_primary(self, capsys: pytest.CaptureFixture) -> None:
        """Help text shows 'remove' as primary with '(rm)' noted.

        Req 9.7: Full-word form is primary, short form in
        parentheses as a single entry.
        """
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "--help"]):
                main()
        captured = capsys.readouterr()
        assert "remove" in captured.out
        lines = captured.out.splitlines()
        rm_standalone = any(
            line.strip().startswith("rm") and "remove" not in line for line in lines
        )
        assert not rm_standalone, "'rm' should not appear as a standalone help entry"

    @patch("ksm.cli._dispatch_ls")
    def test_list_and_ls_dispatch_same_handler(self, mock_dispatch: MagicMock) -> None:
        """Both 'list' and 'ls' dispatch to _dispatch_ls.

        Req 9.3, 9.5: ls retained for backward compat, list
        produces identical output.
        """
        mock_dispatch.return_value = 0
        # Test 'list'
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "list"]):
                main()
        assert mock_dispatch.call_count == 1
        # Test 'ls'
        mock_dispatch.reset_mock()
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "ls"]):
                main()
        assert mock_dispatch.call_count == 1

    @patch("ksm.cli._dispatch_rm")
    def test_remove_and_rm_dispatch_same_handler(
        self, mock_dispatch: MagicMock
    ) -> None:
        """Both 'remove' and 'rm' dispatch to _dispatch_rm.

        Req 9.4, 9.6: rm retained for backward compat, remove
        produces identical output.
        """
        mock_dispatch.return_value = 0
        # Test 'remove'
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "remove", "mybundle"]):
                main()
        assert mock_dispatch.call_count == 1
        # Test 'rm'
        mock_dispatch.reset_mock()
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "rm", "mybundle"]):
                main()
        assert mock_dispatch.call_count == 1

    @patch("ksm.cli.load_manifest")
    @patch("ksm.commands.ls.run_ls", return_value=0)
    def test_dispatch_list_wires_correctly(
        self,
        mock_run_ls: MagicMock,
        mock_load_man: MagicMock,
    ) -> None:
        """'ksm list' wires to run_ls same as 'ksm ls'.

        Req 9.1, 9.5: list alias dispatches identically.
        """
        from ksm.manifest import Manifest

        mock_load_man.return_value = Manifest(entries=[])

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "list"]):
                main()
        assert exc_info.value.code == 0
        mock_run_ls.assert_called_once()

    @patch("ksm.cli.load_manifest")
    @patch("ksm.cli.ensure_ksm_dir")
    @patch("ksm.commands.rm.run_rm", return_value=0)
    def test_dispatch_remove_wires_correctly(
        self,
        mock_run_rm: MagicMock,
        mock_ensure: MagicMock,
        mock_load_man: MagicMock,
    ) -> None:
        """'ksm remove mybundle' wires to run_rm same as 'rm'.

        Req 9.2, 9.6: remove alias dispatches identically.
        """
        from ksm.manifest import Manifest

        mock_load_man.return_value = Manifest(entries=[])

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "remove", "mybundle"]):
                main()
        assert exc_info.value.code == 0
        mock_ensure.assert_called_once()
        mock_run_rm.assert_called_once()


class TestRegistrySubcommandGroup:
    """Test registry subcommand group restructuring.

    Req 7.1–7.11: registry add/remove/list/inspect subcommands
    with full-word primaries and short aliases.
    """

    def test_registry_no_subcommand_exits_2(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """'ksm registry' with no subcommand exits 2.

        Req 7.6: registry without subcommand prints usage and
        exits 2.
        """
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "registry"]):
                main()
        assert exc_info.value.code == 2

    def test_registry_help_exits_0(self, capsys: pytest.CaptureFixture) -> None:
        """'ksm registry --help' exits 0.

        Req 7.10: registry --help prints help and exits 0.
        """
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "registry", "--help"]):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        for sub in ("add", "remove", "list", "inspect"):
            assert sub in captured.out

    def test_registry_add_help_exits_0(self, capsys: pytest.CaptureFixture) -> None:
        """'ksm registry add --help' exits 0.

        Req 7.11: registry <sub> --help prints help and exits 0.
        """
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "registry", "add", "--help"]):
                main()
        assert exc_info.value.code == 0

    def test_registry_remove_help_exits_0(self, capsys: pytest.CaptureFixture) -> None:
        """'ksm registry remove --help' exits 0.

        Req 7.11.
        """
        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["ksm", "registry", "remove", "--help"],
            ):
                main()
        assert exc_info.value.code == 0

    def test_registry_list_help_exits_0(self, capsys: pytest.CaptureFixture) -> None:
        """'ksm registry list --help' exits 0.

        Req 7.11.
        """
        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["ksm", "registry", "list", "--help"],
            ):
                main()
        assert exc_info.value.code == 0

    def test_registry_inspect_help_exits_0(self, capsys: pytest.CaptureFixture) -> None:
        """'ksm registry inspect --help' exits 0.

        Req 7.11.
        """
        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["ksm", "registry", "inspect", "--help"],
            ):
                main()
        assert exc_info.value.code == 0

    @patch("ksm.cli._dispatch_registry")
    def test_registry_remove_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm registry remove myname' dispatches to registry.

        Req 7.3, 7.7: remove is the canonical name.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["ksm", "registry", "remove", "myname"],
            ):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()

    @patch("ksm.cli._dispatch_registry")
    def test_registry_rm_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm registry rm myname' still works as alias.

        Req 7.9: rm accepted as alias for remove.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["ksm", "registry", "rm", "myname"],
            ):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()

    @patch("ksm.cli._dispatch_registry")
    def test_registry_list_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm registry list' dispatches to registry.

        Req 7.4, 7.8: list is the canonical name.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "registry", "list"]):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()

    @patch("ksm.cli._dispatch_registry")
    def test_registry_ls_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm registry ls' still works as alias.

        Req 7.9: ls accepted as alias for list.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "registry", "ls"]):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()

    @patch("ksm.cli.load_registry_index")
    @patch("ksm.cli.ensure_ksm_dir")
    @patch(
        "ksm.commands.registry_rm.run_registry_rm",
        return_value=0,
    )
    def test_dispatch_registry_remove_wires(
        self,
        mock_run_rrm: MagicMock,
        mock_ensure: MagicMock,
        mock_load_reg: MagicMock,
    ) -> None:
        """'ksm registry remove myname' wires to run_registry_rm.

        Req 7.3, 7.7: remove dispatches correctly.
        """
        from ksm.registry import RegistryIndex

        mock_load_reg.return_value = RegistryIndex(registries=[])

        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["ksm", "registry", "remove", "myname"],
            ):
                main()
        assert exc_info.value.code == 0
        mock_ensure.assert_called_once()
        mock_run_rrm.assert_called_once()

    @patch("ksm.cli.load_registry_index")
    @patch("ksm.cli.ensure_ksm_dir")
    @patch(
        "ksm.commands.registry_ls.run_registry_ls",
        return_value=0,
    )
    def test_dispatch_registry_list_wires(
        self,
        mock_run_rls: MagicMock,
        mock_ensure: MagicMock,
        mock_load_reg: MagicMock,
    ) -> None:
        """'ksm registry list' wires to run_registry_ls.

        Req 7.4, 7.8: list dispatches correctly.
        """
        from ksm.registry import RegistryIndex

        mock_load_reg.return_value = RegistryIndex(registries=[])

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "registry", "list"]):
                main()
        assert exc_info.value.code == 0
        mock_ensure.assert_called_once()
        mock_run_rls.assert_called_once()

    @patch("ksm.cli._dispatch_registry")
    def test_registry_add_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm registry add <url>' dispatches.

        Req 7.1: registry add subcommand.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                [
                    "ksm",
                    "registry",
                    "add",
                    "https://example.com/r.git",
                ],
            ):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()

    @patch("ksm.cli._dispatch_registry")
    def test_registry_inspect_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm registry inspect myname' dispatches.

        Req 7.5: registry inspect subcommand.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["ksm", "registry", "inspect", "myname"],
            ):
                main()
        assert exc_info.value.code == 0
        mock_dispatch.assert_called_once()


class TestInteractiveFlag:
    """Test -i/--interactive flag on add and rm subcommands.

    Req 5.1–5.6: -i/--interactive replaces --display as the
    primary flag. --display is hidden from help and retained
    for backward compatibility.
    """

    @patch("ksm.cli._dispatch_add")
    def test_add_interactive_short_flag(self, mock_dispatch: MagicMock) -> None:
        """'ksm add -i' sets interactive=True.

        Req 5.1: -i flag parses correctly on add.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "add", "-i"]):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.interactive is True

    @patch("ksm.cli._dispatch_add")
    def test_add_interactive_long_flag(self, mock_dispatch: MagicMock) -> None:
        """'ksm add --interactive' sets interactive=True.

        Req 5.1: --interactive flag parses correctly on add.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "add", "--interactive"]):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.interactive is True

    @patch("ksm.cli._dispatch_add")
    def test_add_display_still_parses(self, mock_dispatch: MagicMock) -> None:
        """'ksm add --display' still parses for backward compat.

        Req 5.3: --display retained but hidden from help.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "add", "--display"]):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.display is True

    @patch("ksm.cli._dispatch_rm")
    def test_rm_interactive_short_flag(self, mock_dispatch: MagicMock) -> None:
        """'ksm rm -i' sets interactive=True.

        Req 5.2: -i flag parses correctly on rm.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "rm", "-i"]):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.interactive is True

    @patch("ksm.cli._dispatch_rm")
    def test_rm_interactive_long_flag(self, mock_dispatch: MagicMock) -> None:
        """'ksm rm --interactive' sets interactive=True.

        Req 5.2: --interactive flag parses correctly on rm.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "rm", "--interactive"]):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.interactive is True

    @patch("ksm.cli._dispatch_rm")
    def test_rm_display_still_parses(self, mock_dispatch: MagicMock) -> None:
        """'ksm rm --display' still parses for backward compat.

        Req 5.3: --display retained but hidden from help.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "rm", "--display"]):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.display is True

    def test_add_help_shows_interactive_not_display(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """'ksm add --help' shows --interactive, not --display.

        Req 5.4: --display hidden from help text.
        """
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "add", "--help"]):
                main()
        captured = capsys.readouterr()
        assert "--interactive" in captured.out or "-i" in captured.out
        assert "--display" not in captured.out

    def test_rm_help_shows_interactive_not_display(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """'ksm rm --help' shows --interactive, not --display.

        Req 5.4: --display hidden from help text.
        """
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "rm", "--help"]):
                main()
        captured = capsys.readouterr()
        assert "--interactive" in captured.out or "-i" in captured.out
        assert "--display" not in captured.out

    def test_remove_help_shows_interactive_not_display(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """'ksm remove --help' shows --interactive, not --display.

        Req 5.4: --display hidden from help on remove alias too.
        """
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "remove", "--help"]):
                main()
        captured = capsys.readouterr()
        assert "--interactive" in captured.out or "-i" in captured.out
        assert "--display" not in captured.out


class TestForceNameOnlyFlags:
    """Test --force, --name, and --only flag parsing.

    Req 6.1–6.3: -f/--force on registry add and add-registry.
    Req 11.1: --name on registry add and add-registry.
    Req 12.1–12.3: --only on add subparser.
    Req 12.6: --*-only flags hidden from help.
    """

    # --- --force on registry add ---

    @patch("ksm.cli._dispatch_registry")
    def test_registry_add_force_short(self, mock_dispatch: MagicMock) -> None:
        """'ksm registry add -f <url>' sets force=True.

        Req 6.1: -f short flag on registry add.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch(
                "sys.argv",
                ["ksm", "registry", "add", "-f", "https://x.com/r.git"],
            ):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.force is True

    @patch("ksm.cli._dispatch_registry")
    def test_registry_add_force_long(self, mock_dispatch: MagicMock) -> None:
        """'ksm registry add --force <url>' sets force=True.

        Req 6.1: --force long flag on registry add.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch(
                "sys.argv",
                [
                    "ksm",
                    "registry",
                    "add",
                    "--force",
                    "https://x.com/r.git",
                ],
            ):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.force is True

    @patch("ksm.cli._dispatch_registry")
    def test_registry_add_force_default_false(self, mock_dispatch: MagicMock) -> None:
        """'ksm registry add <url>' defaults force=False.

        Req 6.2: --force defaults to False.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch(
                "sys.argv",
                ["ksm", "registry", "add", "https://x.com/r.git"],
            ):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.force is False

    # --- --force on add-registry ---

    @patch("ksm.cli._dispatch_add_registry")
    def test_add_registry_force_short(self, mock_dispatch: MagicMock) -> None:
        """'ksm add-registry -f <url>' sets force=True.

        Req 6.3: -f on legacy add-registry.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch(
                "sys.argv",
                ["ksm", "add-registry", "-f", "https://x.com/r.git"],
            ):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.force is True

    @patch("ksm.cli._dispatch_add_registry")
    def test_add_registry_force_long(self, mock_dispatch: MagicMock) -> None:
        """'ksm add-registry --force <url>' sets force=True.

        Req 6.3: --force on legacy add-registry.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch(
                "sys.argv",
                [
                    "ksm",
                    "add-registry",
                    "--force",
                    "https://x.com/r.git",
                ],
            ):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.force is True

    # --- --name on registry add ---

    @patch("ksm.cli._dispatch_registry")
    def test_registry_add_name(self, mock_dispatch: MagicMock) -> None:
        """'ksm registry add --name foo <url>' sets name='foo'.

        Req 11.1: --name on registry add.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch(
                "sys.argv",
                [
                    "ksm",
                    "registry",
                    "add",
                    "--name",
                    "foo",
                    "https://x.com/r.git",
                ],
            ):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.name == "foo"

    @patch("ksm.cli._dispatch_registry")
    def test_registry_add_name_default_none(self, mock_dispatch: MagicMock) -> None:
        """'ksm registry add <url>' defaults name=None.

        Req 11.1: --name defaults to None.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch(
                "sys.argv",
                ["ksm", "registry", "add", "https://x.com/r.git"],
            ):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.name is None

    # --- --name on add-registry ---

    @patch("ksm.cli._dispatch_add_registry")
    def test_add_registry_name(self, mock_dispatch: MagicMock) -> None:
        """'ksm add-registry --name bar <url>' sets name='bar'.

        Req 11.1: --name on legacy add-registry.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch(
                "sys.argv",
                [
                    "ksm",
                    "add-registry",
                    "--name",
                    "bar",
                    "https://x.com/r.git",
                ],
            ):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.name == "bar"

    # --- --only on add ---

    @patch("ksm.cli._dispatch_add")
    def test_add_only_flag(self, mock_dispatch: MagicMock) -> None:
        """'ksm add --only skills mybundle' sets only='skills'.

        Req 12.1: --only on add subparser.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch(
                "sys.argv",
                ["ksm", "add", "--only", "skills", "mybundle"],
            ):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.only == "skills"

    @patch("ksm.cli._dispatch_add")
    def test_add_only_default_none(self, mock_dispatch: MagicMock) -> None:
        """'ksm add mybundle' defaults only=None.

        Req 12.1: --only defaults to None.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch(
                "sys.argv",
                ["ksm", "add", "mybundle"],
            ):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.only is None

    @patch("ksm.cli._dispatch_add")
    def test_add_only_comma_value(self, mock_dispatch: MagicMock) -> None:
        """'ksm add --only skills,hooks mybundle' passes raw string.

        Req 12.2: --only accepts comma-separated values.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch(
                "sys.argv",
                ["ksm", "add", "--only", "skills,hooks", "mybundle"],
            ):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.only == "skills,hooks"

    # --- --*-only hidden from help ---

    def test_add_help_hides_star_only_flags(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """'ksm add --help' does not show --skills-only etc.

        Req 12.6: --*-only flags hidden from help.
        """
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "add", "--help"]):
                main()
        captured = capsys.readouterr()
        assert "--only" in captured.out
        for hidden in (
            "--skills-only",
            "--agents-only",
            "--steering-only",
            "--hooks-only",
        ):
            assert hidden not in captured.out

    @patch("ksm.cli._dispatch_add")
    def test_add_star_only_flags_still_parse(self, mock_dispatch: MagicMock) -> None:
        """'ksm add --skills-only mybundle' still parses.

        Req 12.6: --*-only retained for backward compat.
        """
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch(
                "sys.argv",
                ["ksm", "add", "--skills-only", "mybundle"],
            ):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.skills_only is True
