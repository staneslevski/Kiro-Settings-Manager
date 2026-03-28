"""Shared JSON I/O utilities for ksm."""

import json
from pathlib import Path
from typing import Union

KSM_DIR: Path = Path.home() / ".kiro" / "ksm"
REGISTRIES_FILE: Path = KSM_DIR / "registries.json"
MANIFEST_FILE: Path = KSM_DIR / "manifest.json"
CONFIG_BUNDLES_DIR: Path = (
    Path(__file__).resolve().parent.parent.parent / "config_bundles"
)

JsonData = Union[dict, list]


def ensure_ksm_dir(path: Path = KSM_DIR) -> None:
    """Create the ksm directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> JsonData:
    """Read and parse a JSON file.

    Raises FileNotFoundError if the file does not exist.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def write_json(path: Path, data: JsonData) -> None:
    """Write data as formatted JSON to a file.

    Creates parent directories if they don't exist.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
