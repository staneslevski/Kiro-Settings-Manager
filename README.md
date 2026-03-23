# Kiro Settings Manager (`ksm`)

A CLI tool for managing [Kiro IDE](https://kiro.dev) configuration bundles. Install, remove, sync, and organise bundles of skills, steering files, hooks, and agents across workspace and global scopes.

## Table of Contents

- [Installation](#installation)
- [Concepts](#concepts)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
- [Usage](#usage)
  - [ksm add](#ksm-add)
  - [ksm list](#ksm-list)
  - [ksm remove](#ksm-remove)
  - [ksm sync](#ksm-sync)
  - [ksm init](#ksm-init)
  - [ksm info](#ksm-info)
  - [ksm search](#ksm-search)
  - [ksm registry](#ksm-registry)
  - [ksm completions](#ksm-completions)
- [Built-in Bundles](#built-in-bundles)
- [Creating and Sharing Bundles](#creating-and-sharing-bundles)
  - [Bundle Structure](#bundle-structure)
  - [Create a Bundle Repository](#create-a-bundle-repository)
  - [Register and Install](#register-and-install)
  - [Share with Your Team](#share-with-your-team)
  - [Keep Bundles in Sync](#keep-bundles-in-sync)
- [Shell Completions](#shell-completions)
- [Development](#development)
- [Architecture](#architecture)
- [License](#license)

## Installation

Requires Python 3.10 or later.

### With pipx (recommended)

[pipx](https://pipx.pypa.io/) installs `ksm` in an isolated environment so it won't affect your global Python setup:

```bash
pipx install kiro-settings-manager
```

### With pip

```bash
pip install kiro-settings-manager
```

### From GitHub

```bash
pip install git+https://github.com/staneslevski/Kiro-Settings-Manager.git

# Or a specific version
pip install git+https://github.com/staneslevski/Kiro-Settings-Manager.git@v0.2.0
```

### From source (for development)

```bash
git clone https://github.com/staneslevski/Kiro-Settings-Manager.git
cd Kiro-Settings-Manager
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

See [Development](#development) for the full dev workflow.

## Concepts

**Bundle** — A directory containing one or more of `skills/`, `steering/`, `hooks/`, and `agents/`. Each bundle packages related Kiro configuration that you can install as a unit.

**Registry** — A source of bundles. `ksm` ships with a built-in default registry. You can register additional git repositories as registries to share bundles across teams.

**Scope** — Where bundles get installed. *Local* scope installs into the current workspace's `.kiro/` directory. *Global* scope installs into `~/.kiro/`, making bundles available across all workspaces. Local is the default.

**Manifest** — A JSON file (`~/.kiro/ksm/manifest.json`) that tracks every installed bundle, its scope, source registry, installed files, and timestamps.

## Quick Start

Bundles package Kiro skills, steering rules, hooks, and agents into installable units. Here's the typical workflow:

```bash
# Initialise .kiro/ in your project
ksm init

# Browse available bundles interactively
ksm add -i

# Install a bundle globally (available in all workspaces)
ksm add python_dev -g

# Install a single skill from a bundle
ksm add git_and_github.skills.github-pr -g

# List what's installed
ksm list

# Sync all installed bundles to pick up changes
ksm sync --all --yes

# Remove a bundle
ksm remove python_dev -g

# Check version
ksm --version
```

## Command Reference

| Command | Description |
|---------|-------------|
| `ksm add <bundle>` | Install a bundle or specific item |
| `ksm list` | List installed bundles (alias: `ls`) |
| `ksm remove <bundle>` | Remove an installed bundle (alias: `rm`) |
| `ksm sync` | Update bundles from their source registries |
| `ksm init` | Create `.kiro/` in the current directory |
| `ksm info <bundle>` | Show bundle metadata and install status |
| `ksm search <query>` | Find bundles by name across all registries |
| `ksm registry add\|list\|remove\|inspect` | Manage bundle registries |
| `ksm completions <shell>` | Generate shell completion scripts |
| `ksm --version` | Show version |

## Usage

### ksm add

Install a bundle or a specific item from a bundle.

```bash
# Install locally (into .kiro/ — this is the default)
ksm add python_dev

# Install globally (into ~/.kiro/)
ksm add python_dev -g

# Interactive selector — browse and pick
ksm add -i

# Dot notation — install one specific item
ksm add git_and_github.skills.github-pr -g

# Install only certain subdirectories (comma-separated)
ksm add project_foundations --only steering -g
ksm add aws --only skills,steering

# Install from any git URL (one-off, source is not registered)
ksm add my-bundle --from https://github.com/org/repo.git -g
```

| Flag | Description |
|------|-------------|
| `-l`, `--local` | Install into workspace `.kiro/` (default) |
| `-g`, `--global` | Install into `~/.kiro/` |
| `-i`, `--interactive` | Launch the interactive bundle selector |
| `--only <types>` | Comma-separated filter: `skills`, `steering`, `hooks`, `agents` |
| `--from <url>` | Install from a git URL without registering it |

The `--from` flag clones the repository temporarily, copies the bundle files, and removes the clone. The installed files are tracked in the manifest, but the source is not saved as a registry. To permanently register a source, use `ksm registry add`.

Dot notation (`bundle.subdir.item`) and `--only` are mutually exclusive.

### ksm list

List all installed bundles. Output is grouped by scope — local bundles first, then global. Each entry shows the bundle name, source registry, and a relative timestamp.

Alias: `ksm ls`

```bash
ksm list                # List all installed bundles
ksm list -v             # Include installed file paths
ksm list --scope local  # Show only workspace-level bundles
ksm list --scope global # Show only user-level bundles
ksm list --format json  # Machine-readable JSON (pipe to jq, etc.)
```

Example output:

```
Local bundles:
  git_and_github  (default)  2 days ago

Global bundles:
  python_dev      (default)  5 minutes ago
  aws             (default)  1 week ago
```

With `-v`, installed file paths appear under each bundle:

```
Local bundles:
  git_and_github  (default)  2 days ago
    steering/git-branching.md
    skills/github-pr/SKILL.md
```

### ksm remove

Remove an installed bundle and delete its files.

Alias: `ksm rm`

```bash
ksm remove python_dev      # Remove a local bundle
ksm remove python_dev -g   # Remove a global bundle
ksm remove -i              # Interactive removal selector
```

| Flag | Description |
|------|-------------|
| `-l`, `--local` | Remove from workspace `.kiro/` |
| `-g`, `--global` | Remove from `~/.kiro/` |
| `-i`, `--interactive` | Launch the interactive removal selector |

### ksm sync

Re-install bundles from their source registries to pick up changes. For git-based registries, `sync` pulls the latest commits before copying.

```bash
ksm sync python_dev    # Sync specific bundles
ksm sync --all         # Sync everything
ksm sync --all --yes   # Skip the confirmation prompt
```

Sync respects the original install scope — a bundle installed globally will be synced globally.

### ksm init

Create the `.kiro/` directory in the current workspace. If running in an interactive terminal, `ksm init` also launches the bundle selector so you can install bundles straight away.

```bash
ksm init
```

```
✓ Initialised .kiro/ in current directory
  Run 'ksm add' to install your first bundle.
```

### ksm info

Show metadata for a bundle: its registry, contents breakdown, and whether it's currently installed.

```bash
ksm info python_dev
```

```
python_dev
  Registry   default
  Contents   agents/ 2 items · steering/ 2 items
  Installed  global
```

If the bundle doesn't exist, `ksm` tells you what went wrong and what to do:

```
error: Bundle 'nonexistent' not found.
  Searched: default
  Run `ksm search <query>` to find available bundles.
```

### ksm search

Case-insensitive name search across all registered registries.

```bash
ksm search python
```

```
  python_dev  default  agents, steering
```

### ksm registry

Manage bundle registries. The `registry` command has four subcommands:

```bash
# Add a git repository as a registry
ksm registry add https://github.com/org/shared-bundles.git

# Give it a custom name
ksm registry add https://github.com/org/shared-bundles.git --name team

# Force re-clone a cached registry
ksm registry add https://github.com/org/shared-bundles.git -f

# List all registered registries
ksm registry list

# Inspect a registry — see all its bundles
ksm registry inspect team

# Remove a user-added registry
ksm registry remove team
```

Aliases: `ksm registry ls`, `ksm registry rm`

The legacy `ksm add-registry` command still works but `ksm registry add` is preferred.

### ksm completions

Generate shell completion scripts for tab-completion of commands and arguments.

```bash
ksm completions bash   # Bash
ksm completions zsh    # Zsh
ksm completions fish   # Fish
```

See [Shell Completions](#shell-completions) for setup instructions.

## Built-in Bundles

These bundles ship with `ksm` in the default registry:

| Bundle | Contents | Description |
|--------|----------|-------------|
| `aws` | skills, steering | AWS-focused skills and steering rules (IAM, MCP) |
| `cli-tools` | agents | CLI engineering agent |
| `example_conf_bund` | agents, hooks, skills, steering | Example bundle demonstrating all subdirectory types |
| `git_and_github` | agents, skills, steering | Git branching rules, GitHub PR skill, README writer agent |
| `kiro_power_usage` | agents, skills | Task builder agent, skill-creating skill |
| `project_foundations` | skills, steering | Project structure and scaffolding guidance |
| `python_dev` | agents, steering | Python development standards, hypothesis testing agent |
| `ux-design` | agents | UX designer agent |

Browse them interactively with `ksm add -i`, or inspect one with `ksm info <bundle>`.

## Creating and Sharing Bundles

You can create your own bundles and share them with your team through a git repository.

### Bundle Structure

A bundle is a directory with at least one of these subdirectories:

```
my-bundle/
├── skills/       # Kiro skill definitions (SKILL.md files)
├── steering/     # Steering markdown files (.md)
├── hooks/        # Hook definitions (.json)
└── agents/       # Custom agent definitions
```

| Type | File format | Purpose |
|------|-------------|---------|
| `skills/` | `SKILL.md` per skill | Define agent capabilities and workflows |
| `steering/` | `.md` files | Provide rules and context to guide agent behaviour |
| `hooks/` | `.json` files | Automate agent actions on IDE events |
| `agents/` | Agent definitions | Custom specialised agents |

### Create a Bundle Repository

1. Create a new GitHub repository to hold your bundles:

```bash
mkdir my-kiro-bundles
cd my-kiro-bundles
git init
```

2. Add one or more bundle directories. Each top-level directory that contains `skills/`, `steering/`, `hooks/`, or `agents/` is automatically recognised as a bundle:

```
my-kiro-bundles/
├── team-standards/
│   ├── steering/
│   │   ├── code-review.md
│   │   └── testing-policy.md
│   └── hooks/
│       └── lint-on-save.json
├── backend-tools/
│   ├── skills/
│   │   └── api-design/
│   │       └── SKILL.md
│   └── agents/
│       └── backend-reviewer.md
└── README.md
```

3. Commit and push:

```bash
git add .
git commit -m "Initial bundles"
git remote add origin https://github.com/your-org/my-kiro-bundles.git
git push -u origin main
```

### Register and Install

Register your repository as a bundle source, then install bundles from it:

```bash
# Register the repository
ksm registry add https://github.com/your-org/my-kiro-bundles.git

# Verify it was added
ksm registry list

# See what bundles are available
ksm registry inspect my-kiro-bundles

# Install a bundle globally
ksm add team-standards -g

# Or install just the steering files
ksm add team-standards --only steering -g
```

You can also do a one-off install without registering the repository:

```bash
ksm add team-standards --from https://github.com/your-org/my-kiro-bundles.git -g
```

### Share with Your Team

Once your repository is on GitHub, teammates register it with a single command:

```bash
ksm registry add https://github.com/your-org/my-kiro-bundles.git
ksm add team-standards -g
```

For private repositories, ensure team members have git access (SSH keys or HTTPS credentials).

### Keep Bundles in Sync

When you push updates to your bundle repository, team members pull the latest with:

```bash
ksm sync team-standards          # Sync a specific bundle
ksm sync --all --yes             # Sync everything at once
```

`sync` pulls the latest commits from the source registry before re-copying the bundle files.

## Shell Completions

Enable tab-completion for `ksm` commands and arguments:

```bash
# Bash — add to ~/.bashrc
eval "$(ksm completions bash)"

# Zsh — add to ~/.zshrc
eval "$(ksm completions zsh)"

# Fish
ksm completions fish > ~/.config/fish/completions/ksm.fish
```

## Development

```bash
git clone https://github.com/staneslevski/Kiro-Settings-Manager.git
cd Kiro-Settings-Manager
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

All commands below assume the virtual environment is activated (`source .venv/bin/activate`):

```bash
pytest                              # Run tests
pytest --cov=ksm tests/             # Run tests with coverage
black src/ tests/                   # Format code
flake8 src/ tests/                  # Lint
mypy src/ tests/                    # Type check
HYPOTHESIS_PROFILE=ci pytest        # Thorough property tests (CI mode)
```

### Utility Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sync-to-kiro-settings.sh` | Merges `settings/allowed_commands.txt` into Kiro's `settings.json` |
| `scripts/update-allowed-commands.sh` | Extracts trusted commands from Kiro's `settings.json` |

## Architecture

```
src/ksm/
├── cli.py              # Argument parsing and command dispatch
├── commands/
│   ├── add.py          # ksm add
│   ├── add_registry.py # ksm add-registry (legacy)
│   ├── completions.py  # ksm completions
│   ├── info.py         # ksm info
│   ├── init.py         # ksm init
│   ├── ls.py           # ksm list / ls
│   ├── registry_add.py # ksm registry add
│   ├── registry_inspect.py # ksm registry inspect
│   ├── registry_ls.py  # ksm registry list
│   ├── registry_rm.py  # ksm registry remove
│   ├── rm.py           # ksm remove / rm
│   ├── search.py       # ksm search
│   └── sync.py         # ksm sync
├── scanner.py          # Discovers valid bundles in a registry directory
├── resolver.py         # Finds a bundle by name across all registries
├── installer.py        # Copies bundle files to target .kiro/ directory
├── copier.py           # Low-level file/tree copy operations
├── remover.py          # Deletes installed bundle files
├── manifest.py         # Tracks installed bundles (manifest.json)
├── registry.py         # Manages registered bundle sources (registries.json)
├── persistence.py      # JSON I/O and path constants
├── selector.py         # Interactive terminal bundle selector
├── dot_notation.py     # Parses bundle.subdir.item selectors
├── git_ops.py          # Git clone/pull operations
└── errors.py           # Custom exception types
```

State is stored in `~/.kiro/ksm/`:
- `manifest.json` — records every installed bundle, its scope, source, and file list
- `registries.json` — lists all registered bundle sources (default + any added git registries)
- `cache/` — cloned git registries

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.

See [Shell Completions](#shell-completions) for setup instructions.

## Built-in Bundles

These bundles ship with `ksm` in the default registry:

| Bundle | Contents | Description |
|--------|----------|-------------|
| `aws` | skills, steering | AWS-focused skills and steering rules (IAM, MCP) |
| `cli-tools` | agents | CLI engineering agent |
| `example_conf_bund` | agents, hooks, skills, steering | Example bundle demonstrating all subdirectory types |
| `git_and_github` | agents, skills, steering | Git branching rules, GitHub PR skill, README writer agent |
| `kiro_power_usage` | agents, skills | Task builder agent, skill-creating skill |
| `project_foundations` | skills, steering | Project structure and scaffolding guidance |
| `python_dev` | agents, steering | Python development standards, hypothesis testing agent |
| `ux-design` | agents | UX designer agent |

Browse them interactively with `ksm add -i`, or inspect one with `ksm info <bundle>`.

## Creating and Sharing Bundles

You can create your own bundles and share them with your team through a git repository.

### Bundle Structure

A bundle is a directory with at least one of these subdirectories:

```
my-bundle/
├── skills/       # Kiro skill definitions (SKILL.md files)
├── steering/     # Steering markdown files (.md)
├── hooks/        # Hook definitions (.json)
└── agents/       # Custom agent definitions
```

| Type | File format | Purpose |
|------|-------------|---------|
| `skills/` | `SKILL.md` per skill | Define agent capabilities and workflows |
| `steering/` | `.md` files | Provide rules and context to guide agent behaviour |
| `hooks/` | `.json` files | Automate agent actions on IDE events |
| `agents/` | Agent definitions | Custom specialised agents |

### Create a Bundle Repository

1. Create a new GitHub repository to hold your bundles:

```bash
mkdir my-kiro-bundles
cd my-kiro-bundles
git init
```

2. Add one or more bundle directories. Each top-level directory that contains `skills/`, `steering/`, `hooks/`, or `agents/` is automatically recognised as a bundle:

```
my-kiro-bundles/
├── team-standards/
│   ├── steering/
│   │   ├── code-review.md
│   │   └── testing-policy.md
│   └── hooks/
│       └── lint-on-save.json
├── backend-tools/
│   ├── skills/
│   │   └── api-design/
│   │       └── SKILL.md
│   └── agents/
│       └── backend-reviewer.md
└── README.md
```

3. Commit and push:

```bash
git add .
git commit -m "Initial bundles"
git remote add origin https://github.com/your-org/my-kiro-bundles.git
git push -u origin main
```

### Register and Install

Register your repository as a bundle source, then install bundles from it:

```bash
# Register the repository
ksm registry add https://github.com/your-org/my-kiro-bundles.git

# Verify it was added
ksm registry list

# See what bundles are available
ksm registry inspect my-kiro-bundles

# Install a bundle globally
ksm add team-standards -g

# Or install just the steering files
ksm add team-standards --only steering -g
```

You can also do a one-off install without registering the repository:

```bash
ksm add team-standards --from https://github.com/your-org/my-kiro-bundles.git -g
```

### Share with Your Team

Once your repository is on GitHub, teammates register it with a single command:

```bash
ksm registry add https://github.com/your-org/my-kiro-bundles.git
ksm add team-standards -g
```

For private repositories, ensure team members have git access (SSH keys or HTTPS credentials).

### Keep Bundles in Sync

When you push updates to your bundle repository, team members pull the latest with:

```bash
ksm sync team-standards          # Sync a specific bundle
ksm sync --all --yes             # Sync everything at once
```

`sync` pulls the latest commits from the source registry before re-copying the bundle files.

## Shell Completions

Enable tab-completion for `ksm` commands and arguments:

```bash
# Bash — add to ~/.bashrc
eval "$(ksm completions bash)"

# Zsh — add to ~/.zshrc
eval "$(ksm completions zsh)"

# Fish
ksm completions fish > ~/.config/fish/completions/ksm.fish
```

## Development

```bash
git clone https://github.com/staneslevski/Kiro-Settings-Manager.git
cd Kiro-Settings-Manager
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

All commands below assume the virtual environment is activated (`source .venv/bin/activate`):

```bash
pytest                              # Run tests
pytest --cov=ksm tests/             # Run tests with coverage
black src/ tests/                   # Format code
flake8 src/ tests/                  # Lint
mypy src/ tests/                    # Type check
HYPOTHESIS_PROFILE=ci pytest        # Thorough property tests (CI mode)
```

### Utility Scripts

| Script | Purpose |
|--------|---------|
| `scripts/sync-to-kiro-settings.sh` | Merges `settings/allowed_commands.txt` into Kiro's `settings.json` |
| `scripts/update-allowed-commands.sh` | Extracts trusted commands from Kiro's `settings.json` |

## Architecture

```
src/ksm/
├── cli.py              # Argument parsing and command dispatch
├── commands/
│   ├── add.py          # ksm add
│   ├── add_registry.py # ksm add-registry (legacy)
│   ├── completions.py  # ksm completions
│   ├── info.py         # ksm info
│   ├── init.py         # ksm init
│   ├── ls.py           # ksm list / ls
│   ├── registry_add.py # ksm registry add
│   ├── registry_inspect.py # ksm registry inspect
│   ├── registry_ls.py  # ksm registry list
│   ├── registry_rm.py  # ksm registry remove
│   ├── rm.py           # ksm remove / rm
│   ├── search.py       # ksm search
│   └── sync.py         # ksm sync
├── scanner.py          # Discovers valid bundles in a registry directory
├── resolver.py         # Finds a bundle by name across all registries
├── installer.py        # Copies bundle files to target .kiro/ directory
├── copier.py           # Low-level file/tree copy operations
├── remover.py          # Deletes installed bundle files
├── manifest.py         # Tracks installed bundles (manifest.json)
├── registry.py         # Manages registered bundle sources (registries.json)
├── persistence.py      # JSON I/O and path constants
├── selector.py         # Interactive terminal bundle selector
├── dot_notation.py     # Parses bundle.subdir.item selectors
├── git_ops.py          # Git clone/pull operations
└── errors.py           # Custom exception types
```

State is stored in `~/.kiro/ksm/`:
- `manifest.json` — records every installed bundle, its scope, source, and file list
- `registries.json` — lists all registered bundle sources (default + any added git registries)
- `cache/` — cloned git registries

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
