# Bugfix Requirements Document

## Introduction

Both local-scope and global-scope bundle installations place files in the wrong directory. When using `ksm add`, `ksm sync`, or `ksm rm`, bundle subdirectories (agents, skills, steering, hooks) are copied directly into the bare target directory instead of the `.kiro/` subdirectory within it.

- Local: files appear at `./agents/`, `./skills/`, etc. instead of `./.kiro/agents/`, `./.kiro/skills/`, etc.
- Global: files appear at `~/agents/`, `~/skills/`, etc. instead of `~/.kiro/agents/`, `~/.kiro/skills/`, etc.

The root cause is in `src/ksm/cli.py` where three dispatch functions (`_dispatch_add`, `_dispatch_sync`, `_dispatch_rm`) pass `target_local=Path.cwd()` and `target_global=Path.home()` instead of `target_local=Path.cwd() / ".kiro"` and `target_global=Path.home() / ".kiro"`.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a bundle is installed locally via `ksm add -l` THEN the system copies bundle subdirectories into `./` (e.g. `./agents/`, `./skills/`) instead of `./.kiro/`

1.2 WHEN a bundle is installed globally via `ksm add -g` THEN the system copies bundle subdirectories into `~/` (e.g. `~/agents/`, `~/skills/`) instead of `~/.kiro/`

1.3 WHEN a locally installed bundle is synced via `ksm sync` THEN the system copies updated bundle subdirectories into `./` instead of `./.kiro/`

1.4 WHEN a globally installed bundle is synced via `ksm sync` THEN the system copies updated bundle subdirectories into `~/` instead of `~/.kiro/`

1.5 WHEN a locally installed bundle is removed via `ksm rm -l` THEN the system looks for files to remove under `./` instead of `./.kiro/`

1.6 WHEN a globally installed bundle is removed via `ksm rm -g` THEN the system looks for files to remove under `~/` instead of `~/.kiro/`

### Expected Behavior (Correct)

2.1 WHEN a bundle is installed locally via `ksm add -l` THEN the system SHALL copy bundle subdirectories into `./.kiro/` (e.g. `./.kiro/agents/`, `./.kiro/skills/`, `./.kiro/steering/`, `./.kiro/hooks/`)

2.2 WHEN a bundle is installed globally via `ksm add -g` THEN the system SHALL copy bundle subdirectories into `~/.kiro/` (e.g. `~/.kiro/agents/`, `~/.kiro/skills/`, `~/.kiro/steering/`, `~/.kiro/hooks/`)

2.3 WHEN a locally installed bundle is synced via `ksm sync` THEN the system SHALL copy updated bundle subdirectories into `./.kiro/`

2.4 WHEN a globally installed bundle is synced via `ksm sync` THEN the system SHALL copy updated bundle subdirectories into `~/.kiro/`

2.5 WHEN a locally installed bundle is removed via `ksm rm -l` THEN the system SHALL look for files to remove under `./.kiro/`

2.6 WHEN a globally installed bundle is removed via `ksm rm -g` THEN the system SHALL look for files to remove under `~/.kiro/`

### Unchanged Behavior (Regression Prevention)

3.1 WHEN any non-install/sync/rm command is executed (e.g. `ksm list`, `ksm registry`, `ksm info`, `ksm search`) THEN the system SHALL CONTINUE TO behave identically to the current implementation

3.2 WHEN the installer, copier, or command modules (add.py, sync.py, rm.py) receive a `target_dir` argument THEN they SHALL CONTINUE TO use it as-is without modification — the path correction is solely in the dispatch layer

3.3 WHEN scope selection logic determines local vs global scope THEN the system SHALL CONTINUE TO use the same scope determination logic (flags `-l`/`-g`, interactive prompt, defaults)

3.4 WHEN manifest entries record installed file paths THEN the paths SHALL CONTINUE TO be relative to the target_dir passed to the installer
