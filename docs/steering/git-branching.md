---
inclusion: always
---

# Git Branching

## Rules

1. Never commit directly to `main`.
2. The default branch is always called `main`.
3. All work must be done on a separate branch and merged via pull request.
4. Branch names must follow the format: `<type>/<short-description>` where type is one of:
   - `feature/` — new functionality
   - `bugfix/` — fixing a bug
   - `chore/` — maintenance or non-functional changes

## Before Starting Work

- If on `main`, create and switch to a new branch before making any changes.
- If a branch does not match the naming convention, rename it before pushing.
