# Requirements Document

## Introduction

The `ksm ide2cli` command converts Kiro IDE-format configuration files into Kiro CLI-compatible JSON files. The IDE markdown files remain the source of truth; the CLI JSON files are derived output. The command handles two convertible types — agents and hooks — in a single pass. Skills and steering use identical formats on both platforms and require no conversion.

## Glossary

- **Converter**: The `ksm ide2cli` command module that orchestrates scanning and conversion of IDE-format files to CLI-format files.
- **Agent_Markdown_File**: A `.md` file with YAML frontmatter (`name`, `description`, `tools`) and a markdown body containing the agent prompt. This is the IDE-native agent format.
- **Agent_JSON_File**: A `.json` file containing `name`, `description`, `prompt`, `tools`, and optional fields (`allowedTools`, `mcpServers`, `resources`, `hooks`, `model`, `keyboardShortcut`, `welcomeMessage`, `toolAliases`, `toolsSettings`, `includeMcpJson`). This is the CLI-native agent format.
- **Hook_File**: A `.kiro.hook` JSON file with `version`, `enabled`, `name`, `when`, and `then` fields. This is the IDE-native hook format.
- **Tool_Name_Map**: A mapping from IDE simplified tool names (`read`, `write`, `shell`, `web`, `spec`) to CLI canonical tool names (`fs_read`, `fs_write`, `execute_bash`, `grep`, `glob`, `code`, `web_search`, `web_fetch`).
- **Kiro_Directory**: The `.kiro/` directory in a workspace or `~/.kiro/` globally, containing `agents/`, `hooks/`, `skills/`, and `steering/` subdirectories.
- **Frontmatter_Parser**: The component that extracts YAML frontmatter and body content from an Agent_Markdown_File.
- **Hook_Converter**: The component that transforms a Hook_File into the CLI hooks structure embedded within an Agent_JSON_File.

## Requirements

### Requirement 1: CLI Command Registration

**User Story:** As a ksm user, I want to run `ksm ide2cli` so that I can convert IDE-format files to CLI-format files from the command line.

#### Acceptance Criteria

1. WHEN the user runs `ksm ide2cli`, THE Converter SHALL scan the current workspace Kiro_Directory for convertible files and produce CLI-format output.
2. WHEN the user runs `ksm ide2cli --help`, THE Converter SHALL display usage information including a description, available flags, and examples.
3. WHEN the user runs `ksm ide2cli` and neither the workspace nor global Kiro_Directory exists, THE Converter SHALL print an error to stderr and exit with code 1.

### Requirement 2: Agent Markdown to JSON Conversion

**User Story:** As a ksm user, I want agent markdown files converted to CLI JSON files so that my agents work with the Kiro CLI.

#### Acceptance Criteria

1. WHEN an Agent_Markdown_File is found in the `agents/` subdirectory, THE Converter SHALL parse the YAML frontmatter to extract `name`, `description`, and `tools` fields.
2. WHEN an Agent_Markdown_File is parsed, THE Converter SHALL produce an Agent_JSON_File with the `prompt` field set to a `file://` URI referencing the original markdown file's absolute path.
3. WHEN the frontmatter `tools` array contains IDE tool names, THE Converter SHALL map each name to its CLI equivalent using the Tool_Name_Map.
4. WHEN the IDE tool name `web` is encountered, THE Converter SHALL expand it to both `web_search` and `web_fetch` in the CLI tools array.
5. WHEN the IDE tool name `read` is encountered, THE Converter SHALL expand it to `fs_read`, `grep`, `glob`, and `code` in the CLI tools array.
6. WHEN the IDE tool name `spec` is encountered, THE Converter SHALL omit it from the CLI tools array and print a warning to stderr indicating that `spec` has no CLI equivalent.
7. THE Converter SHALL write the Agent_JSON_File to the same `agents/` directory as the source Agent_Markdown_File, using the same base filename with a `.json` extension.
8. WHEN an Agent_Markdown_File has missing or invalid YAML frontmatter, THE Converter SHALL print an error to stderr identifying the file and skip it without halting the conversion of other files.

### Requirement 3: Tool Name Mapping

**User Story:** As a ksm user, I want IDE tool names automatically translated to CLI tool names so that I do not need to manually maintain two sets of tool definitions.

#### Acceptance Criteria

1. THE Tool_Name_Map SHALL define the following mappings: `read` maps to `fs_read`, `grep`, `glob`, `code`; `write` maps to `fs_write`; `shell` maps to `execute_bash`; `web` maps to `web_search`, `web_fetch`.
2. WHEN a tool name in the frontmatter does not exist in the Tool_Name_Map, THE Converter SHALL pass it through unchanged to the CLI tools array.
3. THE Converter SHALL produce a deduplicated CLI tools array with no repeated tool names.

### Requirement 4: Hook File Conversion

**User Story:** As a ksm user, I want IDE hook files converted to CLI-compatible hook definitions so that my hooks work with the Kiro CLI.

#### Acceptance Criteria

1. WHEN a Hook_File is found in the `hooks/` subdirectory, THE Converter SHALL parse its JSON content and extract the `when` and `then` fields.
2. WHEN a Hook_File has `then.type` of `runCommand`, THE Converter SHALL convert it to the CLI hook format using the `then.command` value.
3. WHEN a Hook_File has `when.type` of `promptSubmit`, THE Converter SHALL map it to the CLI event type `userPromptSubmit`.
4. WHEN a Hook_File has `when.type` of `agentStop`, THE Converter SHALL map it to the CLI event type `stop`.
5. WHEN a Hook_File has `when.type` of `preToolUse`, THE Converter SHALL map it to the CLI event type `preToolUse` and convert `when.toolTypes` entries to CLI canonical tool names using the Tool_Name_Map as the `matcher` field.
6. WHEN a Hook_File has `when.type` of `postToolUse`, THE Converter SHALL map it to the CLI event type `postToolUse` and convert `when.toolTypes` entries to CLI canonical tool names using the Tool_Name_Map as the `matcher` field.
7. WHEN a Hook_File has `then.type` of `askAgent`, THE Converter SHALL skip the hook, print a warning to stderr indicating that `askAgent` hooks have no CLI equivalent, and continue processing other files.
8. WHEN a Hook_File has `when.type` of `fileEdited`, `fileCreated`, `fileDeleted`, `preTaskExecution`, or `postTaskExecution`, THE Converter SHALL skip the hook, print a warning to stderr indicating that the event type has no CLI equivalent, and continue processing other files.
9. WHEN a Hook_File has `enabled` set to `false`, THE Converter SHALL skip the hook without producing output or warnings.
10. WHEN a Hook_File contains invalid JSON, THE Converter SHALL print an error to stderr identifying the file and skip it without halting the conversion of other files.

### Requirement 5: Conversion Output and Reporting

**User Story:** As a ksm user, I want clear feedback on what was converted, skipped, and failed so that I can verify the conversion results.

#### Acceptance Criteria

1. WHEN the conversion completes, THE Converter SHALL print a summary to stderr listing the count of files converted, files skipped (with reasons), and files that failed.
2. WHEN at least one file is converted, THE Converter SHALL exit with code 0.
3. WHEN no convertible files are found, THE Converter SHALL print a message to stderr indicating no convertible files were found and exit with code 0.
4. WHEN all convertible files fail, THE Converter SHALL exit with code 1.
5. THE Converter SHALL write all diagnostic messages (warnings, errors, summaries) to stderr and write no diagnostic output to stdout.

### Requirement 6: Scope

**User Story:** As a ksm user, I want `ksm ide2cli` to convert files in both the current workspace and the global directory so that all my configuration is converted in one pass.

#### Acceptance Criteria

1. WHEN the user runs `ksm ide2cli`, THE Converter SHALL scan both the workspace Kiro_Directory (`.kiro/` in the current working directory) and the global Kiro_Directory (`~/.kiro/`) for convertible files.
2. WHEN the workspace Kiro_Directory does not exist but the global Kiro_Directory does, THE Converter SHALL convert only the global files without error.
3. WHEN the global Kiro_Directory does not exist but the workspace Kiro_Directory does, THE Converter SHALL convert only the workspace files without error.
4. WHEN neither directory exists, THE Converter SHALL print an error to stderr and exit with code 1.

### Requirement 7: Frontmatter Parsing and Pretty-Printing

**User Story:** As a developer, I want reliable parsing of YAML frontmatter from agent markdown files and the ability to produce well-formatted JSON output so that the conversion is correct and the output is human-readable.

#### Acceptance Criteria

1. WHEN an Agent_Markdown_File contains valid YAML frontmatter delimited by `---` lines, THE Frontmatter_Parser SHALL extract the frontmatter as a dictionary and the remaining body as a string.
2. WHEN an Agent_Markdown_File does not contain `---` delimiters, THE Frontmatter_Parser SHALL return an empty dictionary for frontmatter and the entire file content as the body.
3. THE Converter SHALL write Agent_JSON_Files with 2-space indented JSON and a trailing newline.
4. FOR ALL valid Agent_Markdown_Files, parsing the frontmatter then producing an Agent_JSON_File then re-reading the JSON SHALL yield a valid JSON object containing the original `name` and `description` values (round-trip property).

### Requirement 8: Idempotent Conversion

**User Story:** As a ksm user, I want to run `ksm ide2cli` multiple times without producing duplicate or corrupted output so that I can safely re-run the command after editing source files.

#### Acceptance Criteria

1. WHEN an Agent_JSON_File already exists for a given Agent_Markdown_File, THE Converter SHALL overwrite it with the freshly generated content.
2. WHEN `ksm ide2cli` is run twice on the same unchanged input, THE Converter SHALL produce byte-identical output files (idempotence property).
