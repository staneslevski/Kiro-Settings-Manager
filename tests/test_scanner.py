"""Tests for ksm.scanner module."""

import shutil
from pathlib import Path

from hypothesis import HealthCheck, given, settings as h_settings
from hypothesis import strategies as st

from ksm.scanner import RECOGNISED_SUBDIRS, scan_registry


def _make_bundle(registry: Path, name: str, subdirs: list[str]) -> Path:
    """Helper to create a bundle directory with given subdirs."""
    bundle_dir = registry / name
    bundle_dir.mkdir(parents=True)
    for subdir in subdirs:
        (bundle_dir / subdir).mkdir()
        # Add a file so the subdir isn't empty
        (bundle_dir / subdir / "placeholder.md").write_text("x")
    return bundle_dir


def test_scan_registry_finds_valid_bundles(tmp_path: Path) -> None:
    """scan_registry returns bundles with recognised subdirectories."""
    _make_bundle(tmp_path, "aws", ["skills", "steering"])
    _make_bundle(tmp_path, "git", ["skills"])

    bundles = scan_registry(tmp_path)

    names = [b.name for b in bundles]
    assert "aws" in names
    assert "git" in names
    assert len(bundles) == 2

    aws_bundle = next(b for b in bundles if b.name == "aws")
    assert set(aws_bundle.subdirectories) == {"skills", "steering"}


def test_scan_registry_ignores_dirs_without_recognised_subdirs(
    tmp_path: Path,
) -> None:
    """scan_registry ignores directories without recognised subdirs."""
    _make_bundle(tmp_path, "valid", ["skills"])
    # Create a dir with no recognised subdirs
    invalid = tmp_path / "invalid"
    invalid.mkdir()
    (invalid / "random_dir").mkdir()
    (invalid / "some_file.txt").write_text("not a bundle")

    bundles = scan_registry(tmp_path)

    assert len(bundles) == 1
    assert bundles[0].name == "valid"


def test_scan_registry_empty_directory(tmp_path: Path) -> None:
    """scan_registry returns empty list for empty directory."""
    bundles = scan_registry(tmp_path)
    assert bundles == []


def test_scan_registry_ignores_files_at_root(tmp_path: Path) -> None:
    """scan_registry ignores files at the registry root level."""
    _make_bundle(tmp_path, "bundle1", ["hooks"])
    (tmp_path / "README.md").write_text("readme")

    bundles = scan_registry(tmp_path)

    assert len(bundles) == 1
    assert bundles[0].name == "bundle1"


def test_scan_registry_all_recognised_subdirs(tmp_path: Path) -> None:
    """scan_registry detects all four recognised subdirectory types."""
    _make_bundle(
        tmp_path,
        "full",
        ["skills", "steering", "hooks", "agents"],
    )

    bundles = scan_registry(tmp_path)

    assert len(bundles) == 1
    assert set(bundles[0].subdirectories) == set(RECOGNISED_SUBDIRS)


def test_scan_registry_ignores_dot_kiro(tmp_path: Path) -> None:
    """scan_registry skips .kiro even if it contains recognised subdirs."""
    _make_bundle(tmp_path, "valid", ["skills"])
    _make_bundle(tmp_path, ".kiro", ["skills", "steering"])

    bundles = scan_registry(tmp_path)

    assert len(bundles) == 1
    assert bundles[0].name == "valid"


def test_scan_registry_ignores_dot_git(tmp_path: Path) -> None:
    """scan_registry skips .git even if it contains recognised subdirs."""
    _make_bundle(tmp_path, "valid", ["hooks"])
    _make_bundle(tmp_path, ".git", ["hooks"])

    bundles = scan_registry(tmp_path)

    assert len(bundles) == 1
    assert bundles[0].name == "valid"


def test_scan_registry_ignores_all_hidden_dirs(
    tmp_path: Path,
) -> None:
    """scan_registry skips any directory whose name starts with a dot."""
    _make_bundle(tmp_path, "valid", ["agents"])
    _make_bundle(tmp_path, ".hidden", ["skills"])
    _make_bundle(tmp_path, ".another", ["steering", "hooks"])

    bundles = scan_registry(tmp_path)

    assert len(bundles) == 1
    assert bundles[0].name == "valid"


def test_bundle_info_has_correct_path(tmp_path: Path) -> None:
    """BundleInfo.path points to the bundle directory."""
    _make_bundle(tmp_path, "mybundle", ["steering"])

    bundles = scan_registry(tmp_path)

    assert len(bundles) == 1
    assert bundles[0].path == tmp_path / "mybundle"


# --- Property-based tests ---

# Strategy: generate a mapping of dir_name -> set of subdirs to create
# Some will have recognised subdirs (valid bundles), some won't.
_subdir_names = st.sampled_from(
    list(RECOGNISED_SUBDIRS) + ["docs", "lib", "config", "data"]
)


# Feature: kiro-settings-manager, Property 13: Scanner identifies valid bundles
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    data=st.data(),
    bundle_specs=st.lists(
        st.tuples(
            st.from_regex(r"[a-zA-Z][a-zA-Z0-9_-]{0,14}", fullmatch=True),
            st.frozensets(_subdir_names, min_size=1, max_size=4),
        ),
        min_size=0,
        max_size=6,
    ),
)
def test_property_scanner_identifies_valid_bundles(
    tmp_path: Path,
    data: st.DataObject,
    bundle_specs: list[tuple[str, frozenset[str]]],
) -> None:
    """Property 13: Scanner identifies exactly the dirs with recognised subdirs."""
    # Each hypothesis example gets its own isolated directory
    registry_dir = tmp_path / data.draw(st.uuids().map(str), label="isolation_id")
    registry_dir.mkdir(parents=True, exist_ok=True)
    # Clean any leftover content from previous replay
    for child in list(registry_dir.iterdir()):
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    # Deduplicate names
    seen_names: set[str] = set()
    unique_specs: list[tuple[str, frozenset[str]]] = []
    for name, subdirs in bundle_specs:
        lower = name.lower()
        if lower not in seen_names:
            seen_names.add(lower)
            unique_specs.append((name, subdirs))

    expected_bundles: dict[str, set[str]] = {}
    for name, subdirs in unique_specs:
        bundle_dir = registry_dir / name
        bundle_dir.mkdir()
        recognised = set()
        for sd in subdirs:
            (bundle_dir / sd).mkdir()
            if sd in RECOGNISED_SUBDIRS:
                recognised.add(sd)
        if recognised:
            expected_bundles[name] = recognised

    results = scan_registry(registry_dir)
    result_map = {b.name: set(b.subdirectories) for b in results}

    assert result_map == expected_bundles


# --- Phase 5.2: registry_name population ---


def test_scan_registry_with_registry_name(
    tmp_path: Path,
) -> None:
    """scan_registry populates registry_name when provided."""
    _make_bundle(tmp_path, "aws", ["skills", "steering"])
    _make_bundle(tmp_path, "git", ["hooks"])

    bundles = scan_registry(tmp_path, registry_name="my-reg")

    for b in bundles:
        assert b.registry_name == "my-reg"


def test_scan_registry_without_registry_name(
    tmp_path: Path,
) -> None:
    """scan_registry leaves registry_name empty when not provided."""
    _make_bundle(tmp_path, "aws", ["skills"])

    bundles = scan_registry(tmp_path)

    assert bundles[0].registry_name == ""


def test_scan_registry_name_on_all_bundles(
    tmp_path: Path,
) -> None:
    """scan_registry sets registry_name on every returned BundleInfo."""
    _make_bundle(tmp_path, "a", ["skills"])
    _make_bundle(tmp_path, "b", ["hooks"])
    _make_bundle(tmp_path, "c", ["agents"])

    bundles = scan_registry(tmp_path, registry_name="team")

    assert len(bundles) == 3
    assert all(b.registry_name == "team" for b in bundles)
