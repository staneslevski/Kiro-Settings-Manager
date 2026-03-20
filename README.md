# Kiro Settings Manager (`ksm`)

A CLI tool for managing [Kiro IDE](https://kiro.dev) configuration bundles. `ksm` lets you install, remove, sync, and organise bundles of skills, steering files, hooks, and agents across local (workspace) and global (`~/.kiro/`) scopes.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [ksm add](#ksm-add)
  - [ksm ls](#ksm-ls)
  - [ksm sync](#ksm-sync)
  - [ksm rm](#ksm-rm)
  - [ksm add-registry](#ksm-add-registry)
- [Config Bundles](#config-bundles)
  - [Built-in Bundles](#built-in-bundles)
  - [Authoring a Bundle](#authoring-a-bundle)
- [Architecture](#architecture)
- [Development](#development)

## Features

- Install configuration bundles locally (`.kiro/`) or globally (`~/.kiro/`)
- Interactive terminal selector for browsing and choosing bundles
- Dot-notation targeting to install a single item from a bundle (e.g. `git_and_github.skills.github-pr`)
- Subdirectory filters to install only skills, steering, hooks, or agents
- Registry system with a built-in default registry and support for adding external git registries
- Ephemeral installs from any git URL via `--from`
- Sync installed bundles to pull the latest changes from their source registries
- Persistent manifest tracking what is installed, where, and when

## Prerequisites

- Python 3.10 or later

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd Kiro-Settings-Manager

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

After installation the `ksm` command is available in your shell (while the venv is active).

## Quick Start

```bash
# Browse available bundles interactively
ksm add --display

# Install a bundle globally
ksm add python_dev -g

# Install a single skill from a bundle
ksm add git_and_github.skills.github-pr -g

# List installed bundles
ksm ls

# Sync all installed bundles to latest
ksm sync --all --yes

# Remove a bundle
ksm rm python_dev -g
```

## Usage

### ksm add

Install a bundle or a specific item from a bundle.

```bash
# Install a full bundle locally (into .kiro/)
ksm add python_dev

# Install globally (into ~/.kiro/)
ksm add python_dev -g

# Interactive selector
ksm add --display

# Dot notation — install one item
ksm add git_and_github.skills.github-pr -g

# Install only steering files from a bundle
ksm add project_foundations --steering-only -g

# Install from an external git repo (ephemeral, not registered)
ksm add my-bundle --from https://github.com/org/repo.git -g
```

Subdirectory filter flags: `--skills-only`, `--steering-only`, `--hooks-only`, `--agents-only`. These are mutually exclusive with dot notation.

### ksm ls

List all installed bundles with their scope and source registry.

```bash
ksm ls
```

Example output:

```
python_dev  [global]  (source: default)
git_and_github  [local]  (source: default)
```

### ksm sync

Re-install bundles from their source registries to pick up changes. For git-based registries, `sync` pulls the latest commits before copying.

```bash
# Sync specific bundles
ksm sync python_dev

# Sync everything
ksm sync --all

# Skip the confirmation prompt
ksm sync --all --yes
```

### ksm rm

Remove an installed bundle and its files.

```bash
# Remove a local bundle
ksm rm python_dev

# Remove a global bundle
ksm rm python_dev -g

# Interactive removal selector
ksm rm --display
```

### ksm add-registry

Register an external git repository as a bundle source. The repo is cloned into `~/.kiro/ksm/cache/` and must contain at least one valid config bundle.

```bash
ksm add-registry https://github.com/org/shared-bundles.git
```

After registering, bundles from that registry appear in `ksm add --display` and can be installed by name.

## Config Bundles

A config bundle is a directory containing one or more of these subdirectories:

```
my-bundle/
├── skills/       # Kiro skill definitions (SKILL.md + scripts)
├── steering/     # Steering markdown files
├── hooks/        # Hook JSON files
└── agents/       # Custom agent definitions
```

A bundle is valid if it contains at least one of these four subdirectories.

### Built-in Bundles

| Bundle | Contents | Description |
|--------|----------|-------------|
| `aws` | skills, steering | AWS-focused skills and steering rules |
| `example_conf_bund` | agents, hooks, skills, steering | Example bundle demonstrating all subdirectory types |
| `git_and_github` | agents, skills, steering | Git branching rules, GitHub PR skill, README writer agent |
| `kiro_skill_authoring` | skills | Skill for authoring Kiro skills |
| `project_foundations` | skills, steering | Project structure and scaffolding guidance |
| `python_dev` | steering | Python development standards |

### Authoring a Bundle

1. Create a directory under `config_bundles/` with your bundle name.
2. Add one or more subdirectories: `skills/`, `steering/`, `hooks/`, `agents/`.
3. Populate them with the appropriate files (e.g. `SKILL.md` for skills, `.md` for steering, `.json` for hooks).
4. The bundle is automatically discovered by `ksm` through the default registry.

## Architecture

```
src/ksm/
├── cli.py              # Argument parsing and command dispatch
├── commands/
│   ├── add.py          # ksm add
│   ├── add_registry.py # ksm add-registry
│   ├── ls.py           # ksm ls
│   ├── rm.py           # ksm rm
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

## Development

```bash
# Create venv and install
python -m venv .venv
source .venv/bin/activate && pip install -e ".[dev]"

# Run tests
source .venv/bin/activate && pytest

# Run tests with coverage
source .venv/bin/activate && pytest --cov=ksm tests/

# Format
source .venv/bin/activate && black src/ tests/

# Lint
source .venv/bin/activate && flake8 src/ tests/

# Type check
source .venv/bin/activate && mypy src/ tests/

# Run thorough property tests (CI mode)
source .venv/bin/activate && HYPOTHESIS_PROFILE=ci pytest
```

### Utility Scripts

| Script | Purpose |
|--------|---------|
| `scripts/install-steering-and-skills.sh` | Copies `docs/steering/` and `docs/skills/` to `~/.kiro/` |
| `scripts/sync-to-kiro-settings.sh` | Merges `settings/allowed_commands.txt` into Kiro's `settings.json` |
| `scripts/update-allowed-commands.sh` | Extracts trusted commands from Kiro's `settings.json` into `settings/allowed_commands.txt` |

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
