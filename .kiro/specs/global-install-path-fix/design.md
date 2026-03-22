# Install Path Fix — Bugfix Design

## Overview

The `ksm` CLI dispatches add, sync, and rm commands with incorrect target paths. Both `target_local` and `target_global` are missing the `.kiro` suffix, causing bundle subdirectories to be written directly into the workspace root or home directory instead of the `.kiro/` configuration directory within them. The fix appends `/ ".kiro"` to both target paths in the three dispatch functions in `src/ksm/cli.py`.

## Glossary

- **Bug_Condition (C)**: Any invocation of `_dispatch_add`, `_dispatch_sync`, or `_dispatch_rm` — all three pass incorrect `target_local` and `target_global` values
- **Property (P)**: The target paths passed to command modules must end with `.kiro` so files land in `<workspace>/.kiro/` (local) or `~/.kiro/` (global)
- **Preservation**: All downstream behavior in installer.py, copier.py, add.py, sync.py, rm.py must remain unchanged — they use whatever `target_dir` is given
- **`_dispatch_add`**: Function in `src/ksm/cli.py` that dispatches the `ksm add` command
- **`_dispatch_sync`**: Function in `src/ksm/cli.py` that dispatches the `ksm sync` command
- **`_dispatch_rm`**: Function in `src/ksm/cli.py` that dispatches the `ksm rm` command
- **`target_dir`**: The resolved path (local or global) used as root for file operations

## Bug Details

### Bug Condition

The bug manifests on every invocation of `_dispatch_add`, `_dispatch_sync`, or `_dispatch_rm`. These functions construct `target_local=Path.cwd()` and `target_global=Path.home()`, missing the `.kiro` path component.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type CLIInvocation (command, scope, cwd, home)
  OUTPUT: boolean

  RETURN input.command IN ['add', 'sync', 'rm', 'remove']
         AND dispatchFunction(input.command) passes
             target_local = Path.cwd()       [missing / ".kiro"]
             target_global = Path.home()     [missing / ".kiro"]
END FUNCTION
```

### Examples

- `ksm add my-bundle -l` in `/projects/app`: files go to `/projects/app/agents/` instead of `/projects/app/.kiro/agents/`
- `ksm add my-bundle -g`: files go to `~/agents/` instead of `~/.kiro/agents/`
- `ksm sync --all -y` with a local bundle: files go to `./skills/` instead of `./.kiro/skills/`
- `ksm sync --all -y` with a global bundle: files go to `~/skills/` instead of `~/.kiro/skills/`
- `ksm rm my-bundle -l -y`: looks for files under `./` instead of `./.kiro/`
- `ksm rm my-bundle -g -y`: looks for files under `~/` instead of `~/.kiro/`

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- The command modules (`add.py`, `sync.py`, `rm.py`) must continue to use `target_dir` as-is without appending `.kiro` themselves
- The installer (`installer.py`) and copier (`copier.py`) must continue to operate unchanged
- Scope selection logic (`-l`/`-g` flags, interactive prompt, defaults) must remain identical
- Manifest file path recording (relative to `target_dir`) must remain identical
- All non-dispatch commands (`list`, `registry`, `info`, `search`, `init`, `completions`) must be unaffected

**Scope:**
All inputs that do NOT flow through `_dispatch_add`, `_dispatch_sync`, or `_dispatch_rm` should be completely unaffected. This includes:
- `ksm list` / `ksm ls`
- `ksm registry` subcommands
- `ksm info`, `ksm search`
- `ksm init`, `ksm completions`
- `ksm add-registry`

## Hypothesized Root Cause

The root cause is confirmed by code inspection:

1. **Missing `.kiro` suffix in `_dispatch_add`**: Passes `target_local=Path.cwd()` and `target_global=Path.home()` to `run_add()`. Should be `Path.cwd() / ".kiro"` and `Path.home() / ".kiro"`.

2. **Missing `.kiro` suffix in `_dispatch_sync`**: Same pattern — passes bare `Path.cwd()` and `Path.home()` to `run_sync()`.

3. **Missing `.kiro` suffix in `_dispatch_rm`**: Same pattern — passes bare `Path.cwd()` and `Path.home()` to `run_rm()`.

All three functions have the identical defect. The downstream modules correctly use whatever `target_dir` they receive, so the fix is isolated to the dispatch layer.

## Correctness Properties

Property 1: Bug Condition - Target Paths Include .kiro Suffix

_For any_ CLI invocation of `add`, `sync`, or `rm` commands, the dispatch functions SHALL pass `target_local=Path.cwd() / ".kiro"` and `target_global=Path.home() / ".kiro"` to the corresponding command runner, ensuring bundle files are installed into the `.kiro/` configuration directory.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

Property 2: Preservation - Non-Dispatch Behavior Unchanged

_For any_ input that does NOT flow through `_dispatch_add`, `_dispatch_sync`, or `_dispatch_rm` (i.e. list, registry, info, search, init, completions commands), the fixed code SHALL produce exactly the same behavior as the original code. Additionally, the command modules, installer, and copier SHALL continue to use `target_dir` as-is without modification.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

**File**: `src/ksm/cli.py`

**Functions**: `_dispatch_add`, `_dispatch_sync`, `_dispatch_rm`

**Specific Changes**:

1. **`_dispatch_add`**: Change `target_local=Path.cwd()` to `target_local=Path.cwd() / ".kiro"` and `target_global=Path.home()` to `target_global=Path.home() / ".kiro"`

2. **`_dispatch_sync`**: Change `target_local=Path.cwd()` to `target_local=Path.cwd() / ".kiro"` and `target_global=Path.home()` to `target_global=Path.home() / ".kiro"`

3. **`_dispatch_rm`**: Change `target_local=Path.cwd()` to `target_local=Path.cwd() / ".kiro"` and `target_global=Path.home()` to `target_global=Path.home() / ".kiro"`

No other files require changes.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm the root cause by inspecting the actual values passed to command runners.

**Test Plan**: Write tests that mock `Path.cwd()` and `Path.home()`, invoke each dispatch function, and capture the `target_local` and `target_global` values passed to the command runners. Run on UNFIXED code to observe the missing `.kiro` suffix.

**Test Cases**:
1. **Add Local Path Test**: Call `_dispatch_add` with `-l` flag, assert `target_local` ends with `.kiro` (will fail on unfixed code)
2. **Add Global Path Test**: Call `_dispatch_add` with `-g` flag, assert `target_global` ends with `.kiro` (will fail on unfixed code)
3. **Sync Local Path Test**: Call `_dispatch_sync`, assert `target_local` ends with `.kiro` (will fail on unfixed code)
4. **Sync Global Path Test**: Call `_dispatch_sync`, assert `target_global` ends with `.kiro` (will fail on unfixed code)
5. **Rm Local Path Test**: Call `_dispatch_rm` with `-l` flag, assert `target_local` ends with `.kiro` (will fail on unfixed code)
6. **Rm Global Path Test**: Call `_dispatch_rm` with `-g` flag, assert `target_global` ends with `.kiro` (will fail on unfixed code)

**Expected Counterexamples**:
- `target_local` resolves to `Path.cwd()` without `.kiro` suffix
- `target_global` resolves to `Path.home()` without `.kiro` suffix

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed dispatch functions pass correct target paths.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := dispatch_fixed(input)
  ASSERT result.target_local == Path.cwd() / ".kiro"
  ASSERT result.target_global == Path.home() / ".kiro"
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed code produces the same result as the original.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT dispatch_original(input) == dispatch_fixed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for non-dispatch commands, then write property-based tests capturing that behavior.

**Test Cases**:
1. **List Command Preservation**: Verify `_dispatch_ls` behavior is identical before and after fix
2. **Registry Command Preservation**: Verify `_dispatch_registry` behavior is identical
3. **Info/Search Preservation**: Verify `_dispatch_info` and `_dispatch_search` behavior is identical
4. **Command Module Interface Preservation**: Verify `run_add`, `run_sync`, `run_rm` still receive and use `target_dir` without modification

### Unit Tests

- Test each dispatch function passes correct `target_local` and `target_global` values
- Test that `target_local` is `Path.cwd() / ".kiro"` in all three dispatch functions
- Test that `target_global` is `Path.home() / ".kiro"` in all three dispatch functions
- Test edge case: paths with spaces or special characters still get `.kiro` appended correctly

### Property-Based Tests

- Generate random working directory paths and verify `target_local` always equals `cwd / ".kiro"`
- Generate random home directory paths and verify `target_global` always equals `home / ".kiro"`
- Generate random command inputs for non-dispatch commands and verify behavior is unchanged

### Integration Tests

- Test full add flow with mocked filesystem to verify files land in `.kiro/` subdirectory
- Test full sync flow to verify updated files go to `.kiro/` subdirectory
- Test full rm flow to verify files are removed from `.kiro/` subdirectory
