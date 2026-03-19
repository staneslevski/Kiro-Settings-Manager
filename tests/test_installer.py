"""Tests for ksm.installer module."""

from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings as h_settings
from hypothesis import strategies as st

from ksm.dot_notation import DotSelection
from ksm.manifest import Manifest
from ksm.resolver import ResolvedBundle
from ksm.scanner import RECOGNISED_SUBDIRS


def _make_resolved_bundle(
    registry: Path,
    name: str,
    subdirs: dict[str, dict[str, bytes]],
) -> ResolvedBundle:
    """Create a bundle on disk and return a ResolvedBundle.

    subdirs maps subdir_name -> {relative_file_path: content}.
    """
    bundle_dir = registry / name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    found_subdirs = []
    for subdir_name, files in subdirs.items():
        subdir_path = bundle_dir / subdir_name
        subdir_path.mkdir(exist_ok=True)
        found_subdirs.append(subdir_name)
        for rel, content in files.items():
            fpath = subdir_path / rel
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_bytes(content)
    return ResolvedBundle(
        name=name,
        path=bundle_dir,
        registry_name="default",
        subdirectories=found_subdirs,
    )


def test_full_bundle_installation(tmp_path: Path) -> None:
    """install_bundle copies all recognised subdirs."""
    from ksm.installer import install_bundle

    reg = tmp_path / "reg"
    target = tmp_path / "target" / ".kiro"
    bundle = _make_resolved_bundle(
        reg,
        "aws",
        {
            "skills": {"aws-cross/SKILL.md": b"skill data"},
            "steering": {"AWS-IAM.md": b"iam data"},
        },
    )
    manifest = Manifest(entries=[])

    installed = install_bundle(
        bundle=bundle,
        target_dir=target,
        scope="local",
        subdirectory_filter=None,
        dot_selection=None,
        manifest=manifest,
        source_label="default",
    )

    assert (target / "skills" / "aws-cross" / "SKILL.md").exists()
    assert (target / "steering" / "AWS-IAM.md").exists()
    assert len(installed) == 2


def test_filtered_installation_copies_only_specified(
    tmp_path: Path,
) -> None:
    """install_bundle with filter copies only specified subdirs."""
    from ksm.installer import install_bundle

    reg = tmp_path / "reg"
    target = tmp_path / "target" / ".kiro"
    bundle = _make_resolved_bundle(
        reg,
        "full",
        {
            "skills": {"s.md": b"s"},
            "steering": {"st.md": b"st"},
            "hooks": {"h.json": b"h"},
        },
    )
    manifest = Manifest(entries=[])

    installed = install_bundle(
        bundle=bundle,
        target_dir=target,
        scope="local",
        subdirectory_filter={"skills"},
        dot_selection=None,
        manifest=manifest,
        source_label="default",
    )

    assert (target / "skills" / "s.md").exists()
    assert not (target / "steering").exists()
    assert not (target / "hooks").exists()
    assert len(installed) == 1


def test_dot_notation_installs_only_target_item(
    tmp_path: Path,
) -> None:
    """install_bundle with dot_selection copies only the target item."""
    from ksm.installer import install_bundle

    reg = tmp_path / "reg"
    target = tmp_path / "target" / ".kiro"
    bundle = _make_resolved_bundle(
        reg,
        "aws",
        {
            "skills": {
                "aws-cross/SKILL.md": b"cross",
                "other-skill/SKILL.md": b"other",
            },
        },
    )
    manifest = Manifest(entries=[])
    dot_sel = DotSelection(
        bundle_name="aws",
        subdirectory="skills",
        item_name="aws-cross",
    )

    installed = install_bundle(
        bundle=bundle,
        target_dir=target,
        scope="local",
        subdirectory_filter=None,
        dot_selection=dot_sel,
        manifest=manifest,
        source_label="default",
    )

    assert (target / "skills" / "aws-cross" / "SKILL.md").exists()
    assert not (target / "skills" / "other-skill").exists()
    assert len(installed) == 1


def test_manifest_updated_with_installed_files(
    tmp_path: Path,
) -> None:
    """install_bundle records installed file paths in manifest."""
    from ksm.installer import install_bundle

    reg = tmp_path / "reg"
    target = tmp_path / "target" / ".kiro"
    bundle = _make_resolved_bundle(
        reg,
        "aws",
        {"steering": {"AWS-IAM.md": b"data"}},
    )
    manifest = Manifest(entries=[])

    install_bundle(
        bundle=bundle,
        target_dir=target,
        scope="local",
        subdirectory_filter=None,
        dot_selection=None,
        manifest=manifest,
        source_label="default",
    )

    assert len(manifest.entries) == 1
    entry = manifest.entries[0]
    assert entry.bundle_name == "aws"
    assert entry.scope == "local"
    assert entry.source_registry == "default"
    assert "steering/AWS-IAM.md" in entry.installed_files


def test_target_subdirectory_created_when_missing(
    tmp_path: Path,
) -> None:
    """install_bundle creates target subdirectory if it doesn't exist."""
    from ksm.installer import install_bundle

    reg = tmp_path / "reg"
    target = tmp_path / "target" / ".kiro"
    # target doesn't exist yet
    assert not target.exists()

    bundle = _make_resolved_bundle(reg, "b", {"skills": {"f.md": b"x"}})
    manifest = Manifest(entries=[])

    install_bundle(
        bundle=bundle,
        target_dir=target,
        scope="local",
        subdirectory_filter=None,
        dot_selection=None,
        manifest=manifest,
        source_label="default",
    )

    assert (target / "skills" / "f.md").exists()


def test_warning_for_missing_filtered_subdirectory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """install_bundle warns when a filtered subdir is missing."""
    from ksm.installer import install_bundle

    reg = tmp_path / "reg"
    target = tmp_path / "target" / ".kiro"
    bundle = _make_resolved_bundle(reg, "b", {"skills": {"f.md": b"x"}})
    manifest = Manifest(entries=[])

    installed = install_bundle(
        bundle=bundle,
        target_dir=target,
        scope="local",
        subdirectory_filter={"skills", "hooks"},
        dot_selection=None,
        manifest=manifest,
        source_label="default",
    )

    # skills should be installed, hooks missing triggers warning
    assert (target / "skills" / "f.md").exists()
    assert len(installed) == 1
    captured = capsys.readouterr()
    assert "hooks" in captured.err


def test_error_when_all_filters_miss(tmp_path: Path) -> None:
    """install_bundle raises when all filtered subdirs are missing."""
    from ksm.installer import install_bundle

    reg = tmp_path / "reg"
    target = tmp_path / "target" / ".kiro"
    bundle = _make_resolved_bundle(reg, "b", {"skills": {"f.md": b"x"}})
    manifest = Manifest(entries=[])

    with pytest.raises(SystemExit):
        install_bundle(
            bundle=bundle,
            target_dir=target,
            scope="local",
            subdirectory_filter={"hooks", "agents"},
            dot_selection=None,
            manifest=manifest,
            source_label="default",
        )


def test_reinstallation_overwrites_and_updates_manifest(
    tmp_path: Path,
) -> None:
    """Installing the same bundle twice updates manifest entry."""
    from ksm.installer import install_bundle

    reg = tmp_path / "reg"
    target = tmp_path / "target" / ".kiro"
    bundle = _make_resolved_bundle(reg, "aws", {"steering": {"f.md": b"v1"}})
    manifest = Manifest(entries=[])

    install_bundle(
        bundle=bundle,
        target_dir=target,
        scope="local",
        subdirectory_filter=None,
        dot_selection=None,
        manifest=manifest,
        source_label="default",
    )
    assert len(manifest.entries) == 1
    first_ts = manifest.entries[0].installed_at

    # Update source content and reinstall
    (reg / "aws" / "steering" / "f.md").write_bytes(b"v2")
    install_bundle(
        bundle=bundle,
        target_dir=target,
        scope="local",
        subdirectory_filter=None,
        dot_selection=None,
        manifest=manifest,
        source_label="default",
    )

    assert len(manifest.entries) == 1
    assert (target / "steering" / "f.md").read_bytes() == b"v2"
    assert manifest.entries[0].installed_at == first_ts


def test_dot_notation_single_file(tmp_path: Path) -> None:
    """install_bundle with dot_selection copies a single file item."""
    from ksm.installer import install_bundle

    reg = tmp_path / "reg"
    target = tmp_path / "target" / ".kiro"
    bundle = _make_resolved_bundle(
        reg,
        "b",
        {"steering": {"my-file.md": b"content"}},
    )
    manifest = Manifest(entries=[])
    dot_sel = DotSelection(
        bundle_name="b",
        subdirectory="steering",
        item_name="my-file.md",
    )

    installed = install_bundle(
        bundle=bundle,
        target_dir=target,
        scope="global",
        subdirectory_filter=None,
        dot_selection=dot_sel,
        manifest=manifest,
        source_label="default",
    )

    assert (target / "steering" / "my-file.md").exists()
    assert len(installed) == 1
    assert manifest.entries[0].scope == "global"


# --- Property-based tests ---

_file_map_strategy = st.dictionaries(
    keys=st.sampled_from(list(RECOGNISED_SUBDIRS)),
    values=st.dictionaries(
        keys=st.from_regex(r"[a-z]{1,6}\.[a-z]{1,3}", fullmatch=True),
        values=st.binary(min_size=1, max_size=50),
        min_size=1,
        max_size=3,
    ),
    min_size=1,
    max_size=3,
)


# Property 3: Manifest records exactly the installed files
@given(file_map=_file_map_strategy)
def test_property_manifest_records_exactly_installed_files(
    file_map: dict[str, dict[str, bytes]],
) -> None:
    """Property 3: Manifest records exactly the installed files."""
    import tempfile

    from ksm.installer import install_bundle

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg"
        target = base / "target"
        bundle = _make_resolved_bundle(reg, "b", file_map)
        manifest = Manifest(entries=[])

        install_bundle(
            bundle=bundle,
            target_dir=target,
            scope="local",
            subdirectory_filter=None,
            dot_selection=None,
            manifest=manifest,
            source_label="default",
        )

        entry = manifest.entries[0]
        manifest_set = set(entry.installed_files)
        actual_files = set()
        for f in target.rglob("*"):
            if f.is_file():
                actual_files.add(str(f.relative_to(target)))
        assert manifest_set == actual_files


# Feature: kiro-settings-manager, Property 4: Reinstallation is idempotent
@given(
    file_map=st.dictionaries(
        keys=st.sampled_from(list(RECOGNISED_SUBDIRS)),
        values=st.dictionaries(
            keys=st.from_regex(r"[a-z]{1,6}\.[a-z]{1,3}", fullmatch=True),
            values=st.binary(min_size=1, max_size=50),
            min_size=1,
            max_size=3,
        ),
        min_size=1,
        max_size=2,
    ),
)
def test_property_reinstallation_is_idempotent(
    file_map: dict[str, dict[str, bytes]],
) -> None:
    """Property 4: Reinstallation produces same files and manifest."""
    import tempfile

    from ksm.installer import install_bundle

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg"
        target = base / "target"
        bundle = _make_resolved_bundle(reg, "b", file_map)

        manifest1 = Manifest(entries=[])
        install_bundle(
            bundle=bundle,
            target_dir=target,
            scope="local",
            subdirectory_filter=None,
            dot_selection=None,
            manifest=manifest1,
            source_label="default",
        )

        # Second install — files already exist, should be skipped
        # but manifest should still record them
        manifest2 = Manifest(entries=[])
        install_bundle(
            bundle=bundle,
            target_dir=target,
            scope="local",
            subdirectory_filter=None,
            dot_selection=None,
            manifest=manifest2,
            source_label="default",
        )

        files1 = set(manifest1.entries[0].installed_files)
        files2 = set(manifest2.entries[0].installed_files)
        assert files1 == files2

        for rel in files1:
            assert (target / rel).exists()


# Feature: kiro-settings-manager, Property 17: Only recognised subdirectories are copied
@given(data=st.data())
def test_property_only_recognised_subdirs_copied(
    data: st.DataObject,
) -> None:
    """Property 17: Only recognised subdirectories are copied."""
    import tempfile

    from ksm.installer import install_bundle

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg"
        target = base / "target"

        bundle_dir = reg / "mixed"
        bundle_dir.mkdir(parents=True)
        for sd in ["skills", "docs", "lib"]:
            (bundle_dir / sd).mkdir()
            (bundle_dir / sd / "f.md").write_bytes(b"x")
        (bundle_dir / "README.md").write_bytes(b"readme")

        bundle = ResolvedBundle(
            name="mixed",
            path=bundle_dir,
            registry_name="default",
            subdirectories=["skills"],
        )
        manifest = Manifest(entries=[])

        install_bundle(
            bundle=bundle,
            target_dir=target,
            scope="local",
            subdirectory_filter=None,
            dot_selection=None,
            manifest=manifest,
            source_label="default",
        )

        assert (target / "skills" / "f.md").exists()
        assert not (target / "docs").exists()
        assert not (target / "lib").exists()
        assert not (target / "README.md").exists()


# Property 24: Subdirectory filter restricts copied dirs
@given(
    filter_set=st.frozensets(
        st.sampled_from(list(RECOGNISED_SUBDIRS)),
        min_size=1,
        max_size=3,
    ),
)
def test_property_subdirectory_filter_restricts(
    filter_set: frozenset[str],
) -> None:
    """Property 24: Subdirectory filter restricts copied directories."""
    import tempfile

    from ksm.installer import install_bundle

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg"
        target = base / "target"

        all_subdirs = {sd: {"f.md": b"x"} for sd in RECOGNISED_SUBDIRS}
        bundle = _make_resolved_bundle(reg, "full", all_subdirs)
        manifest = Manifest(entries=[])

        install_bundle(
            bundle=bundle,
            target_dir=target,
            scope="local",
            subdirectory_filter=set(filter_set),
            dot_selection=None,
            manifest=manifest,
            source_label="default",
        )

        for sd in RECOGNISED_SUBDIRS:
            if sd in filter_set:
                assert (target / sd / "f.md").exists()
            else:
                assert not (target / sd).exists()


# Feature: kiro-settings-manager, Property 25: Warning for missing filtered subdirectory
@h_settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    present=st.sampled_from(list(RECOGNISED_SUBDIRS)),
    missing_idx=st.integers(min_value=0, max_value=2),
)
def test_property_warning_for_missing_filtered_subdir(
    present: str,
    missing_idx: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Property 25: Warning emitted for missing filtered subdirectory."""
    import tempfile

    from ksm.installer import install_bundle

    missing_candidates = [s for s in RECOGNISED_SUBDIRS if s != present]
    missing = missing_candidates[missing_idx % len(missing_candidates)]

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg"
        target = base / "target"

        bundle = _make_resolved_bundle(reg, "b", {present: {"f.md": b"x"}})
        manifest = Manifest(entries=[])

        install_bundle(
            bundle=bundle,
            target_dir=target,
            scope="local",
            subdirectory_filter={present, missing},
            dot_selection=None,
            manifest=manifest,
            source_label="default",
        )

        captured = capsys.readouterr()
        assert missing in captured.err


# Feature: kiro-settings-manager, Property 26: Error when all filters miss
@given(data=st.data())
def test_property_error_when_all_filters_miss(
    data: st.DataObject,
) -> None:
    """Property 26: Error when all filtered subdirs are missing."""
    import tempfile

    from ksm.installer import install_bundle

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg"
        target = base / "target"

        bundle = _make_resolved_bundle(reg, "b", {"skills": {"f.md": b"x"}})
        manifest = Manifest(entries=[])

        with pytest.raises(SystemExit):
            install_bundle(
                bundle=bundle,
                target_dir=target,
                scope="local",
                subdirectory_filter={"hooks", "agents"},
                dot_selection=None,
                manifest=manifest,
                source_label="default",
            )


# Property 27: Dot notation installs only the target item
@given(
    subdir=st.sampled_from(list(RECOGNISED_SUBDIRS)),
)
def test_property_dot_notation_installs_only_target(
    subdir: str,
) -> None:
    """Property 27: Dot notation installs only the target item."""
    import tempfile

    from ksm.installer import install_bundle

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg"
        target = base / "target"

        bundle = _make_resolved_bundle(
            reg,
            "b",
            {subdir: {"target-item/f.md": b"t", "other/f.md": b"o"}},
        )
        manifest = Manifest(entries=[])
        dot_sel = DotSelection(
            bundle_name="b",
            subdirectory=subdir,
            item_name="target-item",
        )

        install_bundle(
            bundle=bundle,
            target_dir=target,
            scope="local",
            subdirectory_filter=None,
            dot_selection=dot_sel,
            manifest=manifest,
            source_label="default",
        )

        assert (target / subdir / "target-item" / "f.md").exists()
        assert not (target / subdir / "other").exists()
