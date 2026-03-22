"""Tests for ksm.commands.add_registry module."""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from ksm.commands.registry_add import _derive_name
from ksm.errors import GitError
from ksm.registry import RegistryEntry, RegistryIndex


def _make_args(**kwargs: str) -> argparse.Namespace:
    defaults: dict[str, str] = {
        "git_url": "https://github.com/org/repo.git",
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# --- _derive_name tests ---


class TestDeriveName:
    """Tests for _derive_name URL-to-registry-name derivation."""

    def test_strips_dot_git_suffix(self) -> None:
        """Removes .git suffix from URL."""
        assert _derive_name("https://github.com/org/repo.git") == "repo"

    def test_no_dot_git_suffix(self) -> None:
        """Works when URL has no .git suffix."""
        assert _derive_name("https://github.com/org/my-bundles") == "my-bundles"

    def test_strips_trailing_slash(self) -> None:
        """Strips trailing slash before extracting name."""
        assert _derive_name("https://github.com/org/repo/") == "repo"

    def test_trailing_slash_and_dot_git(self) -> None:
        """Handles trailing slash followed by .git suffix."""
        assert _derive_name("https://github.com/org/repo.git/") == "repo"

    def test_bare_name(self) -> None:
        """Handles a bare name with no path separators."""
        assert _derive_name("my-repo.git") == "my-repo"


def test_clone_new_repo_and_register(tmp_path: Path) -> None:
    """add-registry clones a new git repo and registers it."""
    from ksm.commands.add_registry import run_add_registry

    cache_dir = tmp_path / "cache"
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    # Simulate clone by creating bundle structure at target
    def fake_clone(url: str, target: Path) -> None:
        bundle = target / "my-bundle" / "skills"
        bundle.mkdir(parents=True)
        (bundle / "f.md").write_bytes(b"x")

    idx = RegistryIndex(registries=[])
    args = _make_args()

    with patch(
        "ksm.commands.registry_add.clone_repo",
        side_effect=fake_clone,
    ):
        code = run_add_registry(
            args,
            registry_index=idx,
            registry_index_path=ksm_dir / "registries.json",
            cache_dir=cache_dir,
        )

    assert code == 0
    assert len(idx.registries) == 1
    assert idx.registries[0].url == "https://github.com/org/repo.git"
    assert idx.registries[0].name == "repo"


def test_duplicate_url_prints_message_exits_zero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """add-registry with duplicate URL prints message and exits 0."""
    from ksm.commands.add_registry import run_add_registry

    cache_dir = tmp_path / "cache"
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(
        registries=[
            RegistryEntry(
                name="repo",
                url="https://github.com/org/repo.git",
                local_path=str(cache_dir / "repo"),
                is_default=False,
            )
        ]
    )
    args = _make_args()

    code = run_add_registry(
        args,
        registry_index=idx,
        registry_index_path=ksm_dir / "registries.json",
        cache_dir=cache_dir,
    )

    assert code == 0
    assert len(idx.registries) == 1
    captured = capsys.readouterr()
    assert "already registered" in captured.err.lower()


def test_git_clone_failure_prints_error_exits_one(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """add-registry with git clone failure prints error and exits 1."""
    from ksm.commands.add_registry import run_add_registry

    cache_dir = tmp_path / "cache"
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    idx = RegistryIndex(registries=[])
    args = _make_args()

    with patch(
        "ksm.commands.registry_add.clone_repo",
        side_effect=GitError("clone failed"),
    ):
        code = run_add_registry(
            args,
            registry_index=idx,
            registry_index_path=ksm_dir / "registries.json",
            cache_dir=cache_dir,
        )

    assert code == 1
    assert len(idx.registries) == 0
    captured = capsys.readouterr()
    assert "clone failed" in captured.err


def test_scanned_bundles_registered_from_cloned_repo(
    tmp_path: Path,
) -> None:
    """add-registry scans cloned repo and registers bundles."""
    from ksm.commands.add_registry import run_add_registry

    cache_dir = tmp_path / "cache"
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    def fake_clone(url: str, target: Path) -> None:
        for bname in ["bundle-a", "bundle-b"]:
            sd = target / bname / "skills"
            sd.mkdir(parents=True)
            (sd / "f.md").write_bytes(b"x")
        # Non-bundle dir should be ignored
        (target / "docs").mkdir()
        (target / "docs" / "readme.md").write_bytes(b"r")

    idx = RegistryIndex(registries=[])
    args = _make_args()

    with patch(
        "ksm.commands.registry_add.clone_repo",
        side_effect=fake_clone,
    ):
        code = run_add_registry(
            args,
            registry_index=idx,
            registry_index_path=ksm_dir / "registries.json",
            cache_dir=cache_dir,
        )

    assert code == 0
    # Registry entry is added (bundles are discovered via scanner)
    assert len(idx.registries) == 1


def test_no_valid_bundles_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """add-registry registers even when cloned repo has no valid
    bundles (new behavior via registry_add delegation)."""
    from ksm.commands.add_registry import run_add_registry

    cache_dir = tmp_path / "cache"
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    def fake_clone(url: str, target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        (target / "docs").mkdir()
        (target / "docs" / "readme.md").write_bytes(b"r")

    idx = RegistryIndex(registries=[])
    args = _make_args()

    with patch(
        "ksm.commands.registry_add.clone_repo",
        side_effect=fake_clone,
    ):
        code = run_add_registry(
            args,
            registry_index=idx,
            registry_index_path=ksm_dir / "registries.json",
            cache_dir=cache_dir,
        )

    assert code == 0
    assert len(idx.registries) == 1


def test_registry_is_additive_not_replacing(
    tmp_path: Path,
) -> None:
    """Adding a registry does not remove existing registries."""
    from ksm.commands.add_registry import run_add_registry

    cache_dir = tmp_path / "cache"
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    def fake_clone(url: str, target: Path) -> None:
        bundle = target / "my-bundle" / "steering"
        bundle.mkdir(parents=True)
        (bundle / "f.md").write_bytes(b"x")

    default_entry = RegistryEntry(
        name="default",
        url=None,
        local_path=str(tmp_path / "config_bundles"),
        is_default=True,
    )
    idx = RegistryIndex(registries=[default_entry])
    args = _make_args(git_url="https://github.com/org/other-repo.git")

    with patch(
        "ksm.commands.registry_add.clone_repo",
        side_effect=fake_clone,
    ):
        code = run_add_registry(
            args,
            registry_index=idx,
            registry_index_path=ksm_dir / "registries.json",
            cache_dir=cache_dir,
        )

    assert code == 0
    assert len(idx.registries) == 2
    assert idx.registries[0].name == "default"
    assert idx.registries[0].is_default is True
    assert idx.registries[1].name == "other-repo"
    assert idx.registries[1].is_default is False


def test_empty_cloned_repo_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """add-registry registers even when cloned repo is empty
    (new behavior via registry_add delegation)."""
    from ksm.commands.add_registry import run_add_registry

    cache_dir = tmp_path / "cache"
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    def fake_clone(url: str, target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)

    idx = RegistryIndex(registries=[])
    args = _make_args()

    with patch(
        "ksm.commands.registry_add.clone_repo",
        side_effect=fake_clone,
    ):
        code = run_add_registry(
            args,
            registry_index=idx,
            registry_index_path=ksm_dir / "registries.json",
            cache_dir=cache_dir,
        )

    assert code == 0
    assert len(idx.registries) == 1


def test_registry_index_persisted_to_disk(tmp_path: Path) -> None:
    """add-registry writes the updated registry index to disk."""
    import json

    from ksm.commands.add_registry import run_add_registry

    cache_dir = tmp_path / "cache"
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)
    index_path = ksm_dir / "registries.json"

    def fake_clone(url: str, target: Path) -> None:
        bundle = target / "my-bundle" / "hooks"
        bundle.mkdir(parents=True)
        (bundle / "h.json").write_bytes(b"{}")

    idx = RegistryIndex(registries=[])
    args = _make_args()

    with patch(
        "ksm.commands.registry_add.clone_repo",
        side_effect=fake_clone,
    ):
        code = run_add_registry(
            args,
            registry_index=idx,
            registry_index_path=index_path,
            cache_dir=cache_dir,
        )

    assert code == 0
    assert index_path.exists()
    data = json.loads(index_path.read_text())
    assert len(data["registries"]) == 1
    assert data["registries"][0]["name"] == "repo"


def test_success_message_to_stderr(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """add-registry prints success message to stderr."""
    from ksm.commands.add_registry import run_add_registry

    cache_dir = tmp_path / "cache"
    ksm_dir = tmp_path / "ksm"
    ksm_dir.mkdir(parents=True)

    def fake_clone(url: str, target: Path) -> None:
        bundle = target / "b" / "agents"
        bundle.mkdir(parents=True)
        (bundle / "a.md").write_bytes(b"x")

    idx = RegistryIndex(registries=[])
    args = _make_args(git_url="https://github.com/org/cool-stuff.git")

    with patch(
        "ksm.commands.registry_add.clone_repo",
        side_effect=fake_clone,
    ):
        code = run_add_registry(
            args,
            registry_index=idx,
            registry_index_path=ksm_dir / "registries.json",
            cache_dir=cache_dir,
        )

    assert code == 0
    captured = capsys.readouterr()
    assert "cool-stuff" in captured.err
    assert "registered" in captured.err.lower()


# ── Legacy add-registry deprecation wrapper tests (Req 8) ───


class TestAddRegistryDeprecationWrapper:
    """Tests for legacy add-registry deprecation wrapper.

    Validates Requirements 8.1, 8.2, 8.3, 8.4.
    """

    def test_prints_deprecation_warning_with_versions(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 8.1, 8.4: Prints deprecation warning with version
        numbers when using add-registry."""
        from ksm.commands.add_registry import run_add_registry

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        idx = RegistryIndex(registries=[])
        args = _make_args()

        with patch(
            "ksm.commands.registry_add.run_registry_add",
            return_value=0,
        ):
            run_add_registry(
                args,
                registry_index=idx,
                registry_index_path=tmp_path / "r.json",
                cache_dir=cache_dir,
            )

        captured = capsys.readouterr()
        assert "deprecated:" in captured.err
        assert "add-registry" in captured.err
        assert "registry add" in captured.err
        # Version numbers present (Req 8.4)
        assert "v0.2.0" in captured.err
        assert "v1.0.0" in captured.err

    def test_delegates_to_run_registry_add(
        self,
        tmp_path: Path,
    ) -> None:
        """Req 8.2: Delegates to run_registry_add after warning."""
        from ksm.commands.add_registry import run_add_registry

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        idx_path = tmp_path / "r.json"
        idx = RegistryIndex(registries=[])

        args = _make_args()

        with patch(
            "ksm.commands.registry_add.run_registry_add",
            return_value=0,
        ) as mock_delegate:
            code = run_add_registry(
                args,
                registry_index=idx,
                registry_index_path=idx_path,
                cache_dir=cache_dir,
            )

        assert code == 0
        mock_delegate.assert_called_once_with(
            args,
            registry_index=idx,
            registry_index_path=idx_path,
            cache_dir=cache_dir,
        )

    def test_retains_backward_compatibility(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Req 8.3: add-registry still executes the registry add
        operation after printing the deprecation warning."""
        from ksm.commands.add_registry import run_add_registry

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        idx_path = tmp_path / "r.json"
        idx = RegistryIndex(registries=[])

        args = _make_args(
            git_url="https://github.com/org/new-repo.git",
        )

        with patch(
            "ksm.commands.registry_add.run_registry_add",
            return_value=0,
        ) as mock_delegate:
            code = run_add_registry(
                args,
                registry_index=idx,
                registry_index_path=idx_path,
                cache_dir=cache_dir,
            )

        assert code == 0
        # Delegation happened
        mock_delegate.assert_called_once()
        # Deprecation warning was printed
        captured = capsys.readouterr()
        assert "deprecated:" in captured.err

    def test_passes_force_flag_through(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """add-registry passes --force flag through to
        run_registry_add."""
        from ksm.commands.add_registry import run_add_registry

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        idx = RegistryIndex(registries=[])
        args = argparse.Namespace(
            git_url="https://github.com/org/repo.git",
            force=True,
            custom_name=None,
            interactive=False,
        )

        with patch(
            "ksm.commands.registry_add.run_registry_add",
            return_value=0,
        ) as mock_delegate:
            code = run_add_registry(
                args,
                registry_index=idx,
                registry_index_path=tmp_path / "r.json",
                cache_dir=cache_dir,
            )

        assert code == 0
        mock_delegate.assert_called_once()
        # The args passed through should have force=True
        call_args = mock_delegate.call_args
        assert call_args[0][0].force is True

    def test_passes_name_flag_through(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """add-registry passes --name flag through to
        run_registry_add."""
        from ksm.commands.add_registry import run_add_registry

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        idx = RegistryIndex(registries=[])
        args = argparse.Namespace(
            git_url="https://github.com/org/repo.git",
            force=False,
            custom_name="my-custom",
            interactive=False,
        )

        with patch(
            "ksm.commands.registry_add.run_registry_add",
            return_value=0,
        ) as mock_delegate:
            code = run_add_registry(
                args,
                registry_index=idx,
                registry_index_path=tmp_path / "r.json",
                cache_dir=cache_dir,
            )

        assert code == 0
        mock_delegate.assert_called_once()
        call_args = mock_delegate.call_args
        assert call_args[0][0].custom_name == "my-custom"
