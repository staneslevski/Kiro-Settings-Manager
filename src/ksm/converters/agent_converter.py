"""Agent markdown to CLI JSON conversion."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

from ksm.converters.tool_map import map_tools


def parse_frontmatter(
    content: str,
) -> tuple[dict[str, object], str]:
    """Extract YAML frontmatter and body from markdown.

    Returns:
        (frontmatter_dict, body_string).
        If no ``---`` delimiters found, returns ({}, content).
    """
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    fm_raw = parts[1]
    body = parts[2]
    if body.startswith("\n"):
        body = body[1:]
    try:
        fm = yaml.safe_load(fm_raw)
    except yaml.YAMLError:
        return {}, content
    if not isinstance(fm, dict):
        return {}, content
    return fm, body


@dataclass
class AgentConversionResult:
    """Result of converting a single agent file."""

    source_path: Path
    output_path: Path | None = None
    status: Literal["converted", "skipped", "failed"] = "failed"
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


def convert_agent(md_path: Path) -> AgentConversionResult:
    """Convert a single IDE agent .md file to CLI .json."""
    result = AgentConversionResult(source_path=md_path)
    try:
        content = md_path.read_text(encoding="utf-8")
    except OSError as exc:
        result.error = f"Cannot read {md_path}: {exc}"
        return result

    fm, _ = parse_frontmatter(content)
    if not fm:
        result.error = f"{md_path.name}: missing or invalid YAML frontmatter"
        return result

    name = fm.get("name")
    description = fm.get("description")
    if not name or not description:
        missing = []
        if not name:
            missing.append("name")
        if not description:
            missing.append("description")
        result.error = (
            f"{md_path.name}: missing required field(s): " f"{', '.join(missing)}"
        )
        return result

    raw_tools = fm.get("tools", []) or []
    if not isinstance(raw_tools, list):
        ide_tools = [str(raw_tools)]
    else:
        ide_tools = [str(t) for t in raw_tools]
    cli_tools, tool_warnings = map_tools(ide_tools)
    result.warnings.extend(tool_warnings)

    agent_json = {
        "name": name,
        "description": description,
        "prompt": f"file://{md_path.resolve()}",
        "tools": cli_tools,
    }

    out_path = md_path.with_suffix(".json")
    json_text = json.dumps(agent_json, indent=2) + "\n"
    try:
        out_path.write_text(json_text, encoding="utf-8")
    except OSError as exc:
        result.error = f"Cannot write {out_path}: {exc}"
        return result

    result.output_path = out_path
    result.status = "converted"
    return result
