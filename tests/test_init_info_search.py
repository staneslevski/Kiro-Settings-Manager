"""Tests for init, info, and search commands.

Property 27: Init creates .kiro/ directory
Property 21: Info output contains bundle metadata
Property 20: Search returns exactly matching bundles
Validates: Requirements 17, 18, 19
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ksm.manifest import Manifest, ManifestEntry
from ksm.registry import RegistryEntry, RegistryIndex


def _make_bundle_tree(
    registry_path: Path,
    bundle_names: list[str],
) -> None:
    """Create a minimal bundle tree on disk."""
    for bname in bundle_names:
        skills_dir = registry_path / bname / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "example.md").write_bytes(b"x")


def _make_registry_entry(
    name: str,
    local_path: str,
    url: str | None = None,
    is_default: bool = False,
) -> RegistryEntry:
    return RegistryEntry(
        name=name,
        url=url,
        local_path=local_path,
        is_default=is_default,
    )


# ── init ─────────────────────────────────────────────────────


class TestInit:
    """Tests for run_init."""

    def test_init_creates_kiro_dir(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Property 27: Init creates .kiro/ directory."""
        from ksm.commands.init import run_init

        args = argparse.Namespace()
        code = run_init(args, target_dir=tmp_path)

        assert code == 0
        assert (tmp_path / ".kiro").is_dir()
        captured = capsys.readouterr()
        assert "initialised" in captured.err.lower()

    def test_init_already_exists(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from ksm.commands.init import run_init

        (tmp_path / ".kiro").mkdir()
        args = argparse.Namespace()
        code = run_init(args, target_dir=tmp_path)

        assert code == 0
        captured = capsys.readouterr()
        assert "already" in captured.err.lower()

    def test_init_offers_selector_on_tty(
        self,
        tmp_path: Path,
    ) -> None:
        from ksm.commands.init import run_init

        reg_path = tmp_path / "reg"
        _make_bundle_tree(reg_path, ["b1"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("default", str(reg_path)),
            ]
        )
        manifest = Manifest(entries=[])

        with (
            patch("sys.stdin") as mock_stdin,
            patch(
                "ksm.commands.init.interactive_select",
                return_value=None,
            ) as mock_sel,
        ):
            mock_stdin.isatty.return_value = True
            args = argparse.Namespace()
            run_init(
                args,
                target_dir=tmp_path,
                registry_index=idx,
                manifest=manifest,
            )

        mock_sel.assert_called_once()

    def test_init_no_selector_when_not_tty(
        self,
        tmp_path: Path,
    ) -> None:
        from ksm.commands.init import run_init

        reg_path = tmp_path / "reg"
        _make_bundle_tree(reg_path, ["b1"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("default", str(reg_path)),
            ]
        )
        manifest = Manifest(entries=[])

        with (
            patch("sys.stdin") as mock_stdin,
            patch(
                "ksm.commands.init.interactive_select",
            ) as mock_sel,
        ):
            mock_stdin.isatty.return_value = False
            args = argparse.Namespace()
            run_init(
                args,
                target_dir=tmp_path,
                registry_index=idx,
                manifest=manifest,
            )

        mock_sel.assert_not_called()


# ── info ─────────────────────────────────────────────────────


class TestInfo:
    """Tests for run_info."""

    def test_info_shows_bundle_metadata(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Property 21: Info output contains bundle metadata."""
        from ksm.commands.info import run_info

        reg_path = tmp_path / "reg"
        _make_bundle_tree(reg_path, ["my-bundle"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("default", str(reg_path)),
            ]
        )
        manifest = Manifest(entries=[])

        args = argparse.Namespace(bundle_name="my-bundle")
        code = run_info(
            args,
            registry_index=idx,
            manifest=manifest,
        )

        assert code == 0
        out = capsys.readouterr().out
        assert "my-bundle" in out
        assert "default" in out
        assert "skills/" in out
        assert "no" in out.lower()  # not installed

    def test_info_shows_installed_status(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from ksm.commands.info import run_info

        reg_path = tmp_path / "reg"
        _make_bundle_tree(reg_path, ["my-bundle"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("default", str(reg_path)),
            ]
        )
        manifest = Manifest(
            entries=[
                ManifestEntry(
                    bundle_name="my-bundle",
                    source_registry="default",
                    scope="local",
                    installed_files=["f.md"],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                ),
            ]
        )

        args = argparse.Namespace(bundle_name="my-bundle")
        code = run_info(
            args,
            registry_index=idx,
            manifest=manifest,
        )

        assert code == 0
        out = capsys.readouterr().out
        assert "local" in out

    def test_info_not_found(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from ksm.commands.info import run_info

        reg_path = tmp_path / "reg"
        reg_path.mkdir()

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("default", str(reg_path)),
            ]
        )
        manifest = Manifest(entries=[])

        args = argparse.Namespace(bundle_name="nope")
        code = run_info(
            args,
            registry_index=idx,
            manifest=manifest,
        )

        assert code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()


# ── search ───────────────────────────────────────────────────


class TestSearch:
    """Tests for run_search."""

    def test_search_finds_matching_bundles(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from ksm.commands.search import run_search

        reg_path = tmp_path / "reg"
        _make_bundle_tree(reg_path, ["python-linter", "js-linter", "formatter"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("default", str(reg_path)),
            ]
        )

        args = argparse.Namespace(query="linter")
        code = run_search(args, registry_index=idx)

        assert code == 0
        out = capsys.readouterr().out
        assert "python-linter" in out
        assert "js-linter" in out
        assert "formatter" not in out

    def test_search_case_insensitive(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from ksm.commands.search import run_search

        reg_path = tmp_path / "reg"
        _make_bundle_tree(reg_path, ["MyBundle"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("default", str(reg_path)),
            ]
        )

        args = argparse.Namespace(query="mybundle")
        code = run_search(args, registry_index=idx)

        assert code == 0
        out = capsys.readouterr().out
        assert "MyBundle" in out

    def test_search_no_results(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from ksm.commands.search import run_search

        reg_path = tmp_path / "reg"
        _make_bundle_tree(reg_path, ["bundle-a"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("default", str(reg_path)),
            ]
        )

        args = argparse.Namespace(query="zzz-nope")
        code = run_search(args, registry_index=idx)

        assert code == 0
        captured = capsys.readouterr()
        assert "no bundles" in captured.err.lower()

    @given(
        query=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
            ),
            min_size=1,
            max_size=10,
        ),
    )
    def test_search_returns_exactly_matching_property(
        self,
        query: str,
    ) -> None:
        """Property 20: Search returns exactly matching bundles."""
        import tempfile

        from ksm.commands.search import run_search

        # Build a no_match name that cannot contain query
        # as a substring: use only chars NOT in the query.
        query_lower = set(query.lower())
        pool = [c for c in "abcdefghijklmnopqrstuvwxyz" if c not in query_lower]
        if len(pool) < 3:
            # Query covers almost all letters; skip
            # this example — can't build a safe name.
            from hypothesis import assume

            assume(False)
        no_match = "".join(pool[:5])

        with tempfile.TemporaryDirectory() as td:
            reg_path = Path(td) / "reg"
            # Create bundles: one that matches, one that doesn't
            match_name = f"prefix-{query}-suffix"
            _make_bundle_tree(reg_path, [match_name, no_match])

            idx = RegistryIndex(
                registries=[
                    _make_registry_entry("default", str(reg_path)),
                ]
            )

            import io
            from unittest.mock import patch as mp

            buf = io.StringIO()
            err_buf = io.StringIO()

            def fake_print(*a: object, **kw: object) -> None:
                target = kw.get("file", None)
                import sys

                if target is sys.stderr:
                    if a:
                        err_buf.write(str(a[0]))
                else:
                    if a:
                        buf.write(str(a[0]))

            args = argparse.Namespace(query=query)
            with mp(
                "ksm.commands.search.print",
                side_effect=fake_print,
            ):
                run_search(args, registry_index=idx)

            out = buf.getvalue()
            assert match_name in out
            assert no_match not in out


# ── info color ───────────────────────────────────────────────


class TestInfoColor:
    """Tests for color usage in run_info output.

    **Validates: Requirements 9.2, 9.3**
    """

    def test_installed_scopes_wrapped_in_green(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Property 25: info installed status uses green
        when installed."""
        from ksm.commands.info import run_info

        reg_path = tmp_path / "reg"
        _make_bundle_tree(reg_path, ["my-bundle"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("default", str(reg_path)),
            ]
        )
        manifest = Manifest(
            entries=[
                ManifestEntry(
                    bundle_name="my-bundle",
                    source_registry="default",
                    scope="local",
                    installed_files=["f.md"],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                ),
            ]
        )

        args = argparse.Namespace(bundle_name="my-bundle")
        with patch("ksm.color._color_enabled", return_value=True):
            code = run_info(
                args,
                registry_index=idx,
                manifest=manifest,
            )

        assert code == 0
        out = capsys.readouterr().out
        # Green ANSI wrapping around the scope string
        assert "\033[32mlocal\033[0m" in out

    def test_installed_scopes_no_color_when_no_color_set(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Req 9.3: NO_COLOR suppresses ANSI in info output."""
        from ksm.commands.info import run_info

        monkeypatch.setenv("NO_COLOR", "1")

        reg_path = tmp_path / "reg"
        _make_bundle_tree(reg_path, ["my-bundle"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("default", str(reg_path)),
            ]
        )
        manifest = Manifest(
            entries=[
                ManifestEntry(
                    bundle_name="my-bundle",
                    source_registry="default",
                    scope="local",
                    installed_files=["f.md"],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                ),
            ]
        )

        args = argparse.Namespace(bundle_name="my-bundle")
        code = run_info(
            args,
            registry_index=idx,
            manifest=manifest,
        )

        assert code == 0
        out = capsys.readouterr().out
        assert "\033[" not in out
        assert "local" in out

    def test_not_installed_uses_dim(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Verify not-installed status wraps 'no' in dim."""
        from ksm.commands.info import run_info

        reg_path = tmp_path / "reg"
        _make_bundle_tree(reg_path, ["my-bundle"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("default", str(reg_path)),
            ]
        )
        manifest = Manifest(entries=[])

        args = argparse.Namespace(bundle_name="my-bundle")
        with patch("ksm.color._color_enabled", return_value=True):
            code = run_info(
                args,
                registry_index=idx,
                manifest=manifest,
            )

        assert code == 0
        out = capsys.readouterr().out
        # Dim ANSI wrapping around "no"
        assert "\033[2mno\033[0m" in out

    def test_bundle_name_uses_bold(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Verify bundle name is wrapped in bold."""
        from ksm.commands.info import run_info

        reg_path = tmp_path / "reg"
        _make_bundle_tree(reg_path, ["my-bundle"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("default", str(reg_path)),
            ]
        )
        manifest = Manifest(entries=[])

        args = argparse.Namespace(bundle_name="my-bundle")
        with patch("ksm.color._color_enabled", return_value=True):
            code = run_info(
                args,
                registry_index=idx,
                manifest=manifest,
            )

        assert code == 0
        out = capsys.readouterr().out
        assert "\033[1mmy-bundle\033[0m" in out

    def test_registry_name_uses_dim(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Verify registry name is wrapped in dim."""
        from ksm.commands.info import run_info

        reg_path = tmp_path / "reg"
        _make_bundle_tree(reg_path, ["my-bundle"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("default", str(reg_path)),
            ]
        )
        manifest = Manifest(entries=[])

        args = argparse.Namespace(bundle_name="my-bundle")
        with patch("ksm.color._color_enabled", return_value=True):
            code = run_info(
                args,
                registry_index=idx,
                manifest=manifest,
            )

        assert code == 0
        out = capsys.readouterr().out
        assert "\033[2mdefault\033[0m" in out


# ── search color ─────────────────────────────────────────────


class TestSearchColor:
    """Tests for color usage in search output.

    **Validates: Requirements 9.1, 9.3**
    """

    def test_bundle_name_uses_bold(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 9.1: search wraps bundle names in bold."""
        from ksm.commands.search import run_search

        reg_path = tmp_path / "reg"
        _make_bundle_tree(reg_path, ["my-bundle"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("default", str(reg_path)),
            ]
        )
        args = argparse.Namespace(query="my-bundle")
        with patch("ksm.color._color_enabled", return_value=True):
            code = run_search(args, registry_index=idx)

        assert code == 0
        out = capsys.readouterr().out
        assert "\033[1mmy-bundle\033[0m" in out

    def test_registry_name_and_subdirs_use_dim(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 9.1: search wraps registry name and subdirs
        in dim."""
        from ksm.commands.search import run_search

        reg_path = tmp_path / "reg"
        _make_bundle_tree(reg_path, ["my-bundle"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("default", str(reg_path)),
            ]
        )
        args = argparse.Namespace(query="my-bundle")
        with patch("ksm.color._color_enabled", return_value=True):
            code = run_search(args, registry_index=idx)

        assert code == 0
        out = capsys.readouterr().out
        # Registry name wrapped in dim
        assert "\033[2m(default)\033[0m" in out
        # Subdirectory list wrapped in dim
        assert "\033[2mskills\033[0m" in out

    def test_no_color_suppresses_ansi(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Req 9.3: NO_COLOR suppresses ANSI in search."""
        from ksm.commands.search import run_search

        monkeypatch.setenv("NO_COLOR", "1")

        reg_path = tmp_path / "reg"
        _make_bundle_tree(reg_path, ["my-bundle"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("default", str(reg_path)),
            ]
        )
        args = argparse.Namespace(query="my-bundle")
        code = run_search(args, registry_index=idx)

        assert code == 0
        out = capsys.readouterr().out
        assert "\033[" not in out
        assert "my-bundle" in out
        assert "default" in out
