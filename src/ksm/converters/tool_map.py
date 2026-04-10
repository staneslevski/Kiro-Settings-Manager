"""IDE-to-CLI tool name mapping."""

TOOL_NAME_MAP: dict[str, list[str]] = {
    "read": ["fs_read", "grep", "glob", "code"],
    "write": ["fs_write"],
    "shell": ["execute_bash"],
    "web": ["web_search", "web_fetch"],
}

UNCONVERTIBLE_TOOLS: set[str] = {"spec"}


def map_tools(
    ide_tools: list[str],
) -> tuple[list[str], list[str]]:
    """Map IDE tool names to CLI tool names.

    Returns:
        (cli_tools, warnings) where cli_tools is deduplicated
        and warnings lists any unconvertible tool names.
    """
    seen: dict[str, None] = {}
    warnings: list[str] = []
    for tool in ide_tools:
        if tool in UNCONVERTIBLE_TOOLS:
            warnings.append(f"'{tool}' has no CLI equivalent")
            continue
        expanded = TOOL_NAME_MAP.get(tool, [tool])
        for name in expanded:
            if name not in seen:
                seen[name] = None
    return list(seen), warnings
