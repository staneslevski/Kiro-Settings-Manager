"""Tests for registry ls, rm, and inspect commands.

Property 23: Registry ls output contains all metadata
Property 24: Registry rm removes exactly the named registry
Property 25: Registry not-found error lists registered names
Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5
"""

import argparse
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ksm.registry import RegistryEntry, RegistryIndex


def _make_registry_entry(
    name: str,
    url: str | None,
    local_path: str,
    is_default: bool = False,
) -> RegistryEntry:
    return RegistryEntry(
        name=name,
        url=url,
        local_path=local_path,
        is_default=is_default,
    )


def _make_bundle_tree(
    registry_path: Path,
    bundle_names: list[str],
) -> None:
    """Create a minimal bundle tree on disk."""
    for bname in bundle_names:
        skills_dir = registry_path / bname / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "example.md").write_bytes(b"x")


# ── registry ls ──────────────────────────────────────────────


class TestRegistryLs:
    """Tests for run_registry_ls."""

    def test_empty_registries_prints_to_stderr(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from ksm.commands.registry_ls import run_registry_ls

        idx = RegistryIndex(registries=[])
        args = argparse.Namespace()
        code = run_registry_ls(args, registry_index=idx)

        assert code == 0
        captured = capsys.readouterr()
        assert "no registries" in captured.err.lower()

    def test_ls_shows_name_url_path_bundle_count(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Property 23: Registry ls output contains all metadata."""
        from ksm.commands.registry_ls import run_registry_ls

        reg_path = tmp_path / "my-reg"
        _make_bundle_tree(reg_path, ["bundle-a", "bundle-b"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "my-reg",
                    "https://example.com/repo.git",
                    str(reg_path),
                ),
            ]
        )
        args = argparse.Namespace()
        code = run_registry_ls(args, registry_index=idx)

        assert code == 0
        out = capsys.readouterr().out
        assert "my-reg" in out
        assert "https://example.com/repo.git" in out
        assert str(reg_path) in out
        assert "2 bundles" in out

    def test_ls_local_registry_shows_local_label(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from ksm.commands.registry_ls import run_registry_ls

        reg_path = tmp_path / "default"
        _make_bundle_tree(reg_path, ["b1"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "default",
                    None,
                    str(reg_path),
                    is_default=True,
                ),
            ]
        )
        args = argparse.Namespace()
        code = run_registry_ls(args, registry_index=idx)

        assert code == 0
        out = capsys.readouterr().out
        assert "default" in out
        assert "1 bundle" in out

    @given(
        name=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
            ),
            min_size=1,
            max_size=20,
        ),
        url=st.text(min_size=5, max_size=50),
    )
    def test_ls_output_contains_all_metadata_property(
        self,
        name: str,
        url: str,
    ) -> None:
        """Property 23: ls output contains name, URL, path."""
        import io
        import tempfile
        from unittest.mock import patch

        from ksm.commands.registry_ls import run_registry_ls

        with tempfile.TemporaryDirectory() as td:
            reg_path = Path(td) / "reg"
            reg_path.mkdir(parents=True, exist_ok=True)

            idx = RegistryIndex(
                registries=[
                    _make_registry_entry(name, url, str(reg_path)),
                ]
            )
            args = argparse.Namespace()
            buf = io.StringIO()
            with patch(
                "builtins.print",
                side_effect=lambda *a, **kw: buf.write(str(a[0]) + "\n") if a else None,
            ):
                run_registry_ls(args, registry_index=idx)

            out = buf.getvalue()
            assert name in out
            assert url in out
            assert str(reg_path) in out


# ── registry rm ──────────────────────────────────────────────


class TestRegistryRm:
    """Tests for run_registry_rm."""

    def test_rm_removes_named_registry(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Property 24: rm removes exactly the named registry."""
        from ksm.commands.registry_rm import run_registry_rm

        cache_path = tmp_path / "cache" / "extra"
        cache_path.mkdir(parents=True)
        (cache_path / "file.txt").write_bytes(b"x")

        idx_path = tmp_path / "registries.json"

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "default",
                    None,
                    str(tmp_path / "default"),
                    is_default=True,
                ),
                _make_registry_entry(
                    "extra",
                    "https://example.com/extra.git",
                    str(cache_path),
                ),
            ]
        )

        args = argparse.Namespace(registry_name="extra")
        code = run_registry_rm(
            args,
            registry_index=idx,
            registry_index_path=idx_path,
        )

        assert code == 0
        assert len(idx.registries) == 1
        assert idx.registries[0].name == "default"
        # Cache cleaned
        assert not cache_path.exists()
        captured = capsys.readouterr()
        assert "removed" in captured.err.lower()

    def test_rm_blocks_default_removal(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from ksm.commands.registry_rm import run_registry_rm

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "default",
                    None,
                    str(tmp_path / "default"),
                    is_default=True,
                ),
            ]
        )
        args = argparse.Namespace(registry_name="default")
        code = run_registry_rm(
            args,
            registry_index=idx,
            registry_index_path=tmp_path / "r.json",
        )

        assert code == 1
        assert len(idx.registries) == 1
        captured = capsys.readouterr()
        assert "cannot remove" in captured.err.lower()

    def test_rm_not_found_lists_registered_names(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Property 25: not-found error lists registered names."""
        from ksm.commands.registry_rm import run_registry_rm

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "default",
                    None,
                    str(tmp_path),
                    is_default=True,
                ),
                _make_registry_entry(
                    "extra",
                    "https://x.com/e.git",
                    str(tmp_path / "e"),
                ),
            ]
        )
        args = argparse.Namespace(registry_name="nope")
        code = run_registry_rm(
            args,
            registry_index=idx,
            registry_index_path=tmp_path / "r.json",
        )

        assert code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()
        assert "default" in captured.err
        assert "extra" in captured.err

    @given(
        names=st.lists(
            st.text(
                alphabet=st.characters(
                    whitelist_categories=("L", "N"),
                ),
                min_size=1,
                max_size=10,
            ),
            min_size=1,
            max_size=5,
            unique=True,
        ),
    )
    def test_rm_removes_exactly_one_property(
        self,
        names: list[str],
    ) -> None:
        """Property 24: rm removes exactly the named registry."""
        import tempfile

        from ksm.commands.registry_rm import run_registry_rm

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            entries = [
                _make_registry_entry(n, f"https://{n}", str(tmp / n)) for n in names
            ]
            idx = RegistryIndex(registries=list(entries))
            target = names[0]

            args = argparse.Namespace(registry_name=target)
            code = run_registry_rm(
                args,
                registry_index=idx,
                registry_index_path=tmp / "r.json",
            )

            assert code == 0
            remaining = {e.name for e in idx.registries}
            assert target not in remaining
            assert remaining == set(names[1:])


# ── registry inspect ─────────────────────────────────────────


class TestRegistryInspect:
    """Tests for run_registry_inspect."""

    def test_inspect_shows_bundles_and_subdirs(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from ksm.commands.registry_inspect import (
            run_registry_inspect,
        )

        reg_path = tmp_path / "my-reg"
        _make_bundle_tree(reg_path, ["bundle-a"])
        # Add a hooks subdir too
        hooks_dir = reg_path / "bundle-a" / "hooks"
        hooks_dir.mkdir()
        (hooks_dir / "hook1.json").write_bytes(b"{}")

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "my-reg",
                    "https://example.com/r.git",
                    str(reg_path),
                ),
            ]
        )
        args = argparse.Namespace(registry_name="my-reg")
        code = run_registry_inspect(args, registry_index=idx)

        assert code == 0
        out = capsys.readouterr().out
        assert "my-reg" in out
        assert "bundle-a" in out
        assert "skills/" in out
        assert "hooks/" in out

    def test_inspect_not_found_lists_registered(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Property 25: not-found error lists registered names."""
        from ksm.commands.registry_inspect import (
            run_registry_inspect,
        )

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("alpha", None, str(tmp_path), True),
            ]
        )
        args = argparse.Namespace(registry_name="nope")
        code = run_registry_inspect(args, registry_index=idx)

        assert code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()
        assert "alpha" in captured.err

    def test_inspect_empty_registry(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from ksm.commands.registry_inspect import (
            run_registry_inspect,
        )

        reg_path = tmp_path / "empty-reg"
        reg_path.mkdir()

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("empty-reg", None, str(reg_path)),
            ]
        )
        args = argparse.Namespace(registry_name="empty-reg")
        code = run_registry_inspect(args, registry_index=idx)

        assert code == 0
        captured = capsys.readouterr()
        assert "no bundles" in captured.err.lower()
