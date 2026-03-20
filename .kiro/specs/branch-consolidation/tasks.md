# Tasks: Branch Consolidation

- [x] 1. Safety: Push all branches to origin

    - [x] 1.1 Push unpushed branches

        - [x] 1.1.1 Push `chore/readme` to origin

        - [x] 1.1.2 Push `feature/registry-validation-and-display` to origin

        - [x] 1.1.3 Push `feature/output-quality-phase6` to origin

    - [x] 1.2 Verify all branches exist on origin

        - [x] 1.2.1 Run `git branch -r` and confirm all 5 branches are listed

- [x] 2. Merge branches into main

    - [x] 2.1 Merge `chore/readme`

        - [x] 2.1.1 Checkout `main` and pull latest

        - [x] 2.1.2 Merge `chore/readme` into `main` (expect no conflicts)

    - [x] 2.2 Merge `feature/registry-validation-and-display`

        - [x] 2.2.1 Merge `feature/registry-validation-and-display` into `main`

        - [x] 2.2.2 Resolve any conflicts in `add.py` if present

    - [x] 2.3 Merge `bugfix/selector-raw-mode-alignment`

        - [x] 2.3.1 Merge `bugfix/selector-raw-mode-alignment` into `main`

        - [x] 2.3.2 Resolve conflicts — prefer selector-raw-mode versions for files not touched by output-quality

    - [x] 2.4 Merge `feature/output-quality-phase6`

        - [x] 2.4.1 Merge `feature/output-quality-phase6` into `main`

        - [x] 2.4.2 Resolve conflicts — prefer output-quality-phase6 versions (latest iteration)

        - [x] 2.4.3 Verify merge commit contains all expected files

- [x] 3. Post-merge validation

    - [x] 3.1 Verify code integrity

        - [x] 3.1.1 Run `git log --oneline -20` on main to confirm all commits are present

        - [x] 3.1.2 Verify key files exist: cli.py, selector.py, color.py, errors.py, installer.py, copier.py, remover.py

        - [x] 3.1.3 Run tests if test suite is functional (`source .venv/bin/activate && pytest tests/`)

    - [x] 3.2 Handle stashes

        - [x] 3.2.1 Inspect `stash@{0}` (selector-raw-mode WIP) — check if content is already merged

        - [x] 3.2.2 Inspect `stash@{1}` (registry-validation WIP) — check if content is already merged

        - [x] 3.2.3 Drop stashes if fully covered, or apply on a new branch if unique work exists

- [x] 4. Cleanup and publish

    - [x] 4.1 Push and tidy

        - [x] 4.1.1 Push `main` to origin

        - [x] 4.1.2 Delete local branch `feature/config-bundles` (no unique commits)

        - [x] 4.1.3 Confirm all work is on `main` by comparing file counts against each branch
