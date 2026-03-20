# Requirements: Branch Consolidation

## Problem

Multiple local branches contain work that is not merged to `main` and not all are pushed to `origin`. Code and features appear missing because commits are scattered across branches.

## Goal

Consolidate all branch work into `main` with minimal merge conflicts, preserving all commits and code.

## Current Branch State (as of analysis)

| Branch | Commits ahead | On origin? | Key content |
|---|---|---|---|
| `feature/config-bundles` | 0 | No | Already in main — no unique work |
| `chore/readme` | 1 | No | README.md only |
| `feature/registry-validation-and-display` | 2 | No | Registry validation, config bundles, readme-writer agent |
| `bugfix/selector-raw-mode-alignment` | 4 | Yes | UX phases 1-5, custom agents, new ksm modules |
| `feature/output-quality-phase6` | 3 | No | UX phases 6-8, new commands, installer, copier, remover |

## Stashes

- `stash@{0}` — WIP on `selector-raw-mode-alignment`
- `stash@{1}` — WIP on `registry-validation-and-display`

## Requirements

1. All branches must be pushed to `origin` before any merging begins (safety net)
2. All unique commits must be preserved in `main`
3. Merge order must minimise conflict surface area
4. After completion, `main` must contain all code from all branches
5. Stashes must be inspected and applied if they contain useful work
6. Redundant branches (`feature/config-bundles`) must be cleaned up
7. Final state: all branches merged, `main` pushed to origin
