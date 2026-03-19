# Requirements Document

## Introduction

The Kiro Settings Manager (`ksm`) is a Python CLI tool distributed as `kiro-settings-manager` via pip. It manages Kiro IDE/CLI configuration bundles — installing, listing, syncing, and sourcing them from local or remote registries. Bundles contain subdirectories (`skills/`, `steering/`, `hooks/`, `agents/`) whose contents are copied into a target `.kiro/` directory either locally (workspace) or globally (`~/.kiro/`).

## Glossary

- **CLI**: The `ksm` command-line interface entry point
- **Bundle**: A named directory inside a registry containing Kiro configuration subdirectories (`skills/`, `steering/`, `hooks/`, `agents/`)
- **Registry**: A directory (local or cloned git repository) containing one or more Bundles
- **Default_Registry**: The `config_bundles/` directory shipped with this repository, serving as the built-in Registry
- **Custom_Registry**: A git repository URL added by the user as an additional source of Bundles
- **Registry_Index**: A persistent JSON file tracking all registered Registry sources and their locations on disk
- **Local_Install**: Installation of Bundle contents into the workspace-level `.kiro/` directory
- **Global_Install**: Installation of Bundle contents into the user's home-level `~/.kiro/` directory
- **Install_Manifest**: A persistent JSON record of which Bundles are installed, their source Registry, install scope (local/global), and installed file paths
- **Interactive_Selector**: A terminal UI component that displays a scrollable list of Bundles for selection using arrow keys
- **Bundle_Subdirectory**: One of the recognised subdirectories inside a Bundle: `skills/`, `steering/`, `hooks/`, `agents/`
- **Sync_Operation**: The process of re-copying Bundle contents from the Registry to the install target, updating any changed files
- **Sync_Confirmation_Prompt**: A terminal prompt displayed before a Sync_Operation that warns the user the operation will overwrite current configuration files and requires explicit confirmation to proceed
- **Ephemeral_Registry**: A git repository used as a temporary Registry for a single `ksm add` invocation via the `--from` flag; the repository is cloned to a temporary directory, the requested Bundle is installed, and the temporary clone is deleted after the command completes; the repository is not added to the Registry_Index
- **Subdirectory_Filter**: A CLI flag (`--skills-only`, `--agents-only`, `--steering-only`, `--hooks-only`) that restricts which Bundle_Subdirectories are copied during a `ksm add` installation
- **Dot_Notation_Selector**: A qualified bundle reference in the format `<bundle_name>.<subdirectory_type>.<item_name>` that targets a single item within a specific Bundle_Subdirectory for installation (e.g. `aws.skills.aws-cross-account`)
- **Removal_Selector**: A terminal UI component that displays a scrollable list of installed Bundles (sourced from the Install_Manifest) for selection and removal using arrow keys

## Requirements

### Requirement 1: Bundle Installation

**User Story:** As a developer, I want to install a named configuration bundle so that its skills, steering files, hooks, and agents are available in my Kiro environment.

#### Acceptance Criteria

1. WHEN the user runs `ksm add <bundle_name>`, THE CLI SHALL copy all Bundle_Subdirectory contents from the matching Bundle in the Registry to the target `.kiro/` directory.
2. WHEN the user supplies the `-l` flag, THE CLI SHALL install Bundle contents to the workspace-level `.kiro/` directory.
3. WHEN the user supplies the `-g` flag, THE CLI SHALL install Bundle contents to the user's home-level `~/.kiro/` directory.
4. WHEN neither `-l` nor `-g` is supplied, THE CLI SHALL default to Local_Install.
5. IF the specified `<bundle_name>` does not exist in any registered Registry, THEN THE CLI SHALL print an error message naming the unknown bundle and exit with a non-zero status code.
6. IF the target `.kiro/` subdirectory does not exist, THEN THE CLI SHALL create the subdirectory before copying files.
7. WHEN a Bundle is successfully installed, THE CLI SHALL record the bundle name, source Registry, install scope, and list of installed file paths in the Install_Manifest.
8. IF a Bundle is already installed at the same scope, THEN THE CLI SHALL overwrite the existing files and update the Install_Manifest.

### Requirement 2: Interactive Bundle Selection

**User Story:** As a developer, I want to browse available bundles in an interactive terminal UI so that I can discover and select a bundle without memorising its name.

#### Acceptance Criteria

1. WHEN the user runs `ksm add --display`, THE Interactive_Selector SHALL present all available Bundles from all registered Registries.
2. THE Interactive_Selector SHALL display Bundles in alphabetical order by bundle name.
3. THE Interactive_Selector SHALL use the `>` character as the selector symbol for the currently highlighted Bundle.
4. THE Interactive_Selector SHALL use the terminal's current default color scheme without applying custom colors.
5. THE Interactive_Selector SHALL indicate whether each listed Bundle is already installed by displaying an `[installed]` label next to installed Bundles.
6. WHEN the user presses the up or down arrow keys, THE Interactive_Selector SHALL move the selection highlight accordingly.
7. WHEN the user presses Enter, THE CLI SHALL install the selected Bundle using the same installation logic as `ksm add <bundle_name>`.
8. WHEN the user presses `q` or Escape, THE Interactive_Selector SHALL exit without installing any Bundle.

### Requirement 3: List Installed Bundles

**User Story:** As a developer, I want to list all currently installed bundles so that I can see what configuration is active in my environment.

#### Acceptance Criteria

1. WHEN the user runs `ksm ls`, THE CLI SHALL read the Install_Manifest and display all installed Bundles.
2. THE CLI SHALL display each installed Bundle's name, install scope (local or global), and source Registry.
3. IF no Bundles are installed, THEN THE CLI SHALL print a message indicating that no bundles are currently installed.

### Requirement 4: Sync Bundles

**User Story:** As a developer, I want to update installed bundles from their source registries so that I have the latest configuration files.

#### Acceptance Criteria

1. WHEN the user runs `ksm sync <bundle_name> [<bundle_name> ...]`, THE CLI SHALL display a Sync_Confirmation_Prompt before proceeding with the Sync_Operation.
2. WHEN the user runs `ksm sync --all`, THE CLI SHALL display a Sync_Confirmation_Prompt before proceeding with the Sync_Operation.
3. THE Sync_Confirmation_Prompt SHALL display a warning message stating that the sync will overwrite current configuration files and ask the user to confirm by typing `y` or `n`.
4. IF the user responds with `n` or any value other than `y` to the Sync_Confirmation_Prompt, THEN THE CLI SHALL abort the Sync_Operation and exit with a zero status code.
5. WHEN the user supplies the `--yes` flag, THE CLI SHALL skip the Sync_Confirmation_Prompt and proceed directly with the Sync_Operation.
6. WHEN the user confirms the Sync_Confirmation_Prompt, THE CLI SHALL re-copy the contents of each specified Bundle from its source Registry to the install target.
7. WHEN the user confirms the Sync_Confirmation_Prompt with `--all`, THE CLI SHALL re-copy the contents of all installed Bundles from their source Registries.
8. IF a specified bundle name is not found in the Install_Manifest, THEN THE CLI SHALL print an error message naming the unknown bundle and continue syncing remaining bundles.
9. WHEN a Custom_Registry is a git repository, THE CLI SHALL pull the latest changes from the remote before copying Bundle contents during a Sync_Operation.
10. WHEN a Sync_Operation completes for a Bundle, THE CLI SHALL update the Install_Manifest with the current timestamp.
11. IF neither bundle names nor `--all` is supplied, THEN THE CLI SHALL print a usage message explaining that at least one bundle name or `--all` is required.

### Requirement 5: Add Custom Registry

**User Story:** As a developer, I want to register additional git repositories as bundle registries so that I can access shared configuration bundles maintained by my team.

#### Acceptance Criteria

1. WHEN the user runs `ksm add-registry <git_url>`, THE CLI SHALL clone the git repository to a local cache directory.
2. WHEN the repository is cloned, THE CLI SHALL scan the repository root for directories that contain at least one Bundle_Subdirectory (`skills/`, `steering/`, `hooks/`, or `agents/`) and register each as a Bundle.
3. THE CLI SHALL store the git URL and local cache path in the Registry_Index.
4. IF the git URL is already registered in the Registry_Index, THEN THE CLI SHALL print a message indicating the registry is already registered and exit with a zero status code.
5. IF the git clone operation fails, THEN THE CLI SHALL print an error message describing the failure and exit with a non-zero status code.

### Requirement 6: Registry Index Persistence

**User Story:** As a developer, I want registry and installation data to persist across CLI invocations so that I do not need to re-register or re-install bundles each session.

#### Acceptance Criteria

1. THE CLI SHALL store the Registry_Index as a JSON file at `~/.kiro/ksm/registries.json`.
2. THE CLI SHALL store the Install_Manifest as a JSON file at `~/.kiro/ksm/manifest.json`.
3. WHEN the `~/.kiro/ksm/` directory does not exist, THE CLI SHALL create the directory before writing persistence files.
4. THE CLI SHALL include the Default_Registry in the Registry_Index on first run without requiring user action.
5. FOR ALL valid Registry_Index JSON content, writing then reading the file SHALL produce an equivalent data structure (round-trip property).
6. FOR ALL valid Install_Manifest JSON content, writing then reading the file SHALL produce an equivalent data structure (round-trip property).

### Requirement 7: Bundle File Copying

**User Story:** As a developer, I want bundle installation to correctly copy all files from bundle subdirectories so that my Kiro environment has complete configuration.

#### Acceptance Criteria

1. THE CLI SHALL copy only recognised Bundle_Subdirectories (`skills/`, `steering/`, `hooks/`, `agents/`) from a Bundle, ignoring other files or directories at the Bundle root.
2. THE CLI SHALL preserve the directory structure within each Bundle_Subdirectory when copying to the target `.kiro/` directory.
3. THE CLI SHALL preserve file contents exactly during copy operations (byte-for-byte equivalence).
4. IF a file in the target directory already exists and has identical content to the source, THEN THE CLI SHALL skip the copy for that file.
5. FOR ALL files copied during installation, reading the source file and the destination file SHALL produce identical byte content (round-trip property).

### Requirement 8: CLI Entry Point and Packaging

**User Story:** As a developer, I want to install the tool via pip and invoke it as `ksm` so that it integrates with standard Python tooling.

#### Acceptance Criteria

1. THE package SHALL be installable via `pip install kiro-settings-manager`.
2. WHEN installed, THE package SHALL provide a `ksm` command available on the system PATH.
3. THE CLI SHALL display a help message listing all available commands when invoked with `ksm --help`.
4. THE CLI SHALL display a version string when invoked with `ksm --version`.
5. IF an unknown command is provided, THEN THE CLI SHALL print an error message listing valid commands and exit with a non-zero status code.

### Requirement 9: Ephemeral Registry via --from Flag

**User Story:** As a developer, I want to install a bundle directly from an external git repository without permanently registering it, so that I can quickly pull configuration from ad-hoc sources.

#### Acceptance Criteria

1. WHEN the user runs `ksm add <bundle_name> --from <git_url>`, THE CLI SHALL clone the specified git repository to a temporary directory.
2. WHEN the temporary clone is complete, THE CLI SHALL search the cloned repository for a Bundle matching `<bundle_name>` and install the Bundle using the same installation logic as `ksm add <bundle_name>`.
3. THE CLI SHALL NOT add the git URL from the `--from` flag to the Registry_Index.
4. WHEN the installation completes (success or failure), THE CLI SHALL delete the temporary clone directory.
5. IF the git clone operation for the `--from` URL fails, THEN THE CLI SHALL print an error message describing the failure and exit with a non-zero status code.
6. IF the specified `<bundle_name>` does not exist in the temporarily cloned repository, THEN THE CLI SHALL print an error message naming the unknown bundle, delete the temporary clone, and exit with a non-zero status code.
7. WHEN a Bundle is installed via `--from`, THE CLI SHALL record the source as the git URL in the Install_Manifest so the origin is traceable.
8. THE `--from` flag SHALL be combinable with `-l`, `-g`, Subdirectory_Filter flags, and Dot_Notation_Selector syntax.

### Requirement 10: Subdirectory Type Filters

**User Story:** As a developer, I want to restrict which types of configuration files are installed from a bundle, so that I can selectively pull only skills, agents, steering, or hooks as needed.

#### Acceptance Criteria

1. WHEN the user supplies `--skills-only`, THE CLI SHALL copy only the `skills/` Bundle_Subdirectory from the specified Bundle during installation.
2. WHEN the user supplies `--agents-only`, THE CLI SHALL copy only the `agents/` Bundle_Subdirectory from the specified Bundle during installation.
3. WHEN the user supplies `--steering-only`, THE CLI SHALL copy only the `steering/` Bundle_Subdirectory from the specified Bundle during installation.
4. WHEN the user supplies `--hooks-only`, THE CLI SHALL copy only the `hooks/` Bundle_Subdirectory from the specified Bundle during installation.
5. WHEN multiple Subdirectory_Filter flags are supplied in the same command, THE CLI SHALL copy only the Bundle_Subdirectories corresponding to the specified filters.
6. WHEN no Subdirectory_Filter flag is supplied, THE CLI SHALL copy all recognised Bundle_Subdirectories (default behaviour, unchanged from Requirement 1).
7. IF a Subdirectory_Filter is specified but the Bundle does not contain the corresponding Bundle_Subdirectory, THEN THE CLI SHALL print a warning message naming the missing subdirectory and continue with any remaining applicable subdirectories.
8. IF all specified Subdirectory_Filters refer to subdirectories that do not exist in the Bundle, THEN THE CLI SHALL print an error message and exit with a non-zero status code.
9. WHEN a filtered installation completes, THE CLI SHALL record only the actually installed file paths in the Install_Manifest.
10. THE Subdirectory_Filter flags SHALL be combinable with `-l`, `-g`, `--from`, and Dot_Notation_Selector syntax.

### Requirement 11: Dot Notation for Granular Item Selection

**User Story:** As a developer, I want to target a specific item within a bundle subdirectory using dot notation, so that I can cherry-pick individual skills, agents, steering files, or hooks without installing the entire bundle.

#### Acceptance Criteria

1. WHEN the user runs `ksm add <bundle_name>.<subdirectory_type>.<item_name>`, THE CLI SHALL install only the item matching `<item_name>` from the `<subdirectory_type>/` Bundle_Subdirectory of the specified Bundle.
2. THE CLI SHALL recognise `skills`, `agents`, `steering`, and `hooks` as valid values for `<subdirectory_type>` in the Dot_Notation_Selector.
3. IF the `<subdirectory_type>` in the Dot_Notation_Selector is not one of the recognised values, THEN THE CLI SHALL print an error message listing valid subdirectory types and exit with a non-zero status code.
4. IF the `<item_name>` does not exist within the specified `<subdirectory_type>/` directory of the Bundle, THEN THE CLI SHALL print an error message naming the unknown item and exit with a non-zero status code.
5. WHEN the `<item_name>` refers to a directory (e.g. a skill folder), THE CLI SHALL copy the entire directory and its contents to the target `.kiro/<subdirectory_type>/` path.
6. WHEN the `<item_name>` refers to a single file, THE CLI SHALL copy that file to the target `.kiro/<subdirectory_type>/` path.
7. WHEN a Dot_Notation_Selector installation completes, THE CLI SHALL record only the actually installed item paths in the Install_Manifest.
8. THE Dot_Notation_Selector SHALL be combinable with `-l`, `-g`, and `--from` flags.
9. IF the Dot_Notation_Selector is used together with a Subdirectory_Filter flag, THEN THE CLI SHALL print an error message explaining that these options are mutually exclusive and exit with a non-zero status code.

### Requirement 12: Bundle Removal

**User Story:** As a developer, I want to remove an installed bundle so that I can clean up configuration I no longer need from my Kiro environment.

#### Acceptance Criteria

1. WHEN the user runs `ksm rm <bundle_name>`, THE CLI SHALL delete all files that were installed by the specified Bundle, using the Install_Manifest to determine which files to remove.
2. WHEN the removal of installed files completes, THE CLI SHALL remove the Bundle's entry from the Install_Manifest.
3. IF the specified `<bundle_name>` is not found in the Install_Manifest, THEN THE CLI SHALL print an error message stating that the bundle is not installed and exit with a non-zero status code.
4. WHEN the user supplies the `-l` flag, THE CLI SHALL remove the Bundle installed at the workspace-level `.kiro/` directory.
5. WHEN the user supplies the `-g` flag, THE CLI SHALL remove the Bundle installed at the user's home-level `~/.kiro/` directory.
6. WHEN neither `-l` nor `-g` is supplied, THE CLI SHALL default to removing the Local_Install of the specified Bundle.
7. IF a file listed in the Install_Manifest no longer exists on disk, THEN THE CLI SHALL skip that file and continue removing the remaining files.
8. WHEN all files for a Bundle_Subdirectory have been removed and the subdirectory is empty, THE CLI SHALL leave the empty subdirectory in place without deleting it.
9. WHEN the user runs `ksm rm --display`, THE Removal_Selector SHALL present only installed Bundles sourced from the Install_Manifest.
10. THE Removal_Selector SHALL display installed Bundles in alphabetical order by bundle name.
11. THE Removal_Selector SHALL use the `>` character as the selector symbol for the currently highlighted Bundle.
12. THE Removal_Selector SHALL use the terminal's current default color scheme without applying custom colors.
13. THE Removal_Selector SHALL display the install scope (local or global) next to each listed Bundle.
14. WHEN the user presses the up or down arrow keys, THE Removal_Selector SHALL move the selection highlight accordingly.
15. WHEN the user presses Enter, THE CLI SHALL remove the selected Bundle using the same removal logic as `ksm rm <bundle_name>`.
16. WHEN the user presses `q` or Escape, THE Removal_Selector SHALL exit without removing any Bundle.
17. IF no Bundles are installed, THEN THE Removal_Selector SHALL print a message indicating that no bundles are currently installed and exit with a zero status code.
