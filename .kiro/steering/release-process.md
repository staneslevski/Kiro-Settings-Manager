---
inclusion: manual
---

# Release Process

This document describes the end-to-end process for releasing a new version of `kiro-settings-manager` to PyPI.

## Prerequisites

- Push access to `origin` (`staneslevski/Kiro-Settings-Manager`)
- A PyPI account with an API token configured in `~/.pypirc`
- Dev dependencies installed: `source .venv/bin/activate && pip install -e ".[dev]"`

## 1. Work on a Leaf Branch

All work happens on a branch off `main`. Never commit directly to `main`.

```bash
git pull origin main
git checkout -b <type>/<short-description>   # feature/, bugfix/, or chore/
```

Commit your changes in small, logical increments. Before pushing, ensure:

- All tests pass: `source .venv/bin/activate && pytest tests/`
- Linting is clean: `source .venv/bin/activate && black src/ tests/ && flake8 src/ tests/ && mypy src/`
- Coverage is ≥95%: `source .venv/bin/activate && pytest --cov=ksm tests/`

## 2. Create a Pull Request

Push the branch and open a PR against `main`:

```bash
git push origin <type>/<short-description>
```

Open the PR on GitHub at https://github.com/staneslevski/Kiro-Settings-Manager/pulls. The PR must be submitted for user review before merging. Do not self-merge without approval.

## 3. Bump the Version

After the PR is merged, bump the `version` field in `pyproject.toml` on a new branch:

```bash
git checkout main
git pull origin main
git checkout -b chore/bump-version-to-<new-version>
```

Edit `pyproject.toml` and update the `version` value under `[project]`.

### Versioning Scheme (SemVer)

- Major (`X.0.0`) — breaking changes or backwards-incompatible API changes
- Minor (`0.X.0`) — new features, backwards-compatible
- Patch (`0.0.X`) — bug fixes, no new features

If it is unclear whether the release is major, minor, or patch, ask the user before proceeding.

Commit, push, and merge this version bump via a PR:

```bash
git add pyproject.toml
git commit -m "chore: bump version to <new-version>"
git push origin chore/bump-version-to-<new-version>
```

Open and merge the version-bump PR.

## 4. Sync Main Locally

After the version bump PR is merged, sync your local `main`:

```bash
git checkout main
git pull origin main
```

Verify the version is correct:

```bash
source .venv/bin/activate && python -c "import importlib.metadata; print(importlib.metadata.version('kiro-settings-manager'))"
```

If the printed version does not match, reinstall: `source .venv/bin/activate && pip install -e ".[dev]"`

## 5. Create a GitHub Release

Tag the release and push the tag:

```bash
git tag v<new-version>
git push origin v<new-version>
```

Then create a release on GitHub:

1. Go to https://github.com/staneslevski/Kiro-Settings-Manager/releases/new
2. Select the tag `v<new-version>`
3. Set the release title to `v<new-version>`
4. Write release notes summarising the changes (or use "Generate release notes")
5. Publish the release

## 6. Publish to PyPI

Use the existing publish script to build and upload:

```bash
./scripts/publish-to-pypi.sh
```

This script cleans previous builds, runs `python -m build`, and uploads via `twine upload`.

To test on TestPyPI first:

```bash
./scripts/publish-to-pypi.sh --test
```

Verify the published package:

```bash
pip install --upgrade kiro-settings-manager
ksm --help
```

## Quick Reference

| Step | Command / Action |
|------|-----------------|
| Branch off main | `git checkout -b <type>/<desc>` |
| Run tests | `source .venv/bin/activate && pytest --cov=ksm tests/` |
| Push and open PR | `git push origin <branch>` → open PR on GitHub |
| Merge PR | Reviewer approves → merge on GitHub |
| Bump version | Edit `pyproject.toml` version → PR → merge |
| Sync main | `git checkout main && git pull origin main` |
| Tag release | `git tag v<ver> && git push origin v<ver>` |
| GitHub release | Create release on GitHub for the tag |
| Publish to PyPI | `./scripts/publish-to-pypi.sh` |
