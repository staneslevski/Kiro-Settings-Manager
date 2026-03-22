---
name: project-structure
description: >
  Guides the agent when scaffolding or restructuring a software project.
  Use when the user asks to create a new project, initialise a repository,
  set up a directory layout, or add standard root-level files like README,
  .gitignore, or LICENSE. Do not use for code review or refactoring within
  existing files.
metadata:
  author: user
  version: 1.0.0
  tags: [project, structure, scaffolding, gitignore, layout]
---

## Purpose

- Ensure every new project starts with a consistent, well-organised directory layout.
- Provide standard root-level files and sensible defaults.
- Apply structural best practices that keep projects maintainable as they grow.

## Required Top-Level Directories

When creating a new project, always include:

- `scripts/` — Automation, build, and utility scripts
- `src/` — Application source code
- `docs/` — Documentation and reference material

## Required Root-Level Files

- `README.md` — Project overview, setup instructions, and usage guide
- `.gitignore` — Files and directories excluded from version control
- `LICENSE` — The licence under which the project is distributed
- `CONTRIBUTING.md` — Guidelines for contributing (if the project accepts contributions)

## Additional Top-Level Directories

Add only when the project needs them:

- `tests/` — All test code, mirroring the structure of `src/`
- `config/` — Configuration files (environment configs, CI/CD, linting rules)
- `infra/` — Infrastructure-as-code templates

Do not create empty placeholder folders.

## Principles

1. Separation of concerns — Each directory and file should have a single, clear responsibility. Do not mix business logic, configuration, and infrastructure in the same location.
2. Scalability — Structure the project so new features can be added without reorganising existing directories. Prefer grouping by feature over grouping by file type as the project grows.
3. Intuitiveness — A new team member should be able to navigate the project without a guide. Use conventional, widely-recognised directory names.
4. Reusability — Extract shared logic into common modules rather than duplicating code across features.
5. Ease of change — Keep coupling between directories low so that changes in one area have minimal impact on others.

## Source Code Organisation (`src/`)

- Keep directory nesting to a maximum of 3–4 levels deep.
- Group related code together: place a feature's logic, models, and utilities in the same subtree.
- Separate layers clearly (e.g. controllers, services, models) when using a layered architecture.
- Avoid catch-all directories like `utils/` or `helpers/` growing unbounded — split them by domain when they get large.

## Test Directory Organisation (`tests/`)

- Mirror the `src/` directory structure so each source module has a corresponding test module.
- Keep test fixtures and shared test utilities in a `tests/conftest` or `tests/fixtures/` directory.
- Name test files to clearly indicate what they cover (e.g. `test_user_service.py`).

## `.gitignore`

Every project must include a `.gitignore` file at the repository root. At a minimum it should contain these standard patterns:

```
# OS files
.DS_Store
Thumbs.db

# Editor / IDE files
.idea/
.vscode/
*.swp
*.swo

# Environment and secrets
.env
.env.*

# Dependencies
node_modules/
vendor/
__pycache__/
*.pyc

# Build output
dist/
build/
out/
*.egg-info/

# Logs
*.log

# Coverage and test artifacts
coverage/
.coverage
htmlcov/
.pytest_cache/
```

Add language- or framework-specific patterns as needed, but always start from this baseline.
