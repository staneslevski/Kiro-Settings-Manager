"""Tests for ksm.dot_notation module."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ksm.dot_notation import (
    DotSelection,
    parse_dot_notation,
    validate_dot_selection,
)
from ksm.errors import InvalidSubdirectoryError


def test_parse_plain_name_returns_none() -> None:
    """parse_dot_notation returns None for a plain bundle name."""
    assert parse_dot_notation("aws") is None
    assert parse_dot_notation("my-bundle") is None
    assert parse_dot_notation("bundle_123") is None


def test_parse_valid_dot_notation() -> None:
    """parse_dot_notation returns DotSelection for valid dot notation."""
    result = parse_dot_notation("aws.skills.aws-cross-account")
    assert result is not None
    assert result.bundle_name == "aws"
    assert result.subdirectory == "skills"
    assert result.item_name == "aws-cross-account"


def test_parse_all_valid_subdirectory_types() -> None:
    """parse_dot_notation works for all recognised subdirectory types."""
    for subdir in ("skills", "steering", "hooks", "agents"):
        result = parse_dot_notation(f"bundle.{subdir}.item")
        assert result is not None
        assert result.subdirectory == subdir


def test_validate_valid_subdirectory() -> None:
    """validate_dot_selection accepts recognised subdirectory types."""
    for subdir in ("skills", "steering", "hooks", "agents"):
        sel = DotSelection(bundle_name="b", subdirectory=subdir, item_name="i")
        # Should not raise
        validate_dot_selection(sel)


def test_validate_invalid_subdirectory_raises() -> None:
    """validate_dot_selection raises for invalid subdirectory type."""
    sel = DotSelection(bundle_name="b", subdirectory="plugins", item_name="i")
    with pytest.raises(InvalidSubdirectoryError) as exc_info:
        validate_dot_selection(sel)
    assert "plugins" in str(exc_info.value)
    assert "skills" in str(exc_info.value)


def test_parse_too_few_dots_returns_none() -> None:
    """parse_dot_notation returns None for strings with fewer than 2 dots."""
    assert parse_dot_notation("bundle.skills") is None


def test_parse_too_many_dots() -> None:
    """parse_dot_notation handles strings with more than 2 dots."""
    # Item names can contain dots (e.g. file.name.md)
    result = parse_dot_notation("bundle.skills.my.item.name")
    assert result is not None
    assert result.bundle_name == "bundle"
    assert result.subdirectory == "skills"
    assert result.item_name == "my.item.name"


def test_parse_empty_string_returns_none() -> None:
    """parse_dot_notation returns None for empty string."""
    assert parse_dot_notation("") is None


# --- Property-based tests ---

VALID_SUBDIRS = ["skills", "steering", "hooks", "agents"]
INVALID_SUBDIRS = [
    "plugins",
    "config",
    "lib",
    "data",
    "modules",
    "templates",
]


# Feature: kiro-settings-manager, Property 28: Dot notation validates subdirectory type
@given(subdir=st.sampled_from(VALID_SUBDIRS))
def test_property_valid_subdirectory_accepted(subdir: str) -> None:
    """Property 28: Valid subdirectory types are accepted."""
    sel = DotSelection(bundle_name="bundle", subdirectory=subdir, item_name="item")
    # Should not raise
    validate_dot_selection(sel)


@given(subdir=st.sampled_from(INVALID_SUBDIRS))
def test_property_invalid_subdirectory_rejected(subdir: str) -> None:
    """Property 28: Invalid subdirectory types are rejected."""
    sel = DotSelection(bundle_name="bundle", subdirectory=subdir, item_name="item")
    with pytest.raises(InvalidSubdirectoryError) as exc_info:
        validate_dot_selection(sel)
    assert subdir in str(exc_info.value)
    # Error message should list valid types
    for valid in VALID_SUBDIRS:
        assert valid in str(exc_info.value)
