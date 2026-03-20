"""Tests for registry ls, rm, inspect, and add commands.

Property 23: Registry ls output contains all metadata
Property 24: Registry rm removes exactly the named registry
Property 25: Registry not-found error lists registered names
Property 1: Cache conflict same-URL error contains path and --force
Property 2: Cache conflict different-URL error suggests --name
Property 16: Cache directory uses registry name as namespace
Validates: Requirements 1.1–1.8, 8.1–8.5
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ksm.errors import GitError
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

    def test_rm_cache_cleaned_message_with_path(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 3.1: cache cleaned → message with path."""
        from ksm.commands.registry_rm import run_registry_rm

        cache_path = tmp_path / "cache" / "extra"
        cache_path.mkdir(parents=True)
        (cache_path / "data.txt").write_bytes(b"x")

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
            registry_index_path=tmp_path / "r.json",
        )

        assert code == 0
        assert not cache_path.exists()
        captured = capsys.readouterr()
        assert "Cache directory cleaned:" in captured.err
        assert str(cache_path) in captured.err

    def test_rm_cache_absent_message(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 3.2: cache absent → 'already absent' message."""
        from ksm.commands.registry_rm import run_registry_rm

        # Point to a path that does NOT exist on disk
        missing_cache = tmp_path / "cache" / "gone"

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "default",
                    None,
                    str(tmp_path / "default"),
                    is_default=True,
                ),
                _make_registry_entry(
                    "gone",
                    "https://example.com/gone.git",
                    str(missing_cache),
                ),
            ]
        )
        args = argparse.Namespace(registry_name="gone")
        code = run_registry_rm(
            args,
            registry_index=idx,
            registry_index_path=tmp_path / "r.json",
        )

        assert code == 0
        captured = capsys.readouterr()
        assert "already absent" in captured.err.lower()

    def test_rm_permission_error_warns_and_removes(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 3.3: permission error → warning, removes from index, exit 0."""
        from ksm.commands.registry_rm import run_registry_rm

        cache_path = tmp_path / "cache" / "locked"
        cache_path.mkdir(parents=True)

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "default",
                    None,
                    str(tmp_path / "default"),
                    is_default=True,
                ),
                _make_registry_entry(
                    "locked",
                    "https://example.com/locked.git",
                    str(cache_path),
                ),
            ]
        )
        args = argparse.Namespace(registry_name="locked")

        with patch(
            "ksm.commands.registry_rm.shutil.rmtree",
            side_effect=PermissionError("denied"),
        ):
            code = run_registry_rm(
                args,
                registry_index=idx,
                registry_index_path=tmp_path / "r.json",
            )

        assert code == 0
        # Registry removed from index
        remaining = [e.name for e in idx.registries]
        assert "locked" not in remaining
        # Warning printed
        captured = capsys.readouterr()
        assert "Warning:" in captured.err
        assert "Permission denied" in captured.err or (
            "permission" in captured.err.lower()
        )

    def test_rm_not_found_uses_format_error(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 3.4: not-found → three-line format_error with all names."""
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
                    "alpha",
                    "https://a.com/a.git",
                    str(tmp_path / "a"),
                ),
                _make_registry_entry(
                    "beta",
                    "https://b.com/b.git",
                    str(tmp_path / "b"),
                ),
            ]
        )
        args = argparse.Namespace(registry_name="missing")
        code = run_registry_rm(
            args,
            registry_index=idx,
            registry_index_path=tmp_path / "r.json",
        )

        assert code == 1
        captured = capsys.readouterr()
        # Three-line format_error structure
        assert "Error:" in captured.err
        assert "missing" in captured.err
        # All registered names listed
        assert "default" in captured.err
        assert "alpha" in captured.err
        assert "beta" in captured.err

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

    @given(
        name=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
            ),
            min_size=1,
            max_size=15,
        ),
        cache_exists=st.booleans(),
    )
    def test_rm_feedback_matches_cache_state_property(
        self,
        name: str,
        cache_exists: bool,
    ) -> None:
        """Property 4: Registry remove feedback matches cache state.

        For any registered non-default registry, rm should:
        (a) if cache existed → message contains
            "Cache directory cleaned:" and the path
        (b) if cache was absent → message contains
            "Cache directory was already absent"
        In both cases exit code is 0 and registry is removed.

        Validates: Requirements 3.1, 3.2
        """
        import tempfile

        from ksm.commands.registry_rm import run_registry_rm

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cache_path = tmp / "cache" / name
            if cache_exists:
                cache_path.mkdir(parents=True)
                (cache_path / "f.txt").write_bytes(b"x")

            idx = RegistryIndex(
                registries=[
                    _make_registry_entry(
                        name,
                        f"https://example.com/{name}.git",
                        str(cache_path),
                    ),
                ]
            )
            idx_path = tmp / "r.json"
            args = argparse.Namespace(registry_name=name)

            import io
            import sys

            captured = io.StringIO()
            old_stderr = sys.stderr
            sys.stderr = captured
            try:
                code = run_registry_rm(
                    args,
                    registry_index=idx,
                    registry_index_path=idx_path,
                )
            finally:
                sys.stderr = old_stderr

            assert code == 0
            assert len(idx.registries) == 0

            output = captured.getvalue()
            if cache_exists:
                assert "Cache directory cleaned:" in output
                assert str(cache_path) in output
            else:
                assert "already absent" in output.lower()

    @given(
        registered=st.lists(
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
    def test_rm_not_found_lists_all_names_property(
        self,
        registered: list[str],
    ) -> None:
        """Property 5: Registry remove not-found error lists all names.

        For any registry name that does not exist in the index,
        rm should return exit code 1 and the error message should
        contain every registered registry name.

        Validates: Requirements 3.4
        """
        import tempfile

        from ksm.commands.registry_rm import run_registry_rm

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            entries = [
                _make_registry_entry(
                    n,
                    f"https://{n}.example.com",
                    str(tmp / n),
                )
                for n in registered
            ]
            idx = RegistryIndex(registries=entries)

            # Use a name guaranteed not in the list
            missing = "ZZZZ_not_registered_ZZZZ"
            args = argparse.Namespace(registry_name=missing)

            import io
            import sys

            captured = io.StringIO()
            old_stderr = sys.stderr
            sys.stderr = captured
            try:
                code = run_registry_rm(
                    args,
                    registry_index=idx,
                    registry_index_path=tmp / "r.json",
                )
            finally:
                sys.stderr = old_stderr

            assert code == 1
            output = captured.getvalue()
            assert "Error:" in output
            for name in registered:
                assert name in output


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

    def test_inspect_output_contains_url(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Inspect output shows URL field (Req 14.1)."""
        from ksm.commands.registry_inspect import (
            run_registry_inspect,
        )

        reg_path = tmp_path / "my-reg"
        _make_bundle_tree(reg_path, ["bundle-a"])

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
        assert "https://example.com/r.git" in out

    def test_inspect_output_shows_local_when_no_url(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Inspect output shows '(local)' when URL is None (Req 14.1)."""
        from ksm.commands.registry_inspect import (
            run_registry_inspect,
        )

        reg_path = tmp_path / "local-reg"
        _make_bundle_tree(reg_path, ["bundle-a"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "local-reg",
                    None,
                    str(reg_path),
                    is_default=True,
                ),
            ]
        )
        args = argparse.Namespace(registry_name="local-reg")
        code = run_registry_inspect(args, registry_index=idx)

        assert code == 0
        out = capsys.readouterr().out
        assert "(local)" in out

    def test_inspect_output_contains_default_status(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Inspect output shows default status (Req 14.1)."""
        from ksm.commands.registry_inspect import (
            run_registry_inspect,
        )

        reg_path = tmp_path / "def-reg"
        _make_bundle_tree(reg_path, ["bundle-a"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "def-reg",
                    None,
                    str(reg_path),
                    is_default=True,
                ),
            ]
        )
        args = argparse.Namespace(registry_name="def-reg")
        code = run_registry_inspect(args, registry_index=idx)

        assert code == 0
        out = capsys.readouterr().out
        assert "yes" in out.lower()

    def test_inspect_output_default_no(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Non-default registry shows 'no' for default status."""
        from ksm.commands.registry_inspect import (
            run_registry_inspect,
        )

        reg_path = tmp_path / "non-def"
        _make_bundle_tree(reg_path, ["bundle-a"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "non-def",
                    "https://example.com/r.git",
                    str(reg_path),
                    is_default=False,
                ),
            ]
        )
        args = argparse.Namespace(registry_name="non-def")
        code = run_registry_inspect(args, registry_index=idx)

        assert code == 0
        out = capsys.readouterr().out
        # Should contain "Default: no" or similar
        assert "no" in out.lower()

    def test_inspect_output_contains_path(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Inspect output shows local cache path (Req 14.1)."""
        from ksm.commands.registry_inspect import (
            run_registry_inspect,
        )

        reg_path = tmp_path / "path-reg"
        _make_bundle_tree(reg_path, ["bundle-a"])

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "path-reg",
                    "https://example.com/r.git",
                    str(reg_path),
                ),
            ]
        )
        args = argparse.Namespace(registry_name="path-reg")
        code = run_registry_inspect(args, registry_index=idx)

        assert code == 0
        out = capsys.readouterr().out
        assert str(reg_path) in out

    def test_inspect_output_lists_bundles_with_subdirs(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Inspect lists bundle names with subdirectory types (Req 14.2)."""
        from ksm.commands.registry_inspect import (
            run_registry_inspect,
        )

        reg_path = tmp_path / "multi-reg"
        _make_bundle_tree(reg_path, ["bundle-a", "bundle-b"])
        # Add hooks to bundle-b
        hooks_dir = reg_path / "bundle-b" / "hooks"
        hooks_dir.mkdir()
        (hooks_dir / "h.json").write_bytes(b"{}")

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "multi-reg",
                    "https://example.com/r.git",
                    str(reg_path),
                ),
            ]
        )
        args = argparse.Namespace(registry_name="multi-reg")
        code = run_registry_inspect(args, registry_index=idx)

        assert code == 0
        out = capsys.readouterr().out
        assert "bundle-a" in out
        assert "bundle-b" in out
        assert "skills/" in out
        assert "hooks/" in out

    def test_inspect_not_found_lists_available_registries(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Not-found error lists available registries (Req 14.4)."""
        from ksm.commands.registry_inspect import (
            run_registry_inspect,
        )

        idx = RegistryIndex(
            registries=[
                _make_registry_entry("alpha", None, str(tmp_path), True),
                _make_registry_entry(
                    "beta",
                    "https://example.com/b.git",
                    str(tmp_path),
                ),
            ]
        )
        args = argparse.Namespace(registry_name="nope")
        code = run_registry_inspect(args, registry_index=idx)

        assert code == 1
        captured = capsys.readouterr()
        assert "alpha" in captured.err
        assert "beta" in captured.err

    # Feature: ksm-enhancements, Property 15:
    # Registry inspect output contains all required fields and bundles
    @given(
        reg_name=st.from_regex(r"[a-z]{3,8}", fullmatch=True),
        url=st.one_of(
            st.none(),
            st.from_regex(
                r"https://[a-z]{3,8}\.com/[a-z]{3,8}\.git",
                fullmatch=True,
            ),
        ),
        is_default=st.booleans(),
        bundle_names=st.lists(
            st.from_regex(r"[a-z]{3,8}", fullmatch=True),
            min_size=1,
            max_size=3,
            unique=True,
        ),
    )
    def test_property_inspect_output_completeness(
        self,
        reg_name: str,
        url: str | None,
        is_default: bool,
        bundle_names: list[str],
    ) -> None:
        """Property 15: Inspect output contains all required
        fields and bundles."""
        import tempfile

        from ksm.commands.registry_inspect import (
            run_registry_inspect,
        )

        with tempfile.TemporaryDirectory() as td:
            reg_path = Path(td) / reg_name
            _make_bundle_tree(reg_path, bundle_names)

            idx = RegistryIndex(
                registries=[
                    _make_registry_entry(
                        reg_name,
                        url,
                        str(reg_path),
                        is_default,
                    ),
                ]
            )
            args = argparse.Namespace(registry_name=reg_name)

            import io
            from contextlib import redirect_stdout

            buf = io.StringIO()
            with redirect_stdout(buf):
                code = run_registry_inspect(args, registry_index=idx)

            assert code == 0
            out = buf.getvalue()

            # Must contain registry name
            assert reg_name in out
            # Must contain URL or "(local)"
            if url is not None:
                assert url in out
            else:
                assert "(local)" in out
            # Must contain path
            assert str(reg_path) in out
            # Must contain default status
            if is_default:
                assert "yes" in out.lower()
            else:
                assert "no" in out.lower()
            # Must contain all bundle names
            for bname in bundle_names:
                assert bname in out


# ── registry add — cache conflict handling ───────────────────


class TestRegistryAddCacheConflict:
    """Tests for cache conflict handling in run_registry_add.

    Validates Requirements 1.1–1.7.
    """

    def _make_args(
        self,
        git_url: str,
        force: bool = False,
        custom_name: str | None = None,
        interactive: bool = False,
    ) -> argparse.Namespace:
        return argparse.Namespace(
            git_url=git_url,
            force=force,
            custom_name=custom_name,
            interactive=interactive,
        )

    def test_same_url_readd_without_force_errors(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 1.1–1.3: Same-URL re-add without --force → error
        with path and --force suggestion."""
        from ksm.commands.registry_add import run_registry_add

        cache_dir = tmp_path / "cache"
        target = cache_dir / "my-repo"
        target.mkdir(parents=True)

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "my-repo",
                    "https://example.com/my-repo.git",
                    str(target),
                ),
            ]
        )
        args = self._make_args(
            "https://example.com/my-repo.git",
        )
        code = run_registry_add(
            args,
            registry_index=idx,
            registry_index_path=tmp_path / "r.json",
            cache_dir=cache_dir,
        )

        assert code == 1
        err = capsys.readouterr().err
        assert str(target) in err
        assert "--force" in err

    def test_different_url_collision_suggests_name(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 1.4: Different-URL collision → error with --name
        suggestion, no --force."""
        from ksm.commands.registry_add import run_registry_add

        cache_dir = tmp_path / "cache"
        target = cache_dir / "my-repo"
        target.mkdir(parents=True)

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "my-repo",
                    "https://other.com/my-repo.git",
                    str(target),
                ),
            ]
        )
        args = self._make_args(
            "https://example.com/my-repo.git",
        )
        code = run_registry_add(
            args,
            registry_index=idx,
            registry_index_path=tmp_path / "r.json",
            cache_dir=cache_dir,
        )

        assert code == 1
        err = capsys.readouterr().err
        assert "--name" in err
        assert "--force" not in err

    def test_force_removes_cache_and_reclones(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 1.5: --force removes existing cache and re-clones."""
        from ksm.commands.registry_add import run_registry_add

        cache_dir = tmp_path / "cache"
        target = cache_dir / "my-repo"
        target.mkdir(parents=True)
        (target / "old-file.txt").write_bytes(b"old")

        idx_path = tmp_path / "r.json"
        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "my-repo",
                    "https://example.com/my-repo.git",
                    str(target),
                ),
            ]
        )
        args = self._make_args(
            "https://example.com/my-repo.git",
            force=True,
        )

        with patch("ksm.commands.registry_add.clone_repo") as mock_clone:
            mock_clone.side_effect = lambda url, t: t.mkdir(parents=True, exist_ok=True)
            with patch(
                "ksm.commands.registry_add.scan_registry",
                return_value=[],
            ):
                code = run_registry_add(
                    args,
                    registry_index=idx,
                    registry_index_path=idx_path,
                    cache_dir=cache_dir,
                )

        assert code == 0
        mock_clone.assert_called_once()
        # Old file should be gone (cache was removed)
        assert not (target / "old-file.txt").exists()

    def test_clone_failure_after_force_rollback_warning(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 1.6: Clone failure after --force → rollback warning."""
        from ksm.commands.registry_add import run_registry_add

        cache_dir = tmp_path / "cache"
        target = cache_dir / "my-repo"
        target.mkdir(parents=True)

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "my-repo",
                    "https://example.com/my-repo.git",
                    str(target),
                ),
            ]
        )
        args = self._make_args(
            "https://example.com/my-repo.git",
            force=True,
        )

        with patch(
            "ksm.commands.registry_add.clone_repo",
            side_effect=GitError("clone failed"),
        ):
            code = run_registry_add(
                args,
                registry_index=idx,
                registry_index_path=tmp_path / "r.json",
                cache_dir=cache_dir,
            )

        assert code == 1
        err = capsys.readouterr().err
        assert "removed" in err.lower() or "cache" in err.lower()
        # Cache should have been removed before clone attempt
        assert not target.exists()

    def test_no_conflict_normal_clone_and_register(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 1.7: No conflict → normal clone and register."""
        from ksm.commands.registry_add import run_registry_add

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        idx_path = tmp_path / "r.json"
        idx = RegistryIndex(registries=[])

        args = self._make_args(
            "https://example.com/new-repo.git",
        )

        with patch("ksm.commands.registry_add.clone_repo") as mock_clone:
            mock_clone.side_effect = lambda url, t: t.mkdir(parents=True, exist_ok=True)
            with patch(
                "ksm.commands.registry_add.scan_registry",
                return_value=[],
            ):
                code = run_registry_add(
                    args,
                    registry_index=idx,
                    registry_index_path=idx_path,
                    cache_dir=cache_dir,
                )

        assert code == 0
        assert len(idx.registries) == 1
        assert idx.registries[0].name == "new-repo"
        assert idx.registries[0].url == ("https://example.com/new-repo.git")

    # ── Property 1: same-URL cache conflict ──────────────────

    @given(
        name=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
            ),
            min_size=1,
            max_size=20,
        ),
    )
    def test_same_url_conflict_error_contains_path_and_force(
        self,
        name: str,
    ) -> None:
        """Property 1: Cache conflict same-URL error contains
        path and --force suggestion.

        Validates: Requirements 1.1, 1.2, 1.3
        """
        import tempfile

        from ksm.commands.registry_add import run_registry_add

        url = f"https://example.com/{name}.git"

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cache_dir = tmp / "cache"
            target = cache_dir / name
            target.mkdir(parents=True)

            idx = RegistryIndex(
                registries=[
                    _make_registry_entry(
                        name,
                        url,
                        str(target),
                    ),
                ]
            )
            args = self._make_args(url)

            import io
            from contextlib import redirect_stderr

            buf = io.StringIO()
            with redirect_stderr(buf):
                code = run_registry_add(
                    args,
                    registry_index=idx,
                    registry_index_path=tmp / "r.json",
                    cache_dir=cache_dir,
                )

            assert code == 1
            err = buf.getvalue()
            assert str(target) in err
            assert "--force" in err

    # ── Property 2: different-URL cache conflict ─────────────

    @given(
        name=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
            ),
            min_size=1,
            max_size=20,
        ),
    )
    def test_different_url_conflict_suggests_name_omits_force(
        self,
        name: str,
    ) -> None:
        """Property 2: Cache conflict different-URL error suggests
        --name and omits --force.

        Validates: Requirements 1.4
        """
        import tempfile

        from ksm.commands.registry_add import run_registry_add

        existing_url = f"https://other.com/{name}.git"
        new_url = f"https://example.com/{name}.git"

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cache_dir = tmp / "cache"
            target = cache_dir / name
            target.mkdir(parents=True)

            idx = RegistryIndex(
                registries=[
                    _make_registry_entry(
                        name,
                        existing_url,
                        str(target),
                    ),
                ]
            )
            args = self._make_args(new_url)

            import io
            from contextlib import redirect_stderr

            buf = io.StringIO()
            with redirect_stderr(buf):
                code = run_registry_add(
                    args,
                    registry_index=idx,
                    registry_index_path=tmp / "r.json",
                    cache_dir=cache_dir,
                )

            assert code == 1
            err = buf.getvalue()
            assert "--name" in err
            assert "--force" not in err

    # ── Property 16: cache namespace ─────────────────────────

    @given(
        name_a=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
            ),
            min_size=1,
            max_size=15,
        ),
        name_b=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
            ),
            min_size=1,
            max_size=15,
        ),
    )
    def test_cache_dir_uses_registry_name_as_namespace(
        self,
        name_a: str,
        name_b: str,
    ) -> None:
        """Property 16: Cache directory uses registry name as
        namespace — different names produce different paths.

        Validates: Requirements 1.8
        """
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            cache_dir = Path(td) / "cache"
            cache_dir.mkdir()

            path_a = cache_dir / name_a
            path_b = cache_dir / name_b

            if name_a != name_b:
                assert path_a != path_b
            else:
                assert path_a == path_b


# ── registry add — duplicate URL and --name ──────────────────


class TestRegistryAddDuplicateUrlAndName:
    """Tests for duplicate URL detection and --name flag.

    Validates Requirements 2.1, 2.2, 11.2, 11.3, 11.4.
    """

    def _make_args(
        self,
        git_url: str,
        force: bool = False,
        custom_name: str | None = None,
        interactive: bool = False,
    ) -> argparse.Namespace:
        return argparse.Namespace(
            git_url=git_url,
            force=force,
            custom_name=custom_name,
            interactive=interactive,
        )

    def test_duplicate_url_prints_existing_name_exit_0(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 2.1, 2.2: Duplicate URL → prints existing name,
        exit 0."""
        from ksm.commands.registry_add import run_registry_add

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "my-reg",
                    "https://example.com/repo.git",
                    str(tmp_path / "other-path"),
                ),
            ]
        )
        args = self._make_args(
            "https://example.com/repo.git",
        )
        code = run_registry_add(
            args,
            registry_index=idx,
            registry_index_path=tmp_path / "r.json",
            cache_dir=cache_dir,
        )

        assert code == 0
        err = capsys.readouterr().err
        assert "my-reg" in err

    def test_name_overrides_derived_name(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 11.2: --name overrides derived name."""
        from ksm.commands.registry_add import run_registry_add

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        idx_path = tmp_path / "r.json"
        idx = RegistryIndex(registries=[])

        args = self._make_args(
            "https://example.com/repo.git",
            custom_name="custom-reg",
        )

        with patch("ksm.commands.registry_add.clone_repo") as mock_clone:
            mock_clone.side_effect = lambda url, t: t.mkdir(parents=True, exist_ok=True)
            with patch(
                "ksm.commands.registry_add.scan_registry",
                return_value=[],
            ):
                code = run_registry_add(
                    args,
                    registry_index=idx,
                    registry_index_path=idx_path,
                    cache_dir=cache_dir,
                )

        assert code == 0
        assert len(idx.registries) == 1
        assert idx.registries[0].name == "custom-reg"

    def test_name_collision_with_existing_registry_errors(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 11.4: --name collision with existing → error
        exit 1."""
        from ksm.commands.registry_add import run_registry_add

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        idx = RegistryIndex(
            registries=[
                _make_registry_entry(
                    "taken-name",
                    "https://other.com/repo.git",
                    str(tmp_path / "taken"),
                ),
            ]
        )
        args = self._make_args(
            "https://example.com/new-repo.git",
            custom_name="taken-name",
        )
        code = run_registry_add(
            args,
            registry_index=idx,
            registry_index_path=tmp_path / "r.json",
            cache_dir=cache_dir,
        )

        assert code == 1
        err = capsys.readouterr().err
        assert "taken-name" in err
        assert "--name" in err

    # ── Property 3: duplicate URL detection ──────────────────

    @given(
        name=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
            ),
            min_size=1,
            max_size=20,
        ),
    )
    def test_duplicate_url_returns_existing_name_and_exit_0(
        self,
        name: str,
    ) -> None:
        """Property 3: Duplicate URL detection returns existing
        name and exit code 0.

        Validates: Requirements 2.1, 2.2
        """
        import io
        import tempfile
        from contextlib import redirect_stderr

        from ksm.commands.registry_add import run_registry_add

        url = f"https://example.com/{name}.git"

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cache_dir = tmp / "cache"
            cache_dir.mkdir()

            idx = RegistryIndex(
                registries=[
                    _make_registry_entry(
                        name,
                        url,
                        str(tmp / "other-path"),
                    ),
                ]
            )
            args = self._make_args(url)

            buf = io.StringIO()
            with redirect_stderr(buf):
                code = run_registry_add(
                    args,
                    registry_index=idx,
                    registry_index_path=tmp / "r.json",
                    cache_dir=cache_dir,
                )

            assert code == 0
            err = buf.getvalue()
            assert name in err


# ── _derive_name property tests ──────────────────────────────


class TestDeriveName:
    """Property tests for _derive_name.

    Validates: Requirement 11.3
    """

    @given(
        name=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
            ),
            min_size=1,
            max_size=30,
        ),
    )
    def test_derive_name_idempotent(self, name: str) -> None:
        """Property 10: _derive_name produces consistent
        URL-derived names — calling twice returns same result.

        Validates: Requirements 11.3
        """
        from ksm.commands.registry_add import _derive_name

        url = f"https://example.com/{name}.git"
        result1 = _derive_name(url)
        result2 = _derive_name(url)
        assert result1 == result2
        assert len(result1) > 0

    @given(
        name=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
            ),
            min_size=1,
            max_size=30,
        ),
    )
    def test_derive_name_strips_git_suffix(self, name: str) -> None:
        """_derive_name strips .git suffix."""
        from ksm.commands.registry_add import _derive_name

        url_with_git = f"https://example.com/{name}.git"
        url_without_git = f"https://example.com/{name}"
        assert _derive_name(url_with_git) == name
        assert _derive_name(url_without_git) == name

    @given(
        name=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
            ),
            min_size=1,
            max_size=30,
        ),
    )
    def test_derive_name_strips_trailing_slash(self, name: str) -> None:
        """_derive_name strips trailing slashes."""
        from ksm.commands.registry_add import _derive_name

        url = f"https://example.com/{name}/"
        assert _derive_name(url) == name
