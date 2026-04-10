# Design Document: ide2cli-converter

## Overview

The `ksm ide2cli` command converts Kiro IDE-format configuration files into Kiro CLI-compatible JSON files. It scans a `.kiro/` directory for agent markdown files and hook files, transforms them into CLI-native formats, and writes the output alongside the source files. The IDE markdown remains the source of truth.

Two file types require conversion: agents (markdown → JSON) and hooks (standalone `.kiro.hook` → embedded agent JSON). Skills and steering use identical formats on both platforms and are not converted.

## Architecture

The command follows the existing `ksm` command pattern: a `run_ide2cli` function in `src/ksm/commands/ide2cli.py` registered as a subcommand in `cli.py`. The conversion logic is split into three focused modules:

```
src/ksm/
├── commands/
│   └── ide2cli.py          # Command entry point, orchestration, reporting
├── converters/
│   ├── __init__.py          # Package init, shared types
│   ├── agent_converter.py   # Agent .md → .json conversion
│   ├── hook_converter.py    # Hook .kiro.hook → CLI hook dict conversion
│   └── tool_map.py          # IDE → CLI tool name mapping
```

## Components

### 1. Tool Name Map (`src/ksm/converters/tool_map.py`)

A pure-data module defining the IDE-to-CLI tool name mapping. No I/O, no side effects.

```python
TOOL_NAME_MAP: dict[str, list[str]] = {
    "read": ["fs_read", "grep", "glob", "code"],
    "write": ["fs_write"],
    "shell": ["execute_bash"],
    "web": ["web_search", "web_fetch"],
}

UNCONVERTIBLE_TOOLS: set[str] = {"spec"}


def map_tools(ide_tools: list[str]) -> tuple[list[str], list[str]]:
    """Map IDE tool names to CLI tool names.

    Returns:
        (cli_tools, warnings) where cli_tools is deduplicated
        and warnings lists any unconvertible tool names.
    """
```

The function iterates over `ide_tools`, expands each through `TOOL_NAME_MAP`, collects warnings for tools in `UNCONVERTIBLE_TOOLS`, passes through unknown names unchanged, and deduplicates the result while preserving insertion order.

_Requirements: 3.1, 3.2, 3.3, 2.3, 2.4, 2.5, 2.6_

### 2. Frontmatter Parser (inline in `agent_converter.py`)

Parses YAML frontmatter from agent markdown files. Uses the stdlib `yaml` module (PyYAML, already a project dependency via other paths — if not present, add to `pyproject.toml`).

```python
def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from markdown content.

    Returns:
        (frontmatter_dict, body_string)
        If no --- delimiters found, returns ({}, full_content).
    """
```

The parser splits on the first two `---` lines. Content before the second `---` is parsed as YAML. Everything after is the body. If the file doesn't start with `---`, the entire content is treated as body with an empty frontmatter dict.

_Requirements: 7.1, 7.2_

### 3. Agent Converter (`src/ksm/converters/agent_converter.py`)

Converts a single agent markdown file to a CLI JSON file.

```python
@dataclass
class AgentConversionResult:
    source_path: Path
    output_path: Path | None  # None if skipped/failed
    status: Literal["converted", "skipped", "failed"]
    warnings: list[str]
    error: str | None


def convert_agent(md_path: Path) -> AgentConversionResult:
    """Convert a single IDE agent .md file to CLI .json format."""
```

Conversion steps:
1. Read the markdown file content.
2. Call `parse_frontmatter()` to extract frontmatter dict and body.
3. Validate that `name` and `description` exist in frontmatter. If missing, return a `failed` result with an error message.
4. Extract `tools` from frontmatter (default to empty list if absent).
5. Call `map_tools()` to translate IDE tool names to CLI names.
6. Build the CLI JSON structure:
   ```json
   {
     "name": "<frontmatter.name>",
     "description": "<frontmatter.description>",
     "prompt": "file://<absolute_path_to_md>",
     "tools": ["<cli_tool_1>", "<cli_tool_2>", ...]
   }
   ```
7. Serialize to JSON with 2-space indent and trailing newline.
8. Write to `<same_directory>/<same_basename>.json`.
9. Return an `AgentConversionResult` with status, warnings, and paths.

_Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 7.3, 7.4, 8.1, 8.2_

### 4. Hook Converter (`src/ksm/converters/hook_converter.py`)

Converts IDE hook files to CLI hook dict structures. Because CLI hooks are embedded inside agent configs (not standalone files), the converter produces a dict that can be merged into an agent JSON or written as a standalone hooks JSON file.

```python
# IDE → CLI event type mapping
EVENT_TYPE_MAP: dict[str, str] = {
    "promptSubmit": "userPromptSubmit",
    "agentStop": "stop",
    "preToolUse": "preToolUse",
    "postToolUse": "postToolUse",
}

# IDE event types with no CLI equivalent
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
    source_path: Path
    status: Literal["converted", "skipped", "failed"]
    cli_event_type: str | None
    cli_hook_entry: dict | None  # {"command": "...", "matcher": "..."} or None
    warnings: list[str]
    error: str | None


def convert_hook(hook_path: Path) -> HookConversionResult:
    """Convert a single IDE .kiro.hook file to CLI hook format."""
```

Conversion steps:
1. Read and parse the JSON file. If invalid JSON, return `failed`.
2. If `enabled` is `false`, return `skipped` (no warning).
3. If `then.type` is `askAgent`, return `skipped` with a warning.
4. If `when.type` is in `UNCONVERTIBLE_EVENTS`, return `skipped` with a warning.
5. Map `when.type` through `EVENT_TYPE_MAP` to get the CLI event type.
6. Build the CLI hook entry dict:
   - `"command"`: from `then.command`
   - `"matcher"`: (optional) for `preToolUse`/`postToolUse`, map `when.toolTypes` entries through `tool_map.map_tools()` to get CLI canonical names. If a single tool type maps to multiple CLI names, create one hook entry per CLI name.
7. Return the result with the CLI event type and hook entry.

_Requirements: 4.1–4.10_

### 5. Command Module (`src/ksm/commands/ide2cli.py`)

The orchestrator that ties everything together.

```python
@dataclass
class ConversionSummary:
    converted: int
    skipped: list[tuple[str, str]]  # (filename, reason)
    failed: list[tuple[str, str]]   # (filename, error)


def run_ide2cli(
    args: argparse.Namespace,
    *,
    target_dir: Path | None = None,
) -> int:
    """Run the ide2cli conversion. Returns exit code."""
```

Orchestration flow:
1. Resolve both target directories: workspace `.kiro/` (current working directory) and global `~/.kiro/`. If neither exists, print error to stderr and return 1. If only one exists, proceed with that one.
2. For each existing `.kiro/` directory:
   a. Scan `agents/` subdirectory for `.md` files. For each, call `convert_agent()`.
   b. Scan `hooks/` subdirectory for `.kiro.hook` files. For each, call `convert_hook()`.
   c. For converted hooks: write a `_cli_hooks.json` file in the `hooks/` directory containing all converted hooks grouped by event type.
   ```json
   {
     "preToolUse": [{"matcher": "...", "command": "..."}],
     "userPromptSubmit": [{"command": "..."}]
   }
   ```
6. Collect all results into a `ConversionSummary`.
7. Print the summary to stderr using the project's `format_warning` / `format_error` helpers for any issues.
8. Print a final summary line: `Converted: N | Skipped: N | Failed: N`.
9. Return exit code: 0 if at least one file converted or no convertible files found, 1 if all failed.

_Requirements: 1.1, 1.2, 1.3, 5.1–5.5, 6.1, 6.2, 6.3, 6.4_

### 6. CLI Registration (modification to `src/ksm/cli.py`)

Add the `ide2cli` subcommand to `_build_parser()`:

```python
# --- ide2cli ---
ide2cli_p = sub.add_parser(
    "ide2cli",
    help="Convert IDE config files to CLI format",
    description=(
        "Convert Kiro IDE-format agent and hook files to "
        "CLI-compatible JSON format. Scans both the workspace "
        ".kiro/ and global ~/.kiro/ directories. The IDE "
        "markdown files remain the source of truth."
    ),
)
```

Add a `_dispatch_ide2cli` function following the existing dispatch pattern.

_Requirements: 1.1, 1.2, 6.1, 6.2, 6.3, 6.4_

## Data Models

### Agent Markdown File (IDE Input)

```
---
name: <string>
description: <string or multiline>
tools: [<ide_tool_name>, ...]
---

<markdown body — agent prompt/instructions>
```

### Agent JSON File (CLI Output)

```json
{
  "name": "<string>",
  "description": "<string>",
  "prompt": "file://<absolute_path_to_source.md>",
  "tools": ["<cli_tool_name>", ...]
}
```

### Hook File (IDE Input)

```json
{
  "version": "1.0.0",
  "enabled": true,
  "name": "<string>",
  "when": {
    "type": "<event_type>",
    "patterns": ["<glob>"],
    "toolTypes": ["<tool_category>"]
  },
  "then": {
    "type": "runCommand|askAgent",
    "command": "<shell_command>",
    "prompt": "<agent_prompt>"
  }
}
```

### CLI Hooks File (CLI Output)

```json
{
  "<cli_event_type>": [
    {
      "command": "<shell_command>",
      "matcher": "<cli_tool_name>"
    }
  ]
}
```

## Error Handling Strategy

All errors are non-fatal at the individual file level. The converter processes every file it finds, collecting results. Only when every convertible file fails does the command return exit code 1.

| Scenario | Behavior |
|---|---|
| Missing `.kiro/` directory | Error to stderr, exit 1 |
| Invalid YAML frontmatter | Error to stderr, skip file, continue |
| Missing `name`/`description` in frontmatter | Error to stderr, skip file, continue |
| Invalid JSON in hook file | Error to stderr, skip file, continue |
| `askAgent` hook action | Warning to stderr, skip file, continue |
| Unconvertible event type | Warning to stderr, skip file, continue |
| Disabled hook (`enabled: false`) | Skip silently, continue |
| `spec` tool name | Warning to stderr, omit from tools, continue |
| Unknown tool name | Pass through unchanged, no warning |
| No convertible files found | Info message to stderr, exit 0 |

## Correctness Properties

### Property 1: Tool map expansion is deterministic
For any list of IDE tool names, `map_tools()` always produces the same CLI tool list in the same order.

### Property 2: Tool map produces no duplicates
For any list of IDE tool names (including duplicates), the output of `map_tools()` contains no duplicate entries.

### Property 3: Unknown tools pass through unchanged
For any tool name not in `TOOL_NAME_MAP` and not in `UNCONVERTIBLE_TOOLS`, `map_tools()` includes it unchanged in the output.

### Property 4: Frontmatter round-trip preserves name and description
For any valid frontmatter with `name` and `description`, parsing then building the JSON then re-reading the JSON yields the original `name` and `description` values.

### Property 5: Agent conversion is idempotent
Running `convert_agent()` twice on the same unchanged input produces byte-identical output files.

### Property 6: Event type mapping is total over convertible types
Every IDE event type in `EVENT_TYPE_MAP` maps to exactly one CLI event type. Every IDE event type in `UNCONVERTIBLE_EVENTS` produces a skip result.

### Property 7: Hook conversion skips disabled hooks silently
For any hook file with `enabled: false`, `convert_hook()` returns `skipped` with zero warnings.

### Property 8: All stderr, no stdout
The `run_ide2cli` function writes zero bytes to stdout. All output goes to stderr.

## File Changes Summary

| File | Action |
|---|---|
| `src/ksm/converters/__init__.py` | Create — package init with shared types |
| `src/ksm/converters/tool_map.py` | Create — tool name mapping |
| `src/ksm/converters/agent_converter.py` | Create — agent .md → .json conversion |
| `src/ksm/converters/hook_converter.py` | Create — hook .kiro.hook → CLI dict conversion |
| `src/ksm/commands/ide2cli.py` | Create — command orchestration |
| `src/ksm/cli.py` | Modify — register `ide2cli` subcommand and dispatch |
| `tests/test_ide2cli.py` | Create — tests for the command |
| `tests/test_tool_map.py` | Create — tests for tool name mapping |
| `tests/test_agent_converter.py` | Create — tests for agent conversion |
| `tests/test_hook_converter.py` | Create — tests for hook conversion |
