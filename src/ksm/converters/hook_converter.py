"""Hook .kiro.hook to CLI hook dict conversion."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ksm.converters.tool_map import map_tools

EVENT_TYPE_MAP: dict[str, str] = {
    "promptSubmit": "userPromptSubmit",
    "agentStop": "stop",
    "preToolUse": "preToolUse",
    "postToolUse": "postToolUse",
}

UNCONVERTIBLE_EVENTS: set[str] = {
    "fileEdited",
    "fileCreated",
    "fileDeleted",
    "preTaskExecution",
    "postTaskExecution",
    "userTriggered",
}


@dataclass
class HookConversionResult:
    """Result of converting a single hook file."""

    source_path: Path
    status: Literal["converted", "skipped", "failed"] = "failed"
    cli_event_type: str | None = None
    cli_hook_entries: list[dict[str, str]] = field(
        default_factory=list,
    )
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


def convert_hook(hook_path: Path) -> HookConversionResult:
    """Convert a single IDE .kiro.hook file to CLI format."""
    result = HookConversionResult(source_path=hook_path)
    try:
        raw = hook_path.read_text(encoding="utf-8")
    except OSError as exc:
        result.error = f"Cannot read {hook_path}: {exc}"
        return result

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        result.error = f"{hook_path.name}: invalid JSON"
        return result

    if not data.get("enabled", True):
        result.status = "skipped"
        return result

    then_block = data.get("then", {})
    then_type = then_block.get("type", "")
    if then_type == "askAgent":
        result.status = "skipped"
        result.warnings.append(
            f"{hook_path.name}: 'askAgent' hooks have " f"no CLI equivalent"
        )
        return result

    when_block = data.get("when", {})
    when_type = when_block.get("type", "")
    if when_type in UNCONVERTIBLE_EVENTS:
        result.status = "skipped"
        result.warnings.append(
            f"{hook_path.name}: event type '{when_type}' " f"has no CLI equivalent"
        )
        return result

    cli_event = EVENT_TYPE_MAP.get(when_type)
    if cli_event is None:
        result.error = f"{hook_path.name}: unknown event type " f"'{when_type}'"
        return result

    if then_type != "runCommand":
        result.error = f"{hook_path.name}: unsupported then.type " f"'{then_type}'"
        return result

    command = then_block.get("command", "")
    result.cli_event_type = cli_event

    if when_type in ("preToolUse", "postToolUse"):
        tool_types = when_block.get("toolTypes", [])
        if tool_types:
            cli_names, _ = map_tools(tool_types)
            for name in cli_names:
                result.cli_hook_entries.append({"command": command, "matcher": name})
        else:
            result.cli_hook_entries.append({"command": command})
    else:
        result.cli_hook_entries.append({"command": command})

    result.status = "converted"
    return result
