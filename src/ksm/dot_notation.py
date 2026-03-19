"""Dot notation parsing and validation for ksm.

Parses and validates `<bundle>.<subdir>.<item>` selectors used to
target a specific item within a bundle subdirectory.
"""

from dataclasses import dataclass

from ksm.errors import InvalidSubdirectoryError

VALID_SUBDIRECTORIES: list[str] = [
    "skills",
    "steering",
    "hooks",
    "agents",
]


@dataclass
class DotSelection:
    """A parsed dot-notation selector."""

    bundle_name: str
    subdirectory: str
    item_name: str


def parse_dot_notation(spec: str) -> DotSelection | None:
    """Parse a dot-notation string.

    Returns DotSelection if spec contains at least two dots
    (bundle.subdir.item), otherwise returns None for plain names.
    """
    if not spec:
        return None

    parts = spec.split(".", 2)
    if len(parts) < 3:
        return None

    return DotSelection(
        bundle_name=parts[0],
        subdirectory=parts[1],
        item_name=parts[2],
    )


def validate_dot_selection(selection: DotSelection) -> None:
    """Validate that the subdirectory is a recognised type.

    Raises InvalidSubdirectoryError if not recognised.
    """
    if selection.subdirectory not in VALID_SUBDIRECTORIES:
        raise InvalidSubdirectoryError(selection.subdirectory, VALID_SUBDIRECTORIES)
