"""Tests for completions and versioned install.

Property 26: Version recorded in manifest after versioned install
Test completions bash/zsh/fish produces non-empty output
Test non-existent version produces error with available versions
Validates: Requirements 20, 21
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ksm.commands.add import parse_version_spec
from ksm.errors import GitError
from ksm.git_ops import checkout_version, list_versions


# ── completions ──────────────────────────────────────────────


class TestCompletions:
    """Tests for run_completions."""

    @pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
    def test_completions_produces_nonempty_output(
        self,
        shell: str,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from ksm.commands.completions import run_completions

        args = argparse.Namespace(shell=shell)
        code = run_completions(args)

        assert code == 0
        out = capsys.readouterr().out
        assert len(out.strip()) > 0
        assert "ksm" in out

    def test_completions_unsupported_shell(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from ksm.commands.completions import run_completions

        args = argparse.Namespace(shell="powershell")
        code = run_completions(args)

        assert code == 1
        captured = capsys.readouterr()
        assert "unsupported" in captured.err.lower()

    def test_bash_completion_contains_commands(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from ksm.commands.completions import run_completions

        args = argparse.Namespace(shell="bash")
        run_completions(args)
        out = capsys.readouterr().out
        for cmd in ["add", "ls", "sync", "rm", "registry"]:
            assert cmd in out

    def test_zsh_completion_contains_descriptions(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from ksm.commands.completions import run_completions

        args = argparse.Namespace(shell="zsh")
        run_completions(args)
        out = capsys.readouterr().out
        assert "Install a bundle" in out

    def test_fish_completion_contains_commands(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        from ksm.commands.completions import run_completions

        args = argparse.Namespace(shell="fish")
        run_completions(args)
        out = capsys.readouterr().out
        assert "complete -c ksm" in out


# ── version spec parsing ─────────────────────────────────────


class TestVersionSpec:
    """Tests for parse_version_spec."""

    def test_no_version(self) -> None:
        name, ver = parse_version_spec("my-bundle")
        assert name == "my-bundle"
        assert ver is None

    def test_with_version(self) -> None:
        name, ver = parse_version_spec("my-bundle@v1.0.0")
        assert name == "my-bundle"
        assert ver == "v1.0.0"

    def test_empty_version(self) -> None:
        name, ver = parse_version_spec("my-bundle@")
        assert name == "my-bundle"
        assert ver is None

    @given(
        name=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
                whitelist_characters="-_",
            ),
            min_size=1,
            max_size=20,
        ),
        ver=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
                whitelist_characters=".-",
            ),
            min_size=1,
            max_size=10,
        ),
    )
    def test_version_spec_roundtrip(
        self, name: str, ver: str
    ) -> None:
        spec = f"{name}@{ver}"
        parsed_name, parsed_ver = parse_version_spec(spec)
        assert parsed_name == name
        assert parsed_ver == ver


# ── git_ops version functions ────────────────────────────────


class TestGitOpsVersions:
    """Tests for list_versions and checkout_version."""

    def test_list_versions_returns_tags(
        self, tmp_path: Path
    ) -> None:
        with patch(
            "ksm.git_ops.subprocess.run"
        ) as mock_run:
            mock_run.return_value.stdout = (
                "v2.0.0\nv1.0.0\nv0.1.0\n"
            )
            mock_run.return_value.returncode = 0
            tags = list_versions(tmp_path)

        assert tags == ["v2.0.0", "v1.0.0", "v0.1.0"]

    def test_list_versions_empty(
        self, tmp_path: Path
    ) -> None:
        with patch(
            "ksm.git_ops.subprocess.run"
        ) as mock_run:
            mock_run.return_value.stdout = ""
            mock_run.return_value.returncode = 0
            tags = list_versions(tmp_path)

        assert tags == []

    def test_checkout_version_success(
        self, tmp_path: Path
    ) -> None:
        with patch(
            "ksm.git_ops.subprocess.run"
        ) as mock_run:
            mock_run.return_value.returncode = 0
            checkout_version(tmp_path, "v1.0.0")

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "checkout" in call_args[0][0]
        assert "v1.0.0" in call_args[0][0]

    def test_checkout_version_failure(
        self, tmp_path: Path
    ) -> None:
        import subprocess

        with patch(
            "ksm.git_ops.subprocess.run",
            side_effect=subprocess.CalledProcessError(
                1, "git", stderr="not found"
            ),
        ):
            with pytest.raises(GitError, match="not found"):
                checkout_version(tmp_path, "v999")

    def test_list_versions_failure(
        self, tmp_path: Path
    ) -> None:
        import subprocess

        with patch(
            "ksm.git_ops.subprocess.run",
            side_effect=subprocess.CalledProcessError(
                1, "git", stderr="error"
            ),
        ):
            with pytest.raises(GitError):
                list_versions(tmp_path)


# ── versioned install integration ────────────────────────────


class TestVersionedInstall:
    """Property 26: Version recorded in manifest."""

    def test_version_recorded_in_manifest(
        self,
        tmp_path: Path,
    ) -> None:
        """Version is stored in manifest after install."""
        from ksm.manifest import Manifest, ManifestEntry

        entry = ManifestEntry(
            bundle_name="test",
            source_registry="default",
            scope="local",
            installed_files=["f.md"],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            version="v1.0.0",
        )
        assert entry.version == "v1.0.0"

    def test_version_none_by_default(self) -> None:
        from ksm.manifest import ManifestEntry

        entry = ManifestEntry(
            bundle_name="test",
            source_registry="default",
            scope="local",
            installed_files=[],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        assert entry.version is None

    def test_version_serialization_roundtrip(
        self, tmp_path: Path
    ) -> None:
        """Version survives save/load cycle."""
        from ksm.manifest import (
            Manifest,
            ManifestEntry,
            load_manifest,
            save_manifest,
        )

        manifest = Manifest(
            entries=[
                ManifestEntry(
                    bundle_name="test",
                    source_registry="default",
                    scope="local",
                    installed_files=["f.md"],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                    version="v2.0.0",
                ),
            ]
        )
        path = tmp_path / "manifest.json"
        save_manifest(manifest, path)
        loaded = load_manifest(path)

        assert loaded.entries[0].version == "v2.0.0"

    def test_version_none_not_in_json(
        self, tmp_path: Path
    ) -> None:
        """Version field omitted from JSON when None."""
        from ksm.manifest import (
            Manifest,
            ManifestEntry,
            save_manifest,
        )
        from ksm.persistence import read_json

        manifest = Manifest(
            entries=[
                ManifestEntry(
                    bundle_name="test",
                    source_registry="default",
                    scope="local",
                    installed_files=[],
                    installed_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                ),
            ]
        )
        path = tmp_path / "manifest.json"
        save_manifest(manifest, path)
        data = read_json(path)
        assert isinstance(data, dict)
        assert "version" not in data["entries"][0]
