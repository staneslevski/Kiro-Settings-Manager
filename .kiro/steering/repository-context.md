# Repository Context

## Purpose

This repository contains `ksm` (Kiro Settings Manager), a Python CLI tool for managing Kiro IDE configuration bundles. It lets users install, remove, sync, and organise bundles of skills, steering files, hooks, and agents across workspace (`.kiro/`) and global (`~/.kiro/`) scopes.

## Directory Layout

- `src/ksm/` — Application source code (CLI, commands, core modules)
- `src/ksm/commands/` — Individual CLI command implementations (`add`, `rm`, `ls`, `sync`, etc.)
- `config_bundles/` — Built-in configuration bundles shipped with the tool (the default registry)
- `tests/` — Test suite mirroring `src/ksm/` modules
- `scripts/` — Utility shell scripts for syncing settings and installing legacy docs
- `settings/` — Kiro allowed-commands list (`allowed_commands.txt`)
- `docs/` — Project documentation and review notes
- `.kiro/` — Workspace-level Kiro configuration (steering, agents, hooks, skills, specs)

## Key Files

- `pyproject.toml` — Project metadata, dependencies, and all tool configuration
- `src/ksm/cli.py` — Argument parsing and command dispatch (entry point: `ksm`)
- `config_bundles/` — Each subdirectory is a bundle containing any combination of `skills/`, `steering/`, `hooks/`, `agents/`

## Config Bundles

Bundles live in `config_bundles/` and are the default registry for `ksm`. Current bundles:

- `aws` — AWS skills and steering (IAM, MCP availability)
- `cli-tools` — CLI engineering agent
- `example_conf_bund` — Example bundle demonstrating all subdirectory types
- `git_and_github` — Git branching steering, GitHub PR skill, git/readme agents
- `kiro_power_usage` — Task builder agent, skill-creating skill
- `project_foundations` — Project structure/script-writing skills, planning/process steering
- `python_dev` — Python and testing standards steering, hypothesis/argparse agents
- `ux-design` — UX designer agent

## Default Behavior

- New business logic goes in `src/ksm/`
- New CLI commands go in `src/ksm/commands/`
- New config bundles go in `config_bundles/<bundle-name>/`
- Tests go in `tests/` with filenames matching `test_<module>.py`

## Writing Steering, Skills, Hooks, or Agents

DO NOT write steering files, skills, hooks, or agents into `.kiro/` unless the user explicitly asks for a workspace-level override. The `.kiro/` directory is for this repo's own local config — it is not the authoring location for distributable content.

This repo's purpose is to manage config bundles that users install elsewhere. All distributable content belongs in `config_bundles/`.

When asked to create or update a steering file, skill, hook, or agent:

1. Ask the user which config bundle it should belong to (e.g. `python_dev`, `aws`, `git_and_github`, or a new bundle).
2. Write the file into `config_bundles/<bundle-name>/<type>/` where `<type>` is one of `steering/`, `skills/`, `hooks/`, `agents/`.
3. Only write into `.kiro/` if the user explicitly says "workspace-level", "local", or "just for this repo".

## Scripts

- `scripts/install-steering-and-skills.sh` — Copies `docs/steering/` and `docs/skills/` to `~/.kiro/` (legacy)
- `scripts/sync-to-kiro-settings.sh` — Merges `settings/allowed_commands.txt` into Kiro's `settings.json`
- `scripts/update-allowed-commands.sh` — Extracts trusted commands from Kiro's `settings.json` into `settings/allowed_commands.txt`
