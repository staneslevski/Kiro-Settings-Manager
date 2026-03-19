"""Tests for ksm.typo_suggest module.

Property 29: Typo suggestion returns closest match within
edit distance 2.
"""

from hypothesis import given
from hypothesis import strategies as st

from ksm.typo_suggest import levenshtein_distance, suggest_command

KSM_COMMANDS = ["add", "rm", "ls", "sync", "registry", "init"]


# ------------------------------------------------------------------
# Property 29: Typo suggestion returns closest match
# ------------------------------------------------------------------


@given(
    unknown=st.text(
        alphabet=st.characters(
            whitelist_categories=("L", "N"),
        ),
        min_size=1,
        max_size=20,
    ),
)
def test_suggest_returns_match_within_distance(
    unknown: str,
) -> None:
    """Property 29: If a match exists within distance 2, it is returned."""
    result = suggest_command(unknown, KSM_COMMANDS, max_distance=2)
    if result is not None:
        assert result in KSM_COMMANDS
        assert levenshtein_distance(unknown, result) <= 2


@given(
    unknown=st.text(
        alphabet=st.characters(
            whitelist_categories=("L", "N"),
        ),
        min_size=1,
        max_size=20,
    ),
)
def test_suggest_none_when_no_close_match(unknown: str) -> None:
    """Property 29: No suggestion when nothing is within distance 2."""
    result = suggest_command(unknown, KSM_COMMANDS, max_distance=2)
    if result is None:
        for cmd in KSM_COMMANDS:
            assert levenshtein_distance(unknown, cmd) > 2


# ------------------------------------------------------------------
# Specific examples from the task description
# ------------------------------------------------------------------


def test_suggest_ad_returns_add() -> None:
    """'ad' -> 'add' (distance 1)."""
    assert suggest_command("ad", KSM_COMMANDS) == "add"


def test_suggest_synx_returns_sync() -> None:
    """'synx' -> 'sync' (distance 1)."""
    assert suggest_command("synx", KSM_COMMANDS) == "sync"


def test_suggest_no_match_for_distant_string() -> None:
    """A string far from all commands returns None."""
    assert suggest_command("zzzzzzz", KSM_COMMANDS) is None


# ------------------------------------------------------------------
# Levenshtein distance properties
# ------------------------------------------------------------------


@given(s=st.text(max_size=30))
def test_levenshtein_identity(s: str) -> None:
    """Distance from a string to itself is 0."""
    assert levenshtein_distance(s, s) == 0


@given(a=st.text(max_size=20), b=st.text(max_size=20))
def test_levenshtein_symmetric(a: str, b: str) -> None:
    """Distance is symmetric: d(a,b) == d(b,a)."""
    assert levenshtein_distance(a, b) == levenshtein_distance(b, a)


@given(s=st.text(max_size=30))
def test_levenshtein_empty(s: str) -> None:
    """Distance from empty to s is len(s)."""
    assert levenshtein_distance("", s) == len(s)
    assert levenshtein_distance(s, "") == len(s)


@given(
    a=st.text(max_size=15),
    b=st.text(max_size=15),
    c=st.text(max_size=15),
)
def test_levenshtein_triangle_inequality(a: str, b: str, c: str) -> None:
    """Triangle inequality: d(a,c) <= d(a,b) + d(b,c)."""
    assert levenshtein_distance(a, c) <= (
        levenshtein_distance(a, b) + levenshtein_distance(b, c)
    )


def test_suggest_empty_commands_returns_none() -> None:
    """Empty command list always returns None."""
    assert suggest_command("add", []) is None
