"""Tests for ksm.converters.tool_map module."""

from hypothesis import given
from hypothesis import strategies as st

from ksm.converters.tool_map import (
    TOOL_NAME_MAP,
    UNCONVERTIBLE_TOOLS,
    map_tools,
)

# ------------------------------------------------------------------
# Known mappings
# ------------------------------------------------------------------


def test_read_expands_to_four_tools() -> None:
    tools, warnings = map_tools(["read"])
    assert tools == ["fs_read", "grep", "glob", "code"]
    assert warnings == []


def test_write_expands_to_fs_write() -> None:
    tools, warnings = map_tools(["write"])
    assert tools == ["fs_write"]
    assert warnings == []


def test_shell_expands_to_execute_bash() -> None:
    tools, warnings = map_tools(["shell"])
    assert tools == ["execute_bash"]
    assert warnings == []


def test_web_expands_to_search_and_fetch() -> None:
    tools, warnings = map_tools(["web"])
    assert tools == ["web_search", "web_fetch"]
    assert warnings == []


def test_all_known_mappings_combined() -> None:
    tools, warnings = map_tools(["read", "write", "shell", "web"])
    expected = [
        "fs_read",
        "grep",
        "glob",
        "code",
        "fs_write",
        "execute_bash",
        "web_search",
        "web_fetch",
    ]
    assert tools == expected
    assert warnings == []


# ------------------------------------------------------------------
# Unknown passthrough
# ------------------------------------------------------------------


def test_unknown_tool_passes_through() -> None:
    tools, warnings = map_tools(["custom_tool"])
    assert tools == ["custom_tool"]
    assert warnings == []


def test_unknown_mixed_with_known() -> None:
    tools, warnings = map_tools(["shell", "my_tool"])
    assert tools == ["execute_bash", "my_tool"]
    assert warnings == []


# ------------------------------------------------------------------
# Unconvertible tools
# ------------------------------------------------------------------


def test_spec_produces_warning() -> None:
    tools, warnings = map_tools(["spec"])
    assert tools == []
    assert len(warnings) == 1
    assert "spec" in warnings[0]


def test_spec_mixed_with_known() -> None:
    tools, warnings = map_tools(["shell", "spec"])
    assert tools == ["execute_bash"]
    assert len(warnings) == 1


# ------------------------------------------------------------------
# Deduplication
# ------------------------------------------------------------------


def test_duplicate_inputs_deduplicated() -> None:
    tools, _ = map_tools(["read", "read"])
    assert tools == ["fs_read", "grep", "glob", "code"]


def test_overlapping_expansions_deduplicated() -> None:
    tools, _ = map_tools(["read", "fs_read"])
    assert tools == ["fs_read", "grep", "glob", "code"]


# ------------------------------------------------------------------
# Empty input
# ------------------------------------------------------------------


def test_empty_input() -> None:
    tools, warnings = map_tools([])
    assert tools == []
    assert warnings == []


# ------------------------------------------------------------------
# Property-based tests
# ------------------------------------------------------------------

_all_ide_names = list(TOOL_NAME_MAP.keys()) + list(UNCONVERTIBLE_TOOLS)


@given(
    st.lists(
        st.sampled_from(_all_ide_names + ["unknown_a", "unknown_b"]),
        max_size=20,
    )
)
def test_no_duplicates_in_output(ide_tools: list[str]) -> None:
    """Property 2: output never contains duplicates."""
    tools, _ = map_tools(ide_tools)
    assert len(tools) == len(set(tools))


@given(
    st.lists(
        st.sampled_from(_all_ide_names + ["unknown_a", "unknown_b"]),
        max_size=20,
    )
)
def test_deterministic_output(ide_tools: list[str]) -> None:
    """Property 1: same input always produces same output."""
    result1 = map_tools(ide_tools)
    result2 = map_tools(ide_tools)
    assert result1 == result2


@given(
    st.text(
        min_size=1,
        alphabet=st.characters(
            whitelist_categories=("L", "N"),
            whitelist_characters="_-",
        ),
    ).filter(lambda t: t not in TOOL_NAME_MAP and t not in UNCONVERTIBLE_TOOLS)
)
def test_unknown_tools_pass_through_unchanged(
    tool: str,
) -> None:
    """Property 3: unknown tools appear unchanged in output."""
    tools, warnings = map_tools([tool])
    assert tool in tools
    assert warnings == []
