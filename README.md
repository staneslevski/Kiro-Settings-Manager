# Kiro Settings Manager (`ksm`)

A CLI tool for managing [Kiro](https://kiro.dev) IDE configuration bundles. Install, sync, and remove curated sets of skills, steering files, hooks, and agents from local or remote registries.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Install a bundle to your workspace
ksm add aws

# Browse available bundles interactively
ksm add --display

# List what's installed
ksm ls

# Update installed bundles from their source
ksm sync --all --yes

# Remove a bundle
ksm rm aws
```

## Installation

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

This registers the `ksm` command on your PATH.

## Concepts

A **bundle** is a named directory containing one or more Kiro configuration subdirectories:

```
my-bundle/
├── skills/       # Kiro skills (SKILL.md files)
├── steering/     # Steering documents (.md files)
├── hooks/        # Agent hooks (.json files)
└── agents/       # Agent definitions (.md files)
```

A **registry** is a directory (local or git repo) containing one or more bundles. `ksm` ships with a built-in default registry at `config_bundles/`.

## Commands

### `ksm add <bundle>`

Install a bundle's configuration files into your `.kiro/` directory.

```bash
# Install to workspace (default)
ksm add aws

# Install globally to ~/.kiro/
ksm add -g aws

# Browse and pick interactively
ksm add --display
```

**Subdirectory filters** let you install only specific types:

```bash
ksm add aws --skills-only
ksm add aws --steering-only --hooks-only
```

**Dot notation** targets a single item within a bundle:

```bash
# Install only the aws-cross-account skill from the aws bundle
ksm add aws.skills.aws-cross-account
```

**Ephemeral registry** installs from a git repo without registering it:

```bash
ksm add my-bundle --from https://github.com/org/configs.git
```

### `ksm ls`

List all installed bundles with their scope and source registry.

```bash
$ ksm ls
aws          local   default
python_dev   global  default
```

### `ksm sync`

Re-copy bundle files from their source registry to pick up upstream changes.

```bash
# Sync specific bundles
ksm sync aws python_dev

# Sync everything
ksm sync --all

# Skip the confirmation prompt
ksm sync --all --yes
```

For git-based registries, `ksm sync` pulls the latest changes before copying.

### `ksm add-registry <git_url>`

Register an external git repository as a bundle source.

```bash
ksm add-registry https://github.com/org/team-kiro-configs.git
```

The repo is cloned to `~/.kiro/ksm/cache/` and its bundles become available to `ksm add`.

### `ksm rm <bundle>`

Remove an installed bundle and clean up its files.

```bash
# Remove from workspace (default)
ksm rm aws

# Remove a global install
ksm rm -g aws

# Browse installed bundles and pick one to remove
ksm rm --display
```

## Built-in Bundles

The default registry (`config_bundles/`) ships with:

| Bundle | Contents | Description |
|--------|----------|-------------|
| `aws` | skills, steering | AWS cross-account skill, IAM and MCP steering |
| `git_and_github` | skills, steering | GitHub PR skill, git branching steering |
| `python_dev` | steering | Python standards and testing conventions |
| `project_foundations` | skills, steering | Project structure, script writing, planning |
| `kiro_skill_authoring` | skills | Skill builder skill |
| `example_conf_bund` | agents, hooks, skills, steering | Example bundle showing all subdirectory types |

## How It Works

`ksm` stores its state in `~/.kiro/ksm/`:

- `registries.json` — tracks registered bundle sources
- `manifest.json` — records what's installed, where, and from which registry

When you run `ksm add aws`, the tool:

1. Searches all registries for a bundle named `aws`
2. Copies its `skills/`, `steering/`, `hooks/`, and `agents/` subdirectories into your target `.kiro/` directory
3. Records the installed files in the manifest

Files are copied byte-for-byte. Identical files are skipped. Missing target directories are created automatically.

## Scope: Local vs Global

| Flag | Target | Use case |
|------|--------|----------|
| `-l` (default) | `<workspace>/.kiro/` | Project-specific configuration |
| `-g` | `~/.kiro/` | Configuration shared across all projects |

## Development

```bash
# Format
source .venv/bin/activate && black src/ tests/

# Lint
source .venv/bin/activate && flake8 src/ tests/

# Type check
source .venv/bin/activate && mypy src/

# Test with coverage
source .venv/bin/activate && pytest --cov=ksm --cov-report=term-missing

# Run thorough property tests (CI mode)
source .venv/bin/activate && HYPOTHESIS_PROFILE=ci pytest
```

## License

MIT
