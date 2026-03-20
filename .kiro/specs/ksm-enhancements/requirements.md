commit 19fa7adaf2b649d4b299ffa1906c68cdf145db70
Author: Tom Stanley <tom@ilingu.com>
Date:   Fri Mar 20 15:06:57 2026 +0800

    feat(ksm): add enhancement spec with agent recommendations and project updates
    
    - Add KSM enhancements specification with requirements, design, and task breakdown
    - Include agent recommendations for hypothesis-test-writer and argparse-cli-refactorer
    - Add LICENSE file to project
    - Update README with project overview and setup instructions
    - Bump project version in pyproject.toml
    - Enhance scanner.py with improved registry scanning logic
    - Add comprehensive test coverage for registry addition and scanner functionality
    - Configure Kiro workflow for requirements-first feature development

diff --git a/.kiro/specs/ksm-enhancements/requirements.md b/.kiro/specs/ksm-enhancements/requirements.md
new file mode 100644
index 0000000..3fcfc51
--- /dev/null
+++ b/.kiro/specs/ksm-enhancements/requirements.md
@@ -0,0 +1,209 @@
+# Requirements Document
+
+## Introduction
+
+This document specifies enhancements to the ksm (Kiro Settings Manager) CLI tool. The enhancements cover: restructuring registry commands as a proper subcommand group, adding full-word command aliases for top-level and registry subcommands, improving registry add/remove commands, handling cache directory conflicts during registry cloning, disambiguating bundles with identical names across registries using qualified bundle name syntax (`registry_name/bundle_name`), renaming the `--display` flag to `-i`/`--interactive`, consolidating `--*-only` flags into a single `--only` flag, standardising error message formatting, adding a `--name` flag for custom registry naming, and specifying registry inspect output.
+
+## Glossary
+
+- **CLI**: The ksm command-line interface entry point defined in `src/ksm/cli.py`
+- **Registry**: A git repository registered as a source of configuration bundles, tracked in `registries.json`
+- **Registry_Index**: The in-memory and on-disk data structure (`registries.json`) that stores all registered registry entries
+- **Cache_Directory**: The `~/.kiro/ksm/cache/` directory where cloned registry repositories are stored locally; cache directories use the `registry_name/bundle` structure to avoid collisions between registries
+- **Bundle**: A directory within a registry containing at least one recognised subdirectory (skills/, steering/, hooks/, agents/)
+- **Bundle_Name**: The directory name of a bundle within a registry
+- **Qualified_Bundle_Name**: A bundle reference in the format `registry_name/bundle_name` used to disambiguate bundles that exist in multiple registries (e.g. `default/my-bundle`, `my-org/my-bundle`)
+- **Manifest**: The `manifest.json` file tracking all installed bundles, their scope, and installed files
+- **Selector**: The interactive terminal UI (`selector.py`) used for choosing bundles during add and remove operations
+- **Add_Command**: The `ksm add` subcommand that installs bundles
+- **Remove_Command**: The `ksm remove` subcommand (aliased as `ksm rm`) that removes installed bundles
+- **List_Command**: The `ksm list` subcommand (aliased as `ksm ls`) that lists installed bundles
+- **Registry_Subcommand**: The `ksm registry` subcommand group that manages registries, containing `add`, `remove`, `list`, and `inspect` subcommands
+- **Registry_Add_Command**: The `ksm registry add` subcommand that registers a new bundle source
+- **Registry_Remove_Command**: The `ksm registry remove` subcommand that removes a registered bundle source
+- **Registry_List_Command**: The `ksm registry list` subcommand that lists registered registries
+- **Registry_Inspect_Command**: The `ksm registry inspect` subcommand that displays detailed information about a named registry
+- **Legacy_Add_Registry_Command**: The deprecated `ksm add-registry` top-level command
+- **Scanner**: The module (`scanner.py`) that discovers valid bundles within a registry directory
+
+## Requirements
+
+### Requirement 1: Registry Add — Cache Directory Conflict Handling
+
+**User Story:** As a user, I want `ksm registry add` to handle the case where the cache directory already exists, so that I get a clear error or recovery path instead of a git clone failure.
+
+#### Acceptance Criteria
+
+1. WHEN a user runs `ksm registry add <url>` and the target Cache_Directory already exists and belongs to the same URL being re-added, THEN THE Registry_Add_Command SHALL print a descriptive error message to stderr indicating the cache directory already exists and return exit code 1
+2. WHEN a user runs `ksm registry add <url>` and the target Cache_Directory already exists and belongs to the same URL being re-added, THEN THE Registry_Add_Command SHALL include the path of the existing cache directory in the error message
+3. WHEN a user runs `ksm registry add <url>` and the target Cache_Directory already exists and belongs to the same URL being re-added, THEN THE Registry_Add_Command SHALL suggest using `--force` to replace the existing cache
+4. WHEN the target Cache_Directory already exists and belongs to a different registered registry (i.e. a different URL), THEN THE Registry_Add_Command SHALL print an error indicating the name collision, suggest using `--name <custom-name>` to specify a different cache directory name, and SHALL NOT offer `--force`
+5. WHEN a user runs `ksm registry add <url> --force` and the target Cache_Directory already exists, THE Registry_Add_Command SHALL remove the existing cache directory, clone the repository, and register the registry
+6. WHEN a user runs `ksm registry add <url> --force` and the clone operation fails after removing the existing cache, THEN THE Registry_Add_Command SHALL print the git error to stderr, note that the previous cache was removed and the registry may need to be re-added, and return exit code 1
+7. WHEN a user runs `ksm registry add <url>` and the target Cache_Directory does not exist, THE Registry_Add_Command SHALL clone and register the registry as it does today
+8. THE Registry_Add_Command SHALL use the registry name as a namespace prefix for cache directories to avoid collisions between registries with the same URL-derived name
+
+### Requirement 2: Registry Add — Duplicate URL Detection Improvement
+
+**User Story:** As a user, I want clear feedback when I try to add a registry that is already registered, so that I understand the current state.
+
+#### Acceptance Criteria
+
+1. WHEN a user runs `ksm registry add <url>` and a registry with the same URL is already registered, THE Registry_Add_Command SHALL print the name of the existing registry entry to stderr
+2. WHEN a user runs `ksm registry add <url>` and a registry with the same URL is already registered, THE Registry_Add_Command SHALL return exit code 0
+
+### Requirement 3: Registry Remove — Improved Feedback
+
+**User Story:** As a user, I want the registry remove command to provide clear feedback about what was cleaned up, so that I can verify the operation completed correctly.
+
+#### Acceptance Criteria
+
+1. WHEN a user runs `ksm registry remove <name>` and the registry exists and the cache directory was removed, THE Registry_Remove_Command SHALL print `Removed registry '<name>'. Cache directory cleaned: <path>` to stderr
+2. WHEN a user runs `ksm registry remove <name>` and the registry exists and the cache directory was already absent, THE Registry_Remove_Command SHALL print `Removed registry '<name>'. Cache directory was already absent.` to stderr
+3. WHEN a user runs `ksm registry remove <name>` and the registry cache directory removal fails due to a permission error, THEN THE Registry_Remove_Command SHALL print a warning to stderr, still remove the registry from the Registry_Index, and return exit code 0
+4. WHEN a user runs `ksm registry remove <name>` and the registry does not exist, THE Registry_Remove_Command SHALL list all registered registry names in the error message
+
+### Requirement 4: Bundle Name Disambiguation
+
+**User Story:** As a user, I want to see which registry a bundle comes from when multiple registries contain bundles with the same name, so that I can choose the correct one.
+
+#### Acceptance Criteria
+
+1. WHEN the Selector displays bundles and two or more registries contain a Bundle with the same Bundle_Name, THE Selector SHALL display the registry name alongside each ambiguous bundle entry using the Qualified_Bundle_Name format (`registry_name/bundle_name`)
+2. WHEN the Selector displays bundles and a Bundle_Name is unique across all registries, THE Selector SHALL display the bundle without a registry name qualifier
+3. WHEN a user runs `ksm add <bundle_name>` without the Selector and multiple registries contain a bundle with that Bundle_Name, THE Add_Command SHALL print an error to stderr listing all registries that contain the bundle
+4. WHEN a user runs `ksm add <bundle_name>` without the Selector and multiple registries contain a bundle with that Bundle_Name, THE Add_Command SHALL suggest using `ksm add <registry_name>/<bundle_name>` to specify the source
+5. THE Scanner SHALL populate the `registry_name` field on each BundleInfo object when scanning bundles from a registry
+6. WHEN resolving a bundle by name, THE resolver SHALL scan ALL registries and collect all matches, not return the first match, to enable ambiguity detection
+
+### Requirement 5: Rename --display Flag to -i/--interactive
+
+**User Story:** As a user, I want to use `-i` or `--interactive` instead of `--display` to launch the interactive selector, so that the flag name follows standard CLI conventions.
+
+#### Acceptance Criteria
+
+1. THE CLI SHALL accept `-i` and `--interactive` flags on the Add_Command to launch the interactive selector
+2. THE CLI SHALL accept `-i` and `--interactive` flags on the Remove_Command to launch the interactive selector
+3. THE CLI SHALL remove `--display` from the visible help text of the Add_Command argument parser (hide from `--help` output) but retain it in the parser for backward compatibility
+4. THE CLI SHALL remove `--display` from the visible help text of the Remove_Command argument parser (hide from `--help` output) but retain it in the parser for backward compatibility
+5. WHEN a user passes `--display` to the Add_Command, THE CLI SHALL print a deprecation warning to stderr and treat the flag as equivalent to `--interactive`
+6. WHEN a user passes `--display` to the Remove_Command, THE CLI SHALL print a deprecation warning to stderr and treat the flag as equivalent to `--interactive`
+7. THE Add_Command SHALL launch the interactive selector when the `-i` or `--interactive` flag is provided
+8. THE Remove_Command SHALL launch the interactive selector when the `-i` or `--interactive` flag is provided
+9. WHEN a user provides both a bundle_spec positional argument AND the `-i`/`--interactive` flag, THE Add_Command SHALL ignore the `-i` flag, proceed with the specified bundle_spec, and print a message to stderr indicating that `-i` was ignored because a bundle was specified
+10. WHEN a user provides both a bundle_name positional argument AND the `-i`/`--interactive` flag, THE Remove_Command SHALL ignore the `-i` flag, proceed with the specified bundle_name, and print a message to stderr indicating that `-i` was ignored because a bundle was specified
+
+### Requirement 6: Registry Add — CLI Flag Addition
+
+**User Story:** As a user, I want the `--force` flag available on the registry add command, so that I can replace an existing cache directory.
+
+#### Acceptance Criteria
+
+1. THE CLI SHALL define a `-f`/`--force` flag on the `registry add` subparser
+2. THE CLI SHALL define a `-f`/`--force` flag on the Legacy_Add_Registry_Command subparser
+3. THE `--force` flag SHALL default to false when not provided
+
+### Requirement 7: Registry Subcommand Group Restructuring
+
+**User Story:** As a user, I want registry management commands organised under a `ksm registry` subcommand group with full-word subcommands, so that the CLI structure is consistent and discoverable.
+
+#### Acceptance Criteria
+
+1. THE CLI SHALL provide `ksm registry add <url>` to add a registry by URL
+2. THE CLI SHALL provide `ksm registry add -i` to launch an interactive registry add flow
+3. THE CLI SHALL provide `ksm registry remove <name>` to remove a named registry
+4. THE CLI SHALL provide `ksm registry list` to list all registered registries
+5. THE CLI SHALL provide `ksm registry inspect <name>` to inspect a named registry
+6. WHEN a user runs `ksm registry` without a subcommand, THE CLI SHALL print usage information listing the available subcommands (add, remove, list, inspect) to stderr and return exit code 2
+7. THE Registry_Subcommand SHALL use `remove` as the canonical subcommand name for removing a registry
+8. THE Registry_Subcommand SHALL use `list` as the canonical subcommand name for listing registries
+9. THE Registry_Subcommand SHALL accept `rm` as an alias for `remove` and `ls` as an alias for `list` for backward compatibility
+10. WHEN a user runs `ksm registry --help`, THE CLI SHALL print help text to stdout and return exit code 0
+11. WHEN a user runs `ksm registry <subcommand> --help`, THE CLI SHALL print help text for the subcommand to stdout and return exit code 0
+
+### Requirement 8: Deprecate Legacy add-registry Command
+
+**User Story:** As a user, I want the legacy `ksm add-registry` command to still work but warn me to use the new `ksm registry add` command, so that I can migrate at my own pace.
+
+#### Acceptance Criteria
+
+1. WHEN a user runs `ksm add-registry <url>`, THE CLI SHALL print a deprecation warning to stderr indicating that `ksm add-registry` is deprecated and `ksm registry add` should be used instead
+2. WHEN a user runs `ksm add-registry <url>`, THE Legacy_Add_Registry_Command SHALL still execute the registry add operation after printing the deprecation warning
+3. THE CLI SHALL retain the `add-registry` subparser for backward compatibility
+4. THE deprecation warning SHALL include the version in which `add-registry` was deprecated and the planned removal version
+
+### Requirement 9: Full-Word Top-Level Command Aliases
+
+**User Story:** As a user, I want to use full-word commands like `ksm list` and `ksm remove` in addition to the short forms `ksm ls` and `ksm rm`, so that the CLI is more readable and discoverable.
+
+#### Acceptance Criteria
+
+1. THE CLI SHALL accept `ksm list` as an alias for `ksm ls` with identical behaviour and flags
+2. THE CLI SHALL accept `ksm remove` as an alias for `ksm rm` with identical behaviour and flags
+3. THE CLI SHALL retain `ksm ls` as a supported alias for backward compatibility
+4. THE CLI SHALL retain `ksm rm` as a supported alias for backward compatibility
+5. WHEN a user runs `ksm list`, THE List_Command SHALL produce identical output to `ksm ls`
+6. WHEN a user runs `ksm remove <bundle_name>`, THE Remove_Command SHALL produce identical output to `ksm rm <bundle_name>`
+7. THE CLI help text SHALL show the full-word form as the primary command name with the short form in parentheses (e.g. `list (ls)`) as a single entry, not as two separate entries
+
+### Requirement 10: Qualified Bundle Name Syntax
+
+**User Story:** As a user, I want to use `registry_name/bundle_name` syntax to unambiguously specify which registry a bundle comes from, so that I can install the correct bundle when multiple registries contain bundles with the same name.
+
+#### Acceptance Criteria
+
+1. THE CLI SHALL accept `ksm add <registry_name>/<bundle_name>` to install a bundle from a specific registry
+2. THE resolver SHALL parse the `/` separator to extract registry name and bundle name
+3. WHEN the specified registry does not exist, THE CLI SHALL print an error listing available registries
+4. WHEN the specified bundle does not exist in the specified registry, THE CLI SHALL print an error
+5. THE Selector SHALL display ambiguous bundles using `registry_name/bundle_name` format
+6. THE Selector SHALL display unambiguous bundles using just the bundle name (no registry prefix)
+
+### Requirement 11: Registry Add — Custom Name Flag
+
+**User Story:** As a user, I want to specify a custom name when adding a registry, so that I can avoid name collisions when two registries have the same derived name.
+
+#### Acceptance Criteria
+
+1. THE CLI SHALL define a `--name <custom_name>` flag on the `registry add` subparser
+2. WHEN `--name` is provided, THE Registry_Add_Command SHALL use the custom name instead of the URL-derived name for the registry entry and cache directory
+3. WHEN `--name` is not provided, THE Registry_Add_Command SHALL derive the name from the URL as it does today
+4. WHEN the custom name conflicts with an existing registry name, THE Registry_Add_Command SHALL print an error to stderr and return exit code 1
+
+### Requirement 12: Consolidate --*-only Flags into --only
+
+**User Story:** As a user, I want a single `--only` flag instead of separate `--skills-only`, `--agents-only`, `--steering-only`, `--hooks-only` flags, so that the CLI is more concise and scalable.
+
+#### Acceptance Criteria
+
+1. THE CLI SHALL define an `--only` flag on the Add_Command that accepts one or more subdirectory types
+2. THE `--only` flag SHALL accept comma-separated values (e.g. `--only skills,hooks`)
+3. THE `--only` flag SHALL also accept repeated usage (e.g. `--only skills --only hooks`)
+4. THE valid values for `--only` SHALL be: skills, agents, steering, hooks
+5. WHEN an invalid value is provided to `--only`, THE CLI SHALL print an error listing valid values and return exit code 2
+6. THE CLI SHALL remove the individual `--skills-only`, `--agents-only`, `--steering-only`, `--hooks-only` flags from the visible help text
+7. WHEN a user passes any of the old `--*-only` flags, THE CLI SHALL print a deprecation warning to stderr and treat the flag as equivalent to the corresponding `--only` value
+8. THE `--only` flag SHALL be mutually exclusive with dot notation (e.g. `ksm add bundle.steering.item --only skills` is an error)
+
+### Requirement 13: Standardised Error Message Format
+
+**User Story:** As a user, I want consistent, actionable error messages across all ksm commands, so that I can quickly understand what went wrong and how to fix it.
+
+#### Acceptance Criteria
+
+1. ALL error messages SHALL follow a three-line format: (1) what happened, (2) why/context, (3) what to do / recovery action
+2. ALL error messages SHALL be printed to stderr
+3. ALL error messages SHALL start with `Error: ` prefix
+4. Warning messages SHALL start with `Warning: ` prefix
+5. Deprecation messages SHALL start with `Deprecated: ` prefix
+
+### Requirement 14: Registry Inspect Output Specification
+
+**User Story:** As a user, I want `ksm registry inspect <name>` to show useful information about a registry, so that I can understand what bundles are available and the registry's status.
+
+#### Acceptance Criteria
+
+1. THE Registry_Inspect_Command SHALL display the registry name, URL, local cache path, and whether it is the default registry
+2. THE Registry_Inspect_Command SHALL list all bundles found in the registry with their subdirectory types
+3. THE Registry_Inspect_Command SHALL print output to stdout in a human-readable format
+4. WHEN the registry name is not found, THE Registry_Inspect_Command SHALL print an error listing available registries
