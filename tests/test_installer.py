"""Tests for ksm.installer module."""

from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings as h_settings
from hypothesis import strategies as st

from ksm.dot_notation import DotSelection
from ksm.manifest import Manifest, ManifestEntry
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

    results = install_bundle(
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
    assert len(results) == 2


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

    results = install_bundle(
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
    assert len(results) == 1


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

    results = install_bundle(
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
    assert len(results) == 1


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

    results = install_bundle(
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
    assert len(results) == 1
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


def test_local_scope_records_workspace_path_on_new_entry(
    tmp_path: Path,
) -> None:
    """Local scope install records resolved workspace_path on new entry."""
    from ksm.installer import install_bundle

    reg = tmp_path / "reg"
    target = tmp_path / "project-a" / ".kiro"
    bundle = _make_resolved_bundle(reg, "aws", {"steering": {"AWS-IAM.md": b"data"}})
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
    expected_ws = str((tmp_path / "project-a").resolve())
    assert entry.workspace_path == expected_ws


def test_local_scope_updates_workspace_path_on_existing_entry(
    tmp_path: Path,
) -> None:
    """Local scope install updates workspace_path on existing entry."""
    from ksm.installer import install_bundle

    reg = tmp_path / "reg"
    target = tmp_path / "project-a" / ".kiro"
    bundle = _make_resolved_bundle(reg, "aws", {"steering": {"f.md": b"v1"}})
    manifest = Manifest(entries=[])

    # First install
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

    # Reinstall into a different workspace target
    target2 = tmp_path / "project-b" / ".kiro"
    bundle2 = _make_resolved_bundle(reg, "aws", {"steering": {"f.md": b"v2"}})

    install_bundle(
        bundle=bundle2,
        target_dir=target2,
        scope="local",
        subdirectory_filter=None,
        dot_selection=None,
        manifest=manifest,
        source_label="default",
    )

    assert len(manifest.entries) == 2
    expected_ws_a = str((tmp_path / "project-a").resolve())
    expected_ws_b = str((tmp_path / "project-b").resolve())
    ws_paths = {e.workspace_path for e in manifest.entries}
    assert ws_paths == {expected_ws_a, expected_ws_b}


def test_global_scope_leaves_workspace_path_none(
    tmp_path: Path,
) -> None:
    """Global scope install leaves workspace_path as None."""
    from ksm.installer import install_bundle

    reg = tmp_path / "reg"
    target = tmp_path / "target" / ".kiro"
    bundle = _make_resolved_bundle(reg, "aws", {"steering": {"f.md": b"data"}})
    manifest = Manifest(entries=[])

    install_bundle(
        bundle=bundle,
        target_dir=target,
        scope="global",
        subdirectory_filter=None,
        dot_selection=None,
        manifest=manifest,
        source_label="default",
    )

    assert len(manifest.entries) == 1
    entry = manifest.entries[0]
    assert entry.workspace_path is None


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

    results = install_bundle(
        bundle=bundle,
        target_dir=target,
        scope="global",
        subdirectory_filter=None,
        dot_selection=dot_sel,
        manifest=manifest,
        source_label="default",
    )

    assert (target / "steering" / "my-file.md").exists()
    assert len(results) == 1
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


# --- Tests for legacy entry matching in _update_manifest (Issue #28) ---


def test_update_manifest_legacy_entry_updated_in_place(
    tmp_path: Path,
) -> None:
    """_update_manifest with existing legacy entry (workspace_path=None)
    updates it in place when workspace_path is now provided."""
    from ksm.installer import _update_manifest

    manifest = Manifest(entries=[])

    # Simulate a legacy entry (no workspace_path)
    manifest.entries.append(
        ManifestEntry(
            bundle_name="python_dev",
            source_registry="default",
            scope="local",
            installed_files=["steering/old.md"],
            installed_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            workspace_path=None,
        )
    )

    # Now install with workspace_path set
    _update_manifest(
        manifest,
        bundle_name="python_dev",
        source_registry="default",
        scope="local",
        installed_files=["steering/new.md"],
        workspace_path="/home/user/project",
    )

    # Should update in place, not create a duplicate
    assert len(manifest.entries) == 1
    entry = manifest.entries[0]
    assert entry.workspace_path == "/home/user/project"
    assert entry.installed_files == ["steering/new.md"]
    # installed_at should be preserved (original timestamp)
    assert entry.installed_at == "2025-01-01T00:00:00Z"


def test_update_manifest_multiple_legacy_upgrades_first_only(
    tmp_path: Path,
) -> None:
    """_update_manifest with multiple legacy entries
    (workspace_path=None) upgrades only the first one."""
    from ksm.installer import _update_manifest

    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name="aws",
                source_registry="default",
                scope="local",
                installed_files=["steering/first.md"],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                workspace_path=None,
            ),
            ManifestEntry(
                bundle_name="aws",
                source_registry="default",
                scope="local",
                installed_files=["steering/second.md"],
                installed_at="2025-01-02T00:00:00Z",
                updated_at="2025-01-02T00:00:00Z",
                workspace_path=None,
            ),
        ]
    )

    _update_manifest(
        manifest,
        bundle_name="aws",
        source_registry="default",
        scope="local",
        installed_files=["steering/updated.md"],
        workspace_path="/home/user/project",
    )

    # Should still have 2 entries (first upgraded, second untouched)
    assert len(manifest.entries) == 2

    first = manifest.entries[0]
    assert first.workspace_path == "/home/user/project"
    assert first.installed_files == ["steering/updated.md"]

    second = manifest.entries[1]
    assert second.workspace_path is None
    assert second.installed_files == ["steering/second.md"]


def test_update_manifest_no_legacy_creates_new_entry(
    tmp_path: Path,
) -> None:
    """_update_manifest with no legacy entry and no matching entry
    creates a new entry (existing behavior preserved)."""
    from ksm.installer import _update_manifest

    manifest = Manifest(entries=[])

    _update_manifest(
        manifest,
        bundle_name="aws",
        source_registry="default",
        scope="local",
        installed_files=["steering/new.md"],
        workspace_path="/home/user/project",
    )

    assert len(manifest.entries) == 1
    entry = manifest.entries[0]
    assert entry.bundle_name == "aws"
    assert entry.workspace_path == "/home/user/project"
    assert entry.installed_files == ["steering/new.md"]


def test_update_manifest_matching_entry_updates_it(
    tmp_path: Path,
) -> None:
    """_update_manifest with matching entry (workspace_path set)
    updates it (existing behavior preserved)."""
    from ksm.installer import _update_manifest

    ws = "/home/user/project"
    manifest = Manifest(
        entries=[
            ManifestEntry(
                bundle_name="aws",
                source_registry="default",
                scope="local",
                installed_files=["steering/old.md"],
                installed_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                workspace_path=ws,
            ),
        ]
    )

    _update_manifest(
        manifest,
        bundle_name="aws",
        source_registry="updated",
        scope="local",
        installed_files=["steering/new.md"],
        workspace_path=ws,
    )

    assert len(manifest.entries) == 1
    entry = manifest.entries[0]
    assert entry.source_registry == "updated"
    assert entry.installed_files == ["steering/new.md"]
    assert entry.workspace_path == ws


# --- Tests for hooks filtering in global installs (FR-1.1, FR-1.3, FR-1.4, FR-3.1) ---


def test_global_install_with_hooks_skips_hooks_and_sets_has_hooks(
    tmp_path: Path,
) -> None:
    """(a) Global install of bundle with hooks skips hooks/ subdir
    and sets has_hooks=True on manifest entry.

    **Validates: Requirements FR-1.1, FR-1.3**
    """
    from ksm.installer import install_bundle

    reg = tmp_path / "reg"
    target = tmp_path / "target" / ".kiro"
    bundle = _make_resolved_bundle(
        reg,
        "my-bundle",
        {
            "skills": {"my-skill/SKILL.md": b"skill data"},
            "steering": {"guide.md": b"steering data"},
            "hooks": {"on-save.json": b"hook data"},
        },
    )
    manifest = Manifest(entries=[])

    results = install_bundle(
        bundle=bundle,
        target_dir=target,
        scope="global",
        subdirectory_filter=None,
        dot_selection=None,
        manifest=manifest,
        source_label="default",
    )

    # hooks/ should NOT be copied
    assert not (target / "hooks").exists()
    # Non-hook subdirs should be copied
    assert (target / "skills" / "my-skill" / "SKILL.md").exists()
    assert (target / "steering" / "guide.md").exists()
    # No result should reference hooks
    result_paths = [str(r.path.relative_to(target)) for r in results]
    assert not any(p.startswith("hooks") for p in result_paths)
    # Manifest entry should have has_hooks=True
    assert len(manifest.entries) == 1
    entry = manifest.entries[0]
    assert entry.has_hooks is True
    # Manifest installed_files should not contain hooks paths
    assert not any(f.startswith("hooks") for f in entry.installed_files)


def test_global_install_without_hooks_sets_has_hooks_false(
    tmp_path: Path,
) -> None:
    """(b) Global install of bundle without hooks sets has_hooks=False.

    **Validates: Requirements FR-1.4**
    """
    from ksm.installer import install_bundle

    reg = tmp_path / "reg"
    target = tmp_path / "target" / ".kiro"
    bundle = _make_resolved_bundle(
        reg,
        "no-hooks-bundle",
        {
            "skills": {"s.md": b"skill"},
            "steering": {"st.md": b"steer"},
        },
    )
    manifest = Manifest(entries=[])

    install_bundle(
        bundle=bundle,
        target_dir=target,
        scope="global",
        subdirectory_filter=None,
        dot_selection=None,
        manifest=manifest,
        source_label="default",
    )

    assert len(manifest.entries) == 1
    entry = manifest.entries[0]
    assert entry.has_hooks is False


def test_local_install_with_hooks_copies_hooks_and_has_hooks_false(
    tmp_path: Path,
) -> None:
    """(c) Local install of bundle with hooks copies all subdirs
    including hooks and sets has_hooks=False.

    **Validates: Requirements FR-3.1**
    """
    from ksm.installer import install_bundle

    reg = tmp_path / "reg"
    target = tmp_path / "project" / ".kiro"
    bundle = _make_resolved_bundle(
        reg,
        "hooks-bundle",
        {
            "skills": {"s.md": b"skill"},
            "hooks": {"on-save.json": b"hook data"},
        },
    )
    manifest = Manifest(entries=[])

    results = install_bundle(
        bundle=bundle,
        target_dir=target,
        scope="local",
        subdirectory_filter=None,
        dot_selection=None,
        manifest=manifest,
        source_label="default",
    )

    # hooks/ SHOULD be copied for local installs
    assert (target / "hooks" / "on-save.json").exists()
    assert (target / "skills" / "s.md").exists()
    assert len(results) == 2
    # Manifest entry should have has_hooks=False (local unchanged)
    assert len(manifest.entries) == 1
    entry = manifest.entries[0]
    assert entry.has_hooks is False


# --- Property-based test: CP-1 Hook exclusion from global installs ---


# Strategy: generate bundles that always include hooks/ plus
# at least one other recognised subdir.
_non_hook_subdirs = sorted(RECOGNISED_SUBDIRS - {"hooks"})

_global_bundle_with_hooks_strategy = st.dictionaries(
    keys=st.sampled_from(_non_hook_subdirs),
    values=st.dictionaries(
        keys=st.from_regex(r"[a-z]{1,6}\.[a-z]{1,3}", fullmatch=True),
        values=st.binary(min_size=1, max_size=50),
        min_size=1,
        max_size=3,
    ),
    min_size=1,
    max_size=3,
).map(
    lambda d: {
        **d,
        "hooks": {"hook-file.json": b"hook content"},
    }
)


@given(file_map=_global_bundle_with_hooks_strategy)
def test_property_cp1_global_install_no_hooks_in_installed_files(
    file_map: dict[str, dict[str, bytes]],
) -> None:
    """CP-1: For any global install, no installed file path starts
    with 'hooks/'.

    **Validates: Requirements FR-1.1**
    """
    import tempfile

    from ksm.installer import install_bundle

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        reg = base / "reg"
        target = base / "target"
        bundle = _make_resolved_bundle(reg, "b", file_map)
        manifest = Manifest(entries=[])

        results = install_bundle(
            bundle=bundle,
            target_dir=target,
            scope="global",
            subdirectory_filter=None,
            dot_selection=None,
            manifest=manifest,
            source_label="default",
        )

        # No installed file path should start with "hooks/"
        for r in results:
            rel = str(r.path.relative_to(target))
            assert not rel.startswith(
                "hooks/"
            ), f"Global install contains hooks path: {rel}"

        # Manifest installed_files should also not contain hooks
        entry = manifest.entries[0]
        for f in entry.installed_files:
            assert not f.startswith("hooks/"), f"Manifest contains hooks path: {f}"

        # hooks/ directory should not exist on disk
        assert not (
            target / "hooks"
        ).exists(), "hooks/ dir should not exist after global install"
