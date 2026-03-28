# Bugfix Requirements Document

## Introduction

On a fresh install (no `~/.kiro/ksm/registries.json`), running any `ksm` command other than `ksm init` raises a `FileNotFoundError` from `persistence.py`. The root cause is that six dispatch functions in `cli.py` call `load_registry_index(REGISTRIES_FILE)` without passing `default_registry_path`, so the missing-file fallback in `registry.py` re-raises the exception instead of auto-creating the default registry.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN `registries.json` does not exist AND the user runs `ksm add <bundle>` THEN the system raises `FileNotFoundError` from `persistence.py`

1.2 WHEN `registries.json` does not exist AND the user runs `ksm sync` THEN the system raises `FileNotFoundError` from `persistence.py`

1.3 WHEN `registries.json` does not exist AND the user runs `ksm add-registry <url>` THEN the system raises `FileNotFoundError` from `persistence.py`

1.4 WHEN `registries.json` does not exist AND the user runs `ksm registry add <url>` THEN the system raises `FileNotFoundError` from `persistence.py`

1.5 WHEN `registries.json` does not exist AND the user runs `ksm registry list` (or any `ksm registry` subcommand) THEN the system raises `FileNotFoundError` from `persistence.py`

1.6 WHEN `registries.json` does not exist AND the user runs `ksm info <bundle>` THEN the system raises `FileNotFoundError` from `persistence.py`

1.7 WHEN `registries.json` does not exist AND the user runs `ksm search <query>` THEN the system raises `FileNotFoundError` from `persistence.py`

### Expected Behavior (Correct)

2.1 WHEN `registries.json` does not exist AND the user runs `ksm add <bundle>` THEN the system SHALL auto-create `registries.json` with a default registry entry pointing to the built-in `config_bundles/` directory and proceed normally

2.2 WHEN `registries.json` does not exist AND the user runs `ksm sync` THEN the system SHALL auto-create `registries.json` with a default registry entry and proceed normally

2.3 WHEN `registries.json` does not exist AND the user runs `ksm add-registry <url>` THEN the system SHALL auto-create `registries.json` with a default registry entry and proceed normally

2.4 WHEN `registries.json` does not exist AND the user runs `ksm registry add <url>` THEN the system SHALL auto-create `registries.json` with a default registry entry and proceed normally

2.5 WHEN `registries.json` does not exist AND the user runs `ksm registry list` (or any `ksm registry` subcommand) THEN the system SHALL auto-create `registries.json` with a default registry entry and proceed normally

2.6 WHEN `registries.json` does not exist AND the user runs `ksm info <bundle>` THEN the system SHALL auto-create `registries.json` with a default registry entry and proceed normally

2.7 WHEN `registries.json` does not exist AND the user runs `ksm search <query>` THEN the system SHALL auto-create `registries.json` with a default registry entry and proceed normally

### Unchanged Behavior (Regression Prevention)

3.1 WHEN `registries.json` already exists AND the user runs any command THEN the system SHALL CONTINUE TO load the existing registry index without modification

3.2 WHEN `ksm init` is run without `registries.json` THEN the system SHALL CONTINUE TO handle the missing file gracefully (existing try/except behavior)

3.3 WHEN `registries.json` exists with multiple registries THEN the system SHALL CONTINUE TO load all registry entries correctly

3.4 WHEN `registries.json` exists AND a save/load round-trip is performed THEN the system SHALL CONTINUE TO preserve all registry entry data identically
