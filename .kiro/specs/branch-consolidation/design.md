# Design: Branch Consolidation

## Merge Order Rationale

All branches fork from the same commit (`1500fcd` — current `main` HEAD). The merge order is determined by:
1. Fewest file overlaps with other branches → merge first
2. Foundational work before work that builds on it
3. Most recent / comprehensive changes last (wins conflicts naturally)

## File Overlap Matrix

| Branch pair | Overlapping files |
|---|---|
| `chore/readme` vs any | 0-1 (README.md only) |
| `registry-validation` vs `selector-raw-mode` | 3 (add.py, selector.py, test_selector.py) |
| `registry-validation` vs `output-quality` | 1 (add.py) |
| `selector-raw-mode` vs `output-quality` | 13 files (heavy overlap — cli, color, commands, tests) |

## Merge Order

```
main ← chore/readme ← registry-validation ← selector-raw-mode ← output-quality-phase6
```

1. `chore/readme` — 1 file, zero conflict risk
2. `feature/registry-validation-and-display` — 2 commits, minimal overlap with main
3. `bugfix/selector-raw-mode-alignment` — 4 commits, foundational UX phases 1-5
4. `feature/output-quality-phase6` — 3 commits, latest UX phases 6-8 (wins conflicts)

## Conflict Resolution Strategy

- Steps 1-2: expect no conflicts
- Step 3: possible minor conflicts in `add.py`, `selector.py` from step 2's changes
- Step 4: expect conflicts in ~13 files. Resolution: prefer `output-quality-phase6` versions since they represent the latest iteration of the same UX work

## Stash Handling

Inspect each stash after merging. If the stash contains work already covered by merged commits, drop it. If it contains unique uncommitted work, apply it on a new branch.

## Cleanup

- Delete `feature/config-bundles` (no unique commits)
- Push final `main` to origin
- Optionally delete merged branches from origin after confirming
