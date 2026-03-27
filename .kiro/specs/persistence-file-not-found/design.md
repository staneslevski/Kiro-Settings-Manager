# Persistence File-Not-Found Bugfix Design

## Overview

On a fresh install (no `~/.kiro/ksm/registries.json`), six dispatch functions in `cli.py` call `load_registry_index(REGISTRIES_FILE)` without passing `default_registry_path`. This causes `registry.py` to re-raise `FileNotFoundError` instead of auto-creating the default registry. The fix passes `default_registry_path` to all six calls, using the same `config_bundles/` path resolution pattern.

## Glossary

- **Bug_Condition (C)**: `registries.json` does not exist AND a dispatch function calls `load_registry_index` without `default_registry_path`
- **Property (P)**: When `registries.json` is missing, `load_registry_index` auto-creates it with a default registry entry pointing to `config_bundles/`
- **Preservation**: When `registries.json` already exists, it loads unchanged; `_dispatch_init`'s try/except behavior remains intact
- **`load_registry_index`**: Function in `src/ksm/registry.py` that loads the registry index from JSON, optionally creating a default on first run
- **`REGISTRIES_FILE`**: Constant `~/.kiro/ksm/registries.json` defined in `src/ksm/persistence.py`
- **`default_registry_path`**: Optional `Path` parameter pointing to `config_bundles/` — when provided, enables auto-creation fallback

## Bug Details

### Bug Condition

The bug manifests when `registries.json` does not exist and any of six dispatch functions (`_dispatch_add`, `_dispatch_sync`, `_dispatch_add_registry`, `_dispatch_registry`, `_dispatch_info`, `_dispatch_search`) calls `load_registry_index(REGISTRIES_FILE)` without `default_registry_path`. The function catches `FileNotFoundError`, sees `default_registry_path is None`, and re-raises.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type {command: str, registries_file_exists: bool}
  OUTPUT: boolean

  RETURN NOT input.registries_file_exists
         AND input.command IN ['add', 'sync', 'add-registry',
                               'registry', 'info', 'search']
END FUNCTION
```

### Examples

- `ksm add python_dev` on fresh install → `FileNotFoundError` raised (expected: auto-create registries.json, proceed with add)
- `ksm sync` on fresh install → `FileNotFoundError` raised (expected: auto-create registries.json, proceed with sync)
- `ksm search python` on fresh install → `FileNotFoundError` raised (expected: auto-create registries.json, return search results)
- `ksm registry list` on fresh install → `FileNotFoundError` raised (expected: auto-create registries.json, list default registry)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- When `registries.json` already exists, all commands load it without modification
- `_dispatch_init` continues to catch `FileNotFoundError` and pass `registry_index=None` (its own fallback logic)
- `_dispatch_ls`, `_dispatch_rm`, `_dispatch_completions` are unaffected (they don't call `load_registry_index`)
- Save/load round-trips preserve all registry entry data identically
- Multiple registries in an existing file load correctly

**Scope:**
All inputs where `registries.json` already exists are completely unaffected by this fix. The only changed behavior is for the six dispatch functions when the file is missing.

## Hypothesized Root Cause

Based on code analysis, the root cause is confirmed (not hypothesized):

1. **Missing `default_registry_path` argument**: Six dispatch functions in `cli.py` call `load_registry_index(REGISTRIES_FILE)` with only one argument. The `default_registry_path` parameter defaults to `None`.

2. **Conditional re-raise in `load_registry_index`**: In `registry.py` lines 67-69, when `FileNotFoundError` is caught and `default_registry_path is None`, the exception is re-raised. This is correct behavior — the function needs a path to create the default registry.

3. **No runtime resolution of `config_bundles/`**: The project has no constant or utility that resolves the `config_bundles/` directory path at runtime. The fix needs to compute this path (e.g., `Path(__file__).resolve().parent.parent.parent / "config_bundles"` from `cli.py`, or define a constant in `persistence.py`).

## Correctness Properties

Property 1: Bug Condition - Missing registries.json auto-creates default registry

_For any_ dispatch function in {`_dispatch_add`, `_dispatch_sync`, `_dispatch_add_registry`, `_dispatch_registry`, `_dispatch_info`, `_dispatch_search`} called when `registries.json` does not exist, the fixed function SHALL call `load_registry_index` with `default_registry_path` pointing to `config_bundles/`, causing auto-creation of `registries.json` with a default registry entry, and proceed without raising `FileNotFoundError`.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7**

Property 2: Preservation - Existing registries.json loads unchanged

_For any_ call to `load_registry_index` where `registries.json` already exists (isBugCondition returns false), the fixed function SHALL produce the same `RegistryIndex` as the original function, preserving all registry entries, their names, URLs, local paths, and default flags.

**Validates: Requirements 3.1, 3.3, 3.4**

## Fix Implementation

### Changes Required

**File**: `src/ksm/persistence.py`

**Change**: Add a `CONFIG_BUNDLES_DIR` constant that resolves the `config_bundles/` directory path at runtime relative to the project root.

```python
CONFIG_BUNDLES_DIR: Path = Path(__file__).resolve().parent.parent.parent / "config_bundles"
```

**File**: `src/ksm/cli.py`

**Change 1**: Import `CONFIG_BUNDLES_DIR` from `persistence.py`:
```python
from ksm.persistence import (
    ensure_ksm_dir,
    KSM_DIR,
    MANIFEST_FILE,
    REGISTRIES_FILE,
    CONFIG_BUNDLES_DIR,
)
```

**Change 2**: Pass `default_registry_path=CONFIG_BUNDLES_DIR` to all six `load_registry_index` calls:
- `_dispatch_add` (line 322)
- `_dispatch_sync` (line 349)
- `_dispatch_add_registry` (line 367)
- `_dispatch_registry` (line 398)
- `_dispatch_info` (line 464)
- `_dispatch_search` (line 478)

Each call changes from:
```python
registry_index = load_registry_index(REGISTRIES_FILE)
```
to:
```python
registry_index = load_registry_index(
    REGISTRIES_FILE, default_registry_path=CONFIG_BUNDLES_DIR
)
```

**No changes** to `registry.py` — the fallback logic already works correctly when `default_registry_path` is provided.

**No changes** to `_dispatch_init` — it has its own try/except pattern that passes `registry_index=None`.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm the root cause by calling each dispatch function without `registries.json`.

**Test Plan**: Write tests that call `load_registry_index(path)` (without `default_registry_path`) when the file doesn't exist. Run on UNFIXED code to observe `FileNotFoundError`.

**Test Cases**:
1. **Direct call without default_registry_path**: Call `load_registry_index(nonexistent_path)` — expect `FileNotFoundError` (will fail on unfixed code, confirming the bug)
2. **Direct call with default_registry_path**: Call `load_registry_index(nonexistent_path, default_registry_path=config_bundles)` — expect success (confirms the fix mechanism works)

**Expected Counterexamples**:
- `FileNotFoundError` raised when `registries.json` is missing and `default_registry_path` is `None`
- Confirmed cause: missing argument in dispatch functions

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL command IN ['add', 'sync', 'add-registry', 'registry', 'info', 'search']
  WHERE NOT registries_file_exists DO
    result := dispatch_function_fixed(command)
    ASSERT registries_file_now_exists
    ASSERT registries_file_contains_default_entry
    ASSERT no FileNotFoundError raised
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL registry_index WHERE registries_file_exists DO
  ASSERT load_registry_index_fixed(path, default_registry_path)
         = load_registry_index_original(path)
END FOR
```

**Testing Approach**: Property-based testing with Hypothesis is recommended for preservation checking because:
- It generates many random registry configurations to verify round-trip integrity
- It catches edge cases in serialization/deserialization
- It provides strong guarantees that existing behavior is unchanged

**Test Plan**: Observe behavior on UNFIXED code for existing registries.json files, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Existing file preservation**: Verify `load_registry_index` with `default_registry_path` returns identical results when file exists
2. **Round-trip preservation**: Verify save/load round-trip is unchanged by the fix
3. **Multiple registries preservation**: Verify multi-entry registry files load correctly

### Unit Tests

- Test `CONFIG_BUNDLES_DIR` resolves to a valid directory
- Test each dispatch function creates `registries.json` when missing
- Test each dispatch function loads existing `registries.json` unchanged
- Test `_dispatch_init` behavior is unchanged (still catches `FileNotFoundError`)

### Property-Based Tests

- Generate random `RegistryIndex` instances, save to disk, then call `load_registry_index` with `default_registry_path` — verify loaded data matches saved data (preservation)
- Generate random valid/missing file states and verify correct behavior (auto-create vs load)

### Integration Tests

- Test full CLI flow: fresh install → `ksm add` → verify `registries.json` created with default entry
- Test full CLI flow: existing `registries.json` → `ksm add` → verify file unchanged
- Test `ksm init` followed by `ksm add` on fresh install
