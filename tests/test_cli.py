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
        for cmd in ("add", "ls", "sync", "registry", "rm"):
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
        """Error output for unknown command includes help hint."""
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "bogus-cmd"]):
                main()
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "bogus-cmd" in combined
        assert "ksm --help" in combined


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

    @patch("ksm.cli._dispatch_registry_add")
    def test_registry_add_dispatches(self, mock_dispatch: MagicMock) -> None:
        """'ksm registry add <url>' dispatches to registry add handler."""
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            with patch(
                "sys.argv",
                ["ksm", "registry", "add", "https://example.com/repo.git"],
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
                    "--only",
                    "skills",
                    "--only",
                    "hooks",
                    "mybundle",
                ],
            ):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.only == ["skills", "hooks"]


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
        ).filter(lambda s: s not in ("add", "ls", "sync", "registry", "rm"))
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
        # Error message includes the unknown command and help hint
        assert cmd in combined
        assert "ksm --help" in combined


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
        "ksm.commands.registry_add.run_registry_add",
        return_value=0,
    )
    def test_dispatch_registry_add_wires_correctly(
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
                ["ksm", "registry", "add", "https://x.com/r.git"],
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


# ---------------------------------------------------------------
# Task 2.1.6 — Property tests for parser changes
# ---------------------------------------------------------------

VALID_ONLY_TYPES = ["skills", "agents", "steering", "hooks"]


class TestProperty5:
    """Property 5: --only flag builds correct filter set.

    For any non-empty subset of valid subdirectory types,
    when provided as --only arguments, the resulting filter
    set shall equal exactly the provided subset.

    Validates: Requirements 5.1, 5.2, 5.3
    """

    @given(
        types=st.sets(
            st.sampled_from(VALID_ONLY_TYPES),
            min_size=1,
        )
    )
    def test_only_flag_builds_correct_filter_set(self, types: set[str]) -> None:
        """Feature: ux-review-fixes, Property 5."""
        from ksm.cli import _build_parser

        argv = ["add"]
        for t in sorted(types):
            argv.extend(["--only", t])
        argv.append("mybundle")

        parser = _build_parser()
        args = parser.parse_args(argv)
        assert set(args.only) == types


class TestProperty6:
    """Property 6: Invalid --only type produces error.

    For any string not in the valid set, --only shall
    produce an error message containing all valid types.

    Validates: Requirements 5.5
    """

    @given(
        bad_type=st.text(
            alphabet=st.characters(
                whitelist_categories=("Ll", "Lu", "Nd"),
            ),
            min_size=1,
            max_size=20,
        ).filter(lambda s: s not in VALID_ONLY_TYPES)
    )
    def test_invalid_only_type_produces_error(self, bad_type: str) -> None:
        """Feature: ux-review-fixes, Property 6."""
        import io
        from contextlib import redirect_stderr, redirect_stdout

        from ksm.cli import _build_parser

        parser = _build_parser()
        out = io.StringIO()
        err = io.StringIO()
        with pytest.raises(SystemExit) as exc_info:
            with redirect_stdout(out), redirect_stderr(err):
                parser.parse_args(["add", "--only", bad_type, "mybundle"])
        assert exc_info.value.code == 2
        combined = out.getvalue() + err.getvalue()
        for valid in VALID_ONLY_TYPES:
            assert valid in combined


class TestProperty32:
    """Property 32: Mutually exclusive -l/-g produces error.

    For any command accepting -l/-g (add, rm), providing
    both shall cause exit code 2 with 'not allowed with'.

    Validates: Requirements 27.1, 27.2, 27.3
    """

    @pytest.mark.parametrize(
        "cmd_argv",
        [
            ["add", "-l", "-g", "mybundle"],
            ["rm", "-l", "-g", "mybundle"],
        ],
    )
    def test_mutual_exclusion_l_g(self, cmd_argv: list[str]) -> None:
        """Feature: ux-review-fixes, Property 32."""
        import io
        from contextlib import redirect_stderr, redirect_stdout

        from ksm.cli import _build_parser

        parser = _build_parser()
        out = io.StringIO()
        err = io.StringIO()
        with pytest.raises(SystemExit) as exc_info:
            with redirect_stdout(out), redirect_stderr(err):
                parser.parse_args(cmd_argv)
        assert exc_info.value.code == 2
        combined = out.getvalue() + err.getvalue()
        assert "not allowed with" in combined


class TestProperty33:
    """Property 33: Global verbose/quiet mutual exclusion.

    Providing both --verbose and --quiet shall exit 2.
    Each alone shall set the correct flag.

    Validates: Requirements 28.1, 28.2, 28.5
    """

    def test_verbose_and_quiet_together_errors(self) -> None:
        """Feature: ux-review-fixes, Property 33."""
        import io
        from contextlib import redirect_stderr, redirect_stdout

        from ksm.cli import _build_parser

        parser = _build_parser()
        out = io.StringIO()
        err = io.StringIO()
        with pytest.raises(SystemExit) as exc_info:
            with redirect_stdout(out), redirect_stderr(err):
                parser.parse_args(["--verbose", "--quiet", "ls"])
        assert exc_info.value.code == 2

    def test_verbose_alone_sets_flag(self) -> None:
        from ksm.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["--verbose", "ls"])
        assert args.verbose is True
        assert args.quiet is False

    def test_quiet_alone_sets_flag(self) -> None:
        from ksm.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["--quiet", "ls"])
        assert args.quiet is True
        assert args.verbose is False


class TestDisplayDeprecation:
    """Test --display deprecation warning.

    When --display is used, a deprecation warning shall be
    printed to stderr and args.interactive shall be set True.

    Validates: Requirements 11.1, 11.2, 11.3
    """

    @patch("ksm.cli._dispatch_add")
    def test_display_flag_emits_deprecation_warning(
        self,
        mock_dispatch: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "add", "--display"]):
                main()
        captured = capsys.readouterr()
        assert "--display is deprecated" in captured.err
        assert "--interactive" in captured.err

    @patch("ksm.cli._dispatch_add")
    def test_display_flag_sets_interactive_true(
        self,
        mock_dispatch: MagicMock,
    ) -> None:
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "add", "--display"]):
                main()
        args = mock_dispatch.call_args[0][0]
        assert args.interactive is True

    @patch("ksm.cli._dispatch_rm")
    def test_display_on_rm_emits_deprecation(
        self,
        mock_dispatch: MagicMock,
        capsys: pytest.CaptureFixture,
    ) -> None:
        mock_dispatch.return_value = 0
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "rm", "--display"]):
                main()
        captured = capsys.readouterr()
        assert "--display is deprecated" in captured.err


# ---------------------------------------------------------------
# Task 2.2.3 — Tests for registry subcommand structure
# ---------------------------------------------------------------


class TestRegistrySubcommandStructure:
    """Test registry subcommand group structure.

    Parser accepts registry add/ls/rm/inspect.
    add-registry is rejected as unknown.
    registry with no subcommand shows help and exits 0.

    Validates: Requirements 4.1, 4.3, 4.4
    """

    def test_registry_add_accepted(self) -> None:
        from ksm.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["registry", "add", "https://example.com/repo.git"])
        assert args.command == "registry"
        assert args.registry_command == "add"
        assert args.git_url == "https://example.com/repo.git"

    def test_registry_ls_accepted(self) -> None:
        from ksm.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["registry", "ls"])
        assert args.command == "registry"
        assert args.registry_command == "ls"

    def test_registry_rm_accepted(self) -> None:
        from ksm.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["registry", "rm", "my-reg"])
        assert args.command == "registry"
        assert args.registry_command == "rm"
        assert args.name == "my-reg"

    def test_registry_inspect_accepted(self) -> None:
        from ksm.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["registry", "inspect", "my-reg"])
        assert args.command == "registry"
        assert args.registry_command == "inspect"
        assert args.name == "my-reg"

    def test_add_registry_rejected_as_unknown(self) -> None:
        """add-registry is no longer a valid command."""
        import io
        from contextlib import redirect_stderr, redirect_stdout

        from ksm.cli import _build_parser

        parser = _build_parser()
        out = io.StringIO()
        err = io.StringIO()
        with pytest.raises(SystemExit) as exc_info:
            with redirect_stdout(out), redirect_stderr(err):
                parser.parse_args(
                    [
                        "add-registry",
                        "https://example.com/repo.git",
                    ]
                )
        assert exc_info.value.code != 0

    def test_registry_no_subcommand_shows_help_exits_0(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """registry with no subcommand shows help, exits 0."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm", "registry"]):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "add" in captured.out
        assert "ls" in captured.out
        assert "rm" in captured.out
        assert "inspect" in captured.out


# ---------------------------------------------------------------
# Task 2.3.3 — Tests for help text
# ---------------------------------------------------------------


class TestProperty28:
    """Property 28: Help epilog contains examples for every subcommand.

    For every subcommand, the --help output shall contain an
    'examples' section with at least 2 concrete usage lines.

    Validates: Requirements 23.1, 23.2
    """

    SUBCOMMANDS = [
        ["add"],
        ["rm"],
        ["ls"],
        ["sync"],
        ["registry"],
        ["registry", "add"],
        ["registry", "ls"],
        ["registry", "rm"],
        ["registry", "inspect"],
    ]

    @pytest.mark.parametrize("subcmd", SUBCOMMANDS)
    def test_help_epilog_contains_examples(
        self,
        subcmd: list[str],
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Feature: ux-review-fixes, Property 28."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm"] + subcmd + ["--help"]):
                main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "examples:" in captured.out.lower()
        # Count lines starting with "ksm " in the examples
        example_lines = [
            line.strip()
            for line in captured.out.splitlines()
            if line.strip().startswith("ksm ")
        ]
        assert len(example_lines) >= 2, (
            f"Expected ≥2 example lines for {subcmd}, "
            f"got {len(example_lines)}: {example_lines}"
        )


class TestProperty40:
    """Property 40: Help examples are syntactically valid commands.

    Every example line starting with 'ksm ' (excluding lines
    with placeholder markers < and >) shall be parseable by
    the argparse parser without raising SystemExit.

    Validates: Requirements 35.1
    """

    SUBCOMMANDS_WITH_HELP = [
        ["add"],
        ["rm"],
        ["ls"],
        ["sync"],
        ["registry"],
        ["registry", "add"],
        ["registry", "ls"],
        ["registry", "rm"],
        ["registry", "inspect"],
    ]

    @pytest.mark.parametrize("subcmd", SUBCOMMANDS_WITH_HELP)
    def test_help_examples_round_trip(
        self,
        subcmd: list[str],
        capsys: pytest.CaptureFixture,
    ) -> None:
        """Feature: ux-review-fixes, Property 40."""
        from ksm.cli import _build_parser

        # Capture help output
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm"] + subcmd + ["--help"]):
                main()
        captured = capsys.readouterr()

        # Extract example lines
        example_lines = [
            line.strip()
            for line in captured.out.splitlines()
            if line.strip().startswith("ksm ")
        ]

        parser = _build_parser()
        for line in example_lines:
            # Skip lines with placeholders
            if "<" in line or ">" in line:
                continue
            argv = line.split()[1:]  # strip "ksm"
            # Should parse without error
            parser.parse_args(argv)


class TestCuratedHelp:
    """Test curated help screen when no command given.

    The curated help shall contain the tool name, version,
    grouped commands, and quick-start examples.

    Validates: Requirements 16.1, 16.2, 16.3
    """

    def test_curated_help_contains_tool_name_and_version(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["ksm"]):
                main()
        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "ksm" in captured.out
        assert __version__ in captured.out

    def test_curated_help_contains_commands(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm"]):
                main()
        captured = capsys.readouterr()
        for cmd in (
            "add",
            "rm",
            "ls",
            "sync",
            "registry add",
            "registry ls",
            "registry rm",
        ):
            assert cmd in captured.out

    def test_curated_help_contains_quick_start(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm"]):
                main()
        captured = capsys.readouterr()
        assert "Quick start:" in captured.out

    def test_curated_help_contains_footer(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm"]):
                main()
        captured = capsys.readouterr()
        assert "ksm <command> --help" in captured.out

    def test_top_level_help_flag_contains_footer(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        """--help output contains the footer hint (Req 23.3)."""
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["ksm", "--help"]):
                main()
        captured = capsys.readouterr()
        assert "ksm <command> --help" in captured.out
