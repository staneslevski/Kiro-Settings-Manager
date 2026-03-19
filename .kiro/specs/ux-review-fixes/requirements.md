# Requirements Document

## Introduction

This spec covers all UX fixes identified in the ksm CLI UX review (#[[file:docs/ux-review.md]]) and the CLI engineering review (#[[file:docs/steering/ksm-cli-review.md]]). The findings span critical safety gaps (destructive `rm` with no confirmation), missing user feedback, inconsistent command structure, poor discoverability, missing quality-of-life features, and CLI engineering concerns including help text, cross-platform compatibility, output stream correctness, and signal handling. Implementing these fixes will bring ksm in line with CLI design best practices established by tools like npm, docker, and gh.

## Glossary

- **CLI**: The `ksm` command-line interface entry point defined in `src/ksm/cli.py`
- **Bundle**: A collection of Kiro IDE configuration files (steering, skills, hooks, agents) stored in a registry
- **Registry**: A git repository or local directory containing one or more bundles
- **Manifest**: The persistent JSON file (`manifest.json`) tracking installed bundles, their scope, source, and file paths
- **Selector**: The interactive terminal UI (`src/ksm/selector.py`) that lets users pick bundles via arrow keys
- **Scope**: Either "local" (project `.kiro/`) or "global" (`~/.kiro/`) installation target
- **RemovalResult**: A dataclass returned by `remove_bundle()` containing `removed_files` and `skipped_files` lists
- **TTY**: A terminal device; `sys.stdin.isatty()` returns True when stdin is an interactive terminal
- **NO_COLOR**: An environment variable (https://no-color.org/) that, when set, signals CLI tools to suppress color output
- **Dry_Run_Mode**: A mode where commands print what they would do without making changes to the filesystem or manifest
- **Registry_Subcommand_Group**: The `ksm registry` command group containing `add`, `ls`, `rm`, and `inspect` subcommands
- **Color_Module**: A utility module providing ANSI color formatting with automatic TTY detection and NO_COLOR support
- **Edit_Distance**: A string similarity metric (Levenshtein distance) used to suggest the closest valid command when the user types an unknown command
- **Alternate_Screen_Buffer**: Terminal escape sequences (`\033[?1049h` / `\033[?1049l`) that switch to a separate screen buffer, preserving the user's terminal history
- **Numbered_List_Prompt**: A non-interactive fallback for the Selector that displays numbered items and reads a number from stdin, used when raw terminal mode is unavailable
- **SIGINT_Handler**: A signal handler registered for `SIGINT` (Ctrl+C) that cleans up temporary directories and partial state before exiting with code 130
- **TERM_Dumb**: The `TERM=dumb` environment variable value indicating a terminal with no cursor addressing or escape sequence support

## Requirements

### Requirement 1: Confirmation Prompt for Bundle Removal (C1)

**User Story:** As a developer, I want `ksm rm` to ask for confirmation before deleting files, so that I do not accidentally lose configuration files.

#### Acceptance Criteria

1. WHEN the user runs `ksm rm <bundle>` without `--yes`, THE CLI SHALL display a confirmation prompt listing the bundle name, scope, file count, and each file path to be removed
2. WHEN the user responds with "y" to the confirmation prompt, THE CLI SHALL proceed with the removal
3. WHEN the user responds with anything other than "y" to the confirmation prompt, THE CLI SHALL abort the removal and return exit code 0
4. WHEN the user provides the `--yes` or `-y` flag, THE CLI SHALL skip the confirmation prompt and proceed with removal immediately
5. WHEN stdin reaches EOF during the confirmation prompt, THE CLI SHALL abort the removal and return exit code 0
6. WHEN the user runs `ksm rm --display` and selects a bundle, THE CLI SHALL display the same confirmation prompt before removing

### Requirement 2: Feedback After Successful Removal (C2)

**User Story:** As a developer, I want to see what happened after `ksm rm` completes, so that I know which files were deleted and whether any were already missing.

#### Acceptance Criteria

1. WHEN `remove_bundle()` completes successfully with only removed files, THE CLI SHALL print a summary in the format: `Removed '<bundle>' (<scope>): <N> files deleted`
2. WHEN `remove_bundle()` completes with both removed and skipped files, THE CLI SHALL print a summary in the format: `Removed '<bundle>' (<scope>): <N> files deleted, <M> already missing`
3. WHEN `remove_bundle()` completes with zero removed files and only skipped files, THE CLI SHALL print a summary indicating all files were already missing

### Requirement 3: Interactive Selector Headers and Instructions (C3)

**User Story:** As a developer encountering the interactive selector for the first time, I want to see a title and control instructions, so that I know what the selector does and how to use it.

#### Acceptance Criteria

1. THE Selector SHALL render a header line above the bundle list describing the action (e.g., "Select a bundle to install" or "Select a bundle to remove")
2. THE Selector SHALL render an instruction line showing available controls: arrow keys for navigation, Enter to select, q to quit
3. WHEN the terminal is redrawn after navigation, THE Selector SHALL preserve the header and instruction lines above the list

### Requirement 4: Registry Subcommand Group (M1)

**User Story:** As a developer, I want registry management commands grouped under `ksm registry`, so that the CLI follows a consistent `<noun> <verb>` pattern.

#### Acceptance Criteria

1. THE CLI SHALL provide a `registry` subcommand group with `add`, `ls`, `rm`, and `inspect` subcommands
2. WHEN the user runs `ksm registry add <url>`, THE CLI SHALL clone the git repository and register it as a bundle source (same behavior as the current `add-registry` command)
3. THE CLI SHALL remove the top-level `add-registry` command
4. WHEN the user runs `ksm registry` with no subcommand, THE CLI SHALL display help for the registry subcommand group

### Requirement 5: Unified Subdirectory Filter Flag (M2)

**User Story:** As a developer, I want a single `--only` flag to filter which subdirectories are installed, so that the interface is consistent and scalable.

#### Acceptance Criteria

1. THE CLI SHALL accept a repeatable `--only <type>` flag on the `add` command where `<type>` is one of: skills, agents, steering, hooks
2. WHEN multiple `--only` flags are provided, THE CLI SHALL install only the specified subdirectory types
3. WHEN a single `--only` flag is provided, THE CLI SHALL install only that subdirectory type
4. THE CLI SHALL remove the `--skills-only`, `--agents-only`, `--steering-only`, and `--hooks-only` flags
5. IF an invalid subdirectory type is provided to `--only`, THEN THE CLI SHALL print an error listing valid types and return exit code 1

### Requirement 6: Improved List Output (M3)

**User Story:** As a developer, I want `ksm ls` to show organized, filterable output, so that I can quickly understand what is installed and where.

#### Acceptance Criteria

1. THE CLI SHALL group `ksm ls` output by scope with section headers ("Local (.kiro/):" and "Global (~/.kiro/):")
2. WHEN the `--verbose` or `-v` flag is provided, THE CLI SHALL display the list of installed files under each bundle entry
3. WHEN the `--scope local` or `--scope global` flag is provided, THE CLI SHALL display only bundles matching that scope
4. WHEN the `--format json` flag is provided, THE CLI SHALL output the bundle list as a JSON array to stdout
5. THE CLI SHALL display the source registry and a human-readable relative timestamp for each bundle entry
6. WHEN no bundles are installed, THE CLI SHALL print "No bundles currently installed." and return exit code 0

### Requirement 7: Actionable Error Messages (M4)

**User Story:** As a developer, I want error messages to tell me what went wrong, where the tool looked, and what I can do about it, so that I can resolve issues without guessing.

#### Acceptance Criteria

1. WHEN a bundle is not found, THE CLI SHALL include the bundle name, the list of registries searched, and suggested next steps in the error message
2. WHEN a git clone fails, THE CLI SHALL include the URL, a cleaned-up error summary (not raw stderr), and a suggestion to check the URL and access permissions
3. THE BundleNotFoundError class SHALL accept a list of searched registry names as a constructor parameter
4. THE GitError class SHALL accept the URL and a cleaned-up message as constructor parameters

### Requirement 8: Registry List, Remove, and Inspect Commands (M5)

**User Story:** As a developer, I want to list, remove, and inspect registries, so that I can manage my bundle sources without editing JSON files manually.

#### Acceptance Criteria

1. WHEN the user runs `ksm registry ls`, THE CLI SHALL display all registered registries with their name, URL, local path, and bundle count
2. WHEN the user runs `ksm registry rm <name>`, THE CLI SHALL remove the named registry from the registry index and optionally clean the cached clone
3. IF the user attempts to remove the default registry, THEN THE CLI SHALL print an error and return exit code 1
4. WHEN the user runs `ksm registry inspect <name>`, THE CLI SHALL list all bundles available in the named registry with their subdirectory contents
5. IF the named registry does not exist, THEN THE CLI SHALL print an error with the list of registered registry names

### Requirement 9: Auto-Launch Interactive Selector on Bare `ksm add` (M6)

**User Story:** As a developer, I want `ksm add` with no arguments to launch the interactive selector when I am in a terminal, so that I can browse available bundles without remembering flag names.

#### Acceptance Criteria

1. WHEN `ksm add` is called with no bundle spec and no `--display` flag and stdin is a TTY, THE CLI SHALL auto-launch the interactive bundle selector
2. WHEN `ksm add` is called with no bundle spec and stdin is not a TTY, THE CLI SHALL print an error message with usage hints and return exit code 1
3. WHEN the interactive selector is launched and the user quits without selecting, THE CLI SHALL return exit code 0

### Requirement 10: Color Output Support (m1, CLI review M5)

**User Story:** As a developer, I want color-coded CLI output, so that I can scan results faster and distinguish success, error, and warning messages at a glance.

#### Acceptance Criteria

1. THE Color_Module SHALL provide formatting functions for: success (green), error (red), warning (yellow), dim (gray), and bold styles
2. WHEN the `NO_COLOR` environment variable is set, THE Color_Module SHALL suppress all ANSI color codes
3. WHEN stdout is not a TTY, THE Color_Module SHALL suppress all ANSI color codes
4. THE CLI SHALL use green for success messages, red for error messages, yellow for warnings, and dim for secondary information (timestamps, paths)
5. THE Color_Module SHALL never use color as the sole indicator of meaning
6. WHEN the `TERM` environment variable is set to `dumb`, THE Color_Module SHALL suppress all ANSI color codes and cursor manipulation sequences
7. WHEN rendering to stderr (e.g., Selector output), THE Color_Module SHALL check whether stderr is a TTY (not just stdout) to determine whether to emit ANSI codes

### Requirement 11: Rename `--display` to `--interactive` (m2)

**User Story:** As a developer, I want the interactive selector flag to be named `--interactive` / `-i`, so that its purpose is immediately clear.

#### Acceptance Criteria

1. THE CLI SHALL accept `--interactive` or `-i` as the flag to launch the interactive selector on both `add` and `rm` commands
2. THE CLI SHALL accept `--display` as a hidden alias for backward compatibility
3. WHEN `--display` is used, THE CLI SHALL print a deprecation warning to stderr indicating that `--interactive` should be used instead

### Requirement 12: Dry Run Mode (m3)

**User Story:** As a developer, I want a `--dry-run` flag on `add`, `rm`, and `sync`, so that I can preview what changes will be made before committing to them.

#### Acceptance Criteria

1. WHEN `--dry-run` is provided to `ksm add`, THE CLI SHALL print the list of files that would be installed with their status (new or overwrite) without modifying the filesystem or manifest
2. WHEN `--dry-run` is provided to `ksm rm`, THE CLI SHALL print the list of files that would be deleted without modifying the filesystem or manifest
3. WHEN `--dry-run` is provided to `ksm sync`, THE CLI SHALL print the list of bundles and files that would be synced without modifying the filesystem or manifest
4. WHEN `--dry-run` is active, THE CLI SHALL return exit code 0 after printing the preview

### Requirement 13: Specific Sync Confirmation Message (m4)

**User Story:** As a developer, I want the `ksm sync` confirmation prompt to tell me exactly which bundles and how many files will be affected, so that I can make an informed decision.

#### Acceptance Criteria

1. WHEN `ksm sync` displays a confirmation prompt, THE CLI SHALL list the bundle names being synced and the total number of files that will be overwritten
2. WHEN `ksm sync --all` is used, THE CLI SHALL include the count of bundles in the confirmation message

### Requirement 14: Type-to-Filter in Interactive Selectors (m5)

**User Story:** As a developer with many bundles, I want to type characters to filter the list in the interactive selector, so that I can find bundles quickly without scrolling.

#### Acceptance Criteria

1. WHEN the user types alphanumeric characters in the interactive selector, THE Selector SHALL filter the displayed list to items whose names contain the typed characters (case-insensitive)
2. WHEN the user presses Backspace, THE Selector SHALL remove the last typed character and update the filter
3. WHEN the filter text is cleared, THE Selector SHALL display the full list
4. THE Selector SHALL display the current filter text above the list

### Requirement 15: Multi-Select in Interactive Mode (m6)

**User Story:** As a developer, I want to select multiple bundles at once in the interactive selector, so that I can install or remove several bundles in a single operation.

#### Acceptance Criteria

1. WHEN the user presses Space on a bundle in the interactive selector, THE Selector SHALL toggle that bundle's selection state
2. WHEN the user presses Enter with one or more bundles selected, THE Selector SHALL return all selected bundle names
3. THE Selector SHALL display a checkmark indicator for selected bundles and an empty indicator for unselected bundles
4. WHEN no bundles are selected and the user presses Enter, THE Selector SHALL select and return only the currently highlighted bundle (single-select fallback)

### Requirement 16: Curated Root Help Output (m7)

**User Story:** As a new user, I want `ksm` with no arguments to show a friendly, curated help screen, so that I can quickly understand what the tool does and how to get started.

#### Acceptance Criteria

1. WHEN `ksm` is run with no command, THE CLI SHALL display a curated help screen with the tool name, version, description, grouped command list, quick-start examples, and a hint to run `ksm <command> --help`
2. THE CLI SHALL group commands into logical sections (bundle management, registry management)
3. THE CLI SHALL not display the raw argparse-generated help output when no command is given

### Requirement 17: `ksm init` Command (S1)

**User Story:** As a new user, I want a `ksm init` command, so that I have a guided entry point to set up Kiro configuration in my project.

#### Acceptance Criteria

1. WHEN the user runs `ksm init`, THE CLI SHALL create the `.kiro/` directory in the current working directory if it does not exist
2. WHEN `.kiro/` is created, THE CLI SHALL print a success message with next-step suggestions
3. IF `.kiro/` already exists, THEN THE CLI SHALL print a message indicating the project is already initialized and return exit code 0
4. WHEN stdin is a TTY, THE CLI SHALL offer to launch the interactive selector to pick starter bundles after initialization

### Requirement 18: `ksm info <bundle>` Command (S2)

**User Story:** As a developer, I want to inspect a bundle before installing it, so that I can see what it contains and where it comes from.

#### Acceptance Criteria

1. WHEN the user runs `ksm info <bundle>`, THE CLI SHALL display the bundle name, source registry, and a breakdown of subdirectories with file counts
2. IF the bundle is currently installed, THEN THE CLI SHALL indicate the installed scope and timestamp
3. IF the bundle is not found in any registry, THEN THE CLI SHALL print an actionable error message

### Requirement 19: `ksm search <query>` Command (S3)

**User Story:** As a developer, I want to search for bundles by keyword, so that I can discover relevant configuration bundles across registries.

#### Acceptance Criteria

1. WHEN the user runs `ksm search <query>`, THE CLI SHALL display all bundles whose names contain the query string (case-insensitive)
2. THE CLI SHALL display the source registry name next to each matching bundle
3. WHEN no bundles match the query, THE CLI SHALL print a message indicating no results were found

### Requirement 20: Versioned Bundle Installation (S4)

**User Story:** As a developer, I want to install a specific version of a bundle using `ksm add bundle@version`, so that I can pin configurations to known-good versions.

#### Acceptance Criteria

1. WHEN the user runs `ksm add <bundle>@<version>`, THE CLI SHALL check out the specified git tag or branch in the source registry before resolving the bundle
2. IF the specified version does not exist as a tag or branch, THEN THE CLI SHALL print an error listing available versions
3. THE Manifest SHALL record the installed version alongside the bundle entry

### Requirement 21: Shell Completions (S5)

**User Story:** As a developer, I want shell completions for ksm, so that I can discover commands and options by pressing Tab.

#### Acceptance Criteria

1. THE CLI SHALL provide a mechanism to generate shell completions for bash, zsh, and fish
2. WHEN the user runs `ksm completions <shell>`, THE CLI SHALL output the completion script to stdout
3. THE CLI SHALL document how to install completions in the root help or README

### Requirement 22: File-Level Diff After Add and Sync (S6)

**User Story:** As a developer, I want to see what files were added, updated, or unchanged after `ksm add` and `ksm sync`, so that I know exactly what changed in my configuration.

#### Acceptance Criteria

1. WHEN `ksm add` completes successfully, THE CLI SHALL print a summary listing each installed file with its status: new, updated, or unchanged
2. WHEN `ksm sync` completes successfully, THE CLI SHALL print a per-bundle summary listing each file with its status
3. THE CLI SHALL use distinct prefixes or symbols for each status (e.g., `+` for new, `~` for updated, `=` for unchanged)


### Requirement 23: Help Text Examples for All Commands (CLI review C1)

**User Story:** As a developer, I want every `--help` output to include concrete usage examples, so that I can learn how to use commands without reading external documentation.

#### Acceptance Criteria

1. THE CLI SHALL display an examples section in the `--help` output of every subcommand (`add`, `rm`, `ls`, `sync`, `registry add`, `registry ls`, `registry rm`, `registry inspect`, `init`, `info`, `search`, `completions`)
2. WHEN `--help` is displayed for a subcommand, THE CLI SHALL show 2-3 concrete usage examples using `RawDescriptionHelpFormatter` and `epilog` in argparse
3. THE CLI SHALL display a footer in the top-level `--help` output reading: `Use "ksm <command> --help" for more information about a command.`

### Requirement 24: Typo Suggestions for Unknown Commands (CLI review C2)

**User Story:** As a developer who mistypes a command, I want the CLI to suggest the closest valid command, so that I can correct my input without consulting help.

#### Acceptance Criteria

1. WHEN the user provides an unknown command (e.g., `ksm delpoy`), THE CLI SHALL compute the edit distance between the unknown command and all valid commands
2. WHEN a valid command is within an edit distance of 2 from the unknown command, THE CLI SHALL suggest the closest match in the error message (e.g., `Did you mean "add"?`)
3. WHEN no valid command is within edit distance 2, THE CLI SHALL display the standard error listing all valid commands
4. THE CLI SHALL include a hint to run `ksm --help` in all unknown-command error messages

### Requirement 25: Selector Renders to stderr (CLI review C3)

**User Story:** As a developer piping CLI output, I want the interactive selector UI to render to stderr, so that ANSI escape sequences do not corrupt piped stdout.

#### Acceptance Criteria

1. THE Selector SHALL write all ANSI escape sequences and rendered UI lines to stderr, not stdout
2. WHEN the user selects a bundle, THE Selector SHALL return the selection to the calling code without writing the selected value to stdout
3. WHEN the Selector output is piped (e.g., `ksm add --interactive | ...`), THE piped stdout SHALL contain no ANSI escape sequences from the Selector

### Requirement 26: Cross-Platform Selector Fallback (CLI review C4)

**User Story:** As a developer on a platform where `tty`/`termios` are unavailable, I want the interactive selector to fall back to a numbered-list prompt, so that the CLI does not crash.

#### Acceptance Criteria

1. WHEN `tty` or `termios` modules are not available (e.g., on Windows), THE Selector SHALL fall back to a Numbered_List_Prompt displaying items with numeric indices
2. WHEN using the Numbered_List_Prompt, THE Selector SHALL accept a number from stdin to select an item
3. WHEN using the Numbered_List_Prompt, THE Selector SHALL accept `q` to quit and return no selection
4. IF the user enters an invalid number in the Numbered_List_Prompt, THEN THE Selector SHALL print an error and re-prompt

### Requirement 27: Mutually Exclusive Scope Flags (CLI review C5)

**User Story:** As a developer, I want `ksm add -l -g` to produce a clear error, so that I do not accidentally install to the wrong scope.

#### Acceptance Criteria

1. THE CLI SHALL define `-l`/`--local` and `-g`/`--global` as mutually exclusive flags on the `add` command using argparse's `add_mutually_exclusive_group()`
2. THE CLI SHALL define `-l`/`--local` and `-g`/`--global` as mutually exclusive flags on the `rm` command using argparse's `add_mutually_exclusive_group()`
3. WHEN both `-l` and `-g` are provided, THE CLI SHALL display an argparse error: `argument -g/--global: not allowed with argument -l/--local` and return exit code 2

### Requirement 28: Global Verbose and Quiet Flags (CLI review M3)

**User Story:** As a developer, I want `--verbose` and `--quiet` flags on the top-level parser, so that I can get diagnostic detail or suppress non-error output for scripting.

#### Acceptance Criteria

1. THE CLI SHALL accept `--verbose` or `-v` on the top-level parser to enable detailed progress output to stderr
2. THE CLI SHALL accept `--quiet` or `-q` on the top-level parser to suppress warnings and informational messages
3. WHEN `--verbose` is active, THE CLI SHALL print additional diagnostic information (e.g., registry resolution steps, file copy details) to stderr
4. WHEN `--quiet` is active, THE CLI SHALL suppress all output except error messages and data output (e.g., `ls --format json`)
5. IF both `--verbose` and `--quiet` are provided, THEN THE CLI SHALL print an error and return exit code 2

### Requirement 29: TERM=dumb Selector Fallback (CLI review M5)

**User Story:** As a developer using a dumb terminal, I want the interactive selector to fall back to a numbered-list prompt, so that I do not see garbled escape sequences.

#### Acceptance Criteria

1. WHEN the `TERM` environment variable is set to `dumb`, THE Selector SHALL use the Numbered_List_Prompt instead of raw terminal mode
2. WHEN `TERM=dumb`, THE Selector SHALL not emit any ANSI escape sequences (cursor hide/show, screen clear, alternate buffer)
3. WHEN `TERM` is unset or set to any value other than `dumb`, THE Selector SHALL use the standard raw terminal mode (if available)

### Requirement 30: Alternate Screen Buffer for Selector (CLI review M6)

**User Story:** As a developer, I want the interactive selector to use the alternate screen buffer, so that my terminal history is preserved after selection.

#### Acceptance Criteria

1. WHEN entering the interactive selector, THE Selector SHALL emit `\033[?1049h` to switch to the alternate screen buffer
2. WHEN exiting the interactive selector (by selection or quit), THE Selector SHALL emit `\033[?1049l` to restore the main screen buffer
3. WHEN the Selector exits, THE user's previous terminal content SHALL be fully restored

### Requirement 31: TTY Check Before Confirmation Prompts (CLI review M7)

**User Story:** As a developer running ksm in a script or pipe, I want confirmation prompts to fail clearly when stdin is not a TTY, so that piped data is not consumed as a confirmation response.

#### Acceptance Criteria

1. WHEN `ksm sync` needs to display a confirmation prompt and stdin is not a TTY and `--yes` is not provided, THE CLI SHALL print an error to stderr: `Error: confirmation required but stdin is not a terminal. Use --yes to skip confirmation in non-interactive mode.` and return exit code 1
2. WHEN `ksm rm` needs to display a confirmation prompt and stdin is not a TTY and `--yes` is not provided, THE CLI SHALL print the same TTY error to stderr and return exit code 1
3. WHEN `--yes` is provided, THE CLI SHALL skip the TTY check and proceed without prompting regardless of stdin state

### Requirement 32: Informational Messages to stderr (CLI review m2, m3)

**User Story:** As a developer piping CLI output, I want informational messages to go to stderr, so that stdout remains clean for data output.

#### Acceptance Criteria

1. WHEN `ksm ls` has no installed bundles, THE CLI SHALL print "No bundles currently installed." to stderr (not stdout)
2. WHEN `ksm registry add` succeeds, THE CLI SHALL print the success message to stderr (not stdout)
3. THE CLI SHALL reserve stdout exclusively for data output (bundle lists, JSON, completion scripts) and send all informational, success, warning, and progress messages to stderr

### Requirement 33: Remove Empty Directories After Bundle Removal (CLI review m6)

**User Story:** As a developer, I want `ksm rm` to clean up empty directories left behind after removing bundle files, so that my `.kiro/` directory does not accumulate clutter.

#### Acceptance Criteria

1. WHEN `remove_bundle()` deletes files, THE CLI SHALL walk up the directory tree from each deleted file and remove any empty parent directories
2. THE CLI SHALL not remove directories above the `.kiro/` boundary (i.e., `.kiro/` itself and its parent directories are never removed)
3. WHEN a parent directory still contains other files or subdirectories, THE CLI SHALL leave the directory in place

### Requirement 34: Signal Handling for Graceful Cleanup (CLI review m10)

**User Story:** As a developer who presses Ctrl+C during a long operation, I want ksm to clean up temporary files and partial state, so that my system is not left in an inconsistent state.

#### Acceptance Criteria

1. THE CLI SHALL register a SIGINT_Handler at startup that cleans up temporary directories (e.g., partial git clones in the cache directory) and partial file copy state
2. WHEN SIGINT is received during a git clone or file copy operation, THE SIGINT_Handler SHALL remove any temporary directories created by the interrupted operation
3. WHEN SIGINT is received, THE SIGINT_Handler SHALL print a brief cancellation message to stderr and exit with code 130
4. WHEN no operation is in progress, THE SIGINT_Handler SHALL exit immediately with code 130 without attempting cleanup

### Requirement 35: Help Text Examples Round-Trip Consistency

**User Story:** As a developer, I want the examples shown in `--help` output to be syntactically valid ksm commands, so that I can copy-paste them directly.

#### Acceptance Criteria

1. FOR ALL subcommand help texts, every example line in the epilog SHALL be a syntactically valid `ksm` command that the parser accepts without error (round-trip property)
2. THE CLI SHALL not include placeholder text (e.g., `<url>`, `<bundle>`) in example commands without clearly marking them as placeholders
