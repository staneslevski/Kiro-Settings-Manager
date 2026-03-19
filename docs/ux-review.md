# UX Review: ksm (Kiro Settings Manager) CLI

## Context

ksm is a CLI tool for managing Kiro IDE configuration bundles — collections of steering files, skills, hooks, and agents. It targets developers who use Kiro and want to share, install, and synchronize configuration across projects and machines. The mental model is a package manager (think npm, brew, or apt) for IDE configuration.

This review evaluates the tool against CLI design heuristics, identifies friction points, and provides concrete fixes ranked by severity.

---

## What Works Well

- **Dot notation** (`ksm add bundle.steering.my-file`) is a genuinely good idea. It gives power users surgical control without adding flags. The parsing is clean and the validation is solid.
- **Ephemeral registries** (`--from URL`) are a smart escape hatch. Users can try a bundle without permanently registering a source. The cleanup-on-exit pattern is correct.
- **Manifest tracking** is well-structured. The `installed_at`/`updated_at` timestamps and per-file tracking enable reliable sync and removal.
- **Skip-if-identical** in the copier is a nice touch that prevents unnecessary file churn.
- **Exit codes** are consistently 0/1 across all commands.
- **Errors go to stderr, output to stdout** — this is correct and many CLI tools get it wrong.

---

## Findings

### Critical

#### C1: `rm` has no confirmation prompt for destructive file deletion

`rm` silently deletes files from the user's `.kiro/` directory with zero confirmation. This is a data-loss risk. The `sync` command correctly asks for confirmation before overwriting, but `rm` — which is arguably more destructive — does not.

**Fix:** Add a confirmation prompt to `rm` that lists what will be deleted. Support `--yes` / `-y` to skip it (matching `sync`'s pattern). Example:

```
$ ksm rm my-bundle
This will remove 4 files from .kiro/ (local scope):
  steering/code-review.md
  steering/testing.md
  skills/refactor/SKILL.md
  hooks/pre-commit.json

Continue? [y/n]
```

**File:** `src/ksm/commands/rm.py` — add confirmation logic before calling `remove_bundle()`.

---

#### C2: `rm` gives no feedback after successful removal

`remove_bundle()` returns a `RemovalResult` with `removed_files` and `skipped_files`, but `run_rm()` completely ignores it. The user gets zero output on success. They have no idea what happened.

**Fix:** Print a summary after removal:

```
Removed 'my-bundle' (local): 4 files deleted
```

If files were skipped (already missing), warn:

```
Removed 'my-bundle' (local): 3 files deleted, 1 already missing
```

**File:** `src/ksm/commands/rm.py` lines 38-39 and 55-56 — use the `RemovalResult` return value.

---

#### C3: Interactive selectors have no instructions or header

Both `interactive_select` and `interactive_removal_select` drop the user into a raw-mode terminal with a list of items and zero context. There is no title, no instructions, no hint about controls. A user encountering this for the first time will not know what to do.

**Fix:** Render a header above the list:

```
Select a bundle to install (↑/↓ navigate, Enter select, q quit):

> my-bundle        [installed]
  other-bundle
  third-bundle
```

**File:** `src/ksm/selector.py` — add header lines to `render_add_selector()` and `render_removal_selector()`.

---

### Major

#### M1: Command naming is inconsistent — `add-registry` breaks the pattern

Every other command is a single word (`add`, `ls`, `rm`, `sync`). Then `add-registry` appears as a hyphenated compound. This creates two problems:
1. Users will try `ksm registry add` or `ksm add --registry` first.
2. The command hierarchy is flat when it should be nested.

**Fix:** Introduce a `registry` subcommand group:

```
ksm registry add <url>      # was: ksm add-registry <url>
ksm registry ls              # new: list registered registries
ksm registry rm <name>       # new: unregister a registry
```

This follows the `<noun> <verb>` pattern used by tools like `docker`, `kubectl`, and `gh`. It also opens the door for `registry ls` and `registry rm` which are currently missing (see M5).

---

#### M2: The `--*-only` flags are a poor pattern that doesn't scale

`--skills-only`, `--agents-only`, `--steering-only`, `--hooks-only` — four boolean flags that are semantically a single-choice filter. Problems:
1. Users can combine them (`--skills-only --hooks-only`), which the code silently allows by building a set. The flag names say "only" but the behavior is "include these." The naming lies.
2. Adding a new subdirectory type requires adding a new flag.
3. Four flags clutter `--help` output.

**Fix:** Replace with a single repeatable `--only` flag:

```
ksm add my-bundle --only skills
ksm add my-bundle --only skills --only hooks
```

Or use comma-separated values:

```
ksm add my-bundle --only skills,hooks
```

This is how `docker run --mount`, `pytest -k`, and similar tools handle multi-value filters. It scales to new subdirectory types without CLI changes.

---

#### M3: `ksm ls` output is too sparse to be useful

The current output is a flat, uncolored, ungrouped list:

```
my-bundle  [local ]  (source: default)
other      [global]  (source: my-registry)
```

For a tool managing IDE configuration, users need to answer: "What's installed? Where? What files?" The current output answers the first two weakly and the third not at all.

**Fix:**
1. Group by scope (local, then global) with section headers.
2. Add `--verbose` / `-v` to show installed files.
3. Add `--scope local|global` to filter.
4. Add `--format json` for machine consumption.

Example improved output:

```
Local (.kiro/):
  my-bundle     (source: default)       2 days ago
  other-bundle  (source: my-registry)   5 min ago

Global (~/.kiro/):
  shared-config (source: default)       1 week ago
```

With `-v`:

```
Local (.kiro/):
  my-bundle (source: default) — 2 days ago
    steering/code-review.md
    steering/testing.md
    skills/refactor/SKILL.md
```

**File:** `src/ksm/commands/ls.py` — the entire `run_ls` function needs rework.

---

#### M4: Error messages are not actionable

Current errors tell the user what went wrong but not what to do about it:

| Current | Problem |
|---------|---------|
| `Bundle not found: foo` | Doesn't say where it looked or suggest alternatives |
| `Failed to clone <url>: <raw git stderr>` | Raw git output is noisy and unhelpful |
| `Invalid subdirectory type: bar. Valid types: skills, steering, hooks, agents` | Good — this one is actually fine |

**Fix for BundleNotFoundError:**

```
Error: Bundle 'foo' not found in any registered registry.
  Searched 2 registries: default, my-registry
  Run `ksm registry ls` to see available registries.
  Run `ksm add foo --from <git-url>` to install from a specific source.
```

This requires passing the registry names into the error context.

**Fix for GitError:**

```
Error: Failed to clone repository.
  URL: https://github.com/example/repo.git
  Git said: repository not found
  Check that the URL is correct and you have access.
```

Strip the raw stderr to the meaningful line. Wrap it in context.

**File:** `src/ksm/errors.py` — enrich error classes with context fields. Update `commands/*.py` to format them properly.

---

#### M5: No way to list or remove registries

Users can add registries with `ksm add-registry` but cannot:
- List what registries are registered
- Remove a registry they no longer want
- See what bundles are available in a registry before installing

This is a dead end. Once you add a registry, you're stuck with it unless you manually edit `~/.kiro/ksm/registries.json`.

**Fix:** Add these commands (under the `registry` subcommand group from M1):

```
ksm registry ls                    # list all registries with bundle counts
ksm registry rm <name>             # unregister and optionally clean cache
ksm registry inspect <name>        # show available bundles in a registry
```

---

#### M6: `ksm add` with no arguments and no `--display` gives a bare error

```
$ ksm add
Error: no bundle specified
```

This is a missed opportunity. The user clearly wants to add something but doesn't know what's available.

**Fix:** When `ksm add` is called with no arguments, either:
1. Auto-launch the interactive selector (make `--display` the default when no spec is given), or
2. Print a helpful message:

```
Error: no bundle specified

Usage: ksm add <bundle-name> [--local | --global]

Available bundles:
  my-bundle       (default registry)
  other-bundle    (default registry)

Use `ksm add --display` for interactive selection.
```

Option 1 is better UX. If the user typed `ksm add` with nothing else, they want to browse.

---

### Minor

#### m1: No color anywhere in the output

The entire tool is monochrome. Color is not required, but it significantly aids scannability:
- Green for success messages
- Red for errors
- Yellow for warnings
- Dim/gray for secondary information (timestamps, paths)
- Bold for bundle names in lists

**Fix:** Add a small color utility module. Respect `NO_COLOR` environment variable (https://no-color.org/) and detect non-TTY output to disable color automatically. Never use color as the sole indicator of meaning.

---

#### m2: `--display` is a confusing flag name

`--display` sounds like it controls output formatting ("display mode"), not that it launches an interactive picker. Every other CLI tool calls this `--interactive` or `-i`.

**Fix:** Rename to `--interactive` / `-i`. Keep `--display` as a hidden alias for backward compatibility during a deprecation period.

---

#### m3: No `--dry-run` support on any command

Users cannot preview what `add`, `rm`, or `sync` will do before it happens. This is especially important for `sync --all` which overwrites files across all installed bundles.

**Fix:** Add `--dry-run` to `add`, `rm`, and `sync`. Print what would happen without doing it:

```
$ ksm add my-bundle --dry-run
Would install to .kiro/ (local):
  steering/code-review.md (new)
  steering/testing.md (overwrite)
  skills/refactor/SKILL.md (new)
```

---

#### m4: `ksm sync` confirmation message is vague

Current: `"This will overwrite current configuration files. Continue? [y/n]"`

This doesn't say which bundles or how many files. The user is confirming blind.

**Fix:**

```
Syncing 3 bundles: my-bundle, other-bundle, shared-config
This will overwrite configuration files in .kiro/ and ~/.kiro/.
Continue? [y/n]
```

**File:** `src/ksm/commands/sync.py` — build the message from `entries_to_sync`.

---

#### m5: Interactive selectors don't support search/filter

With more than ~15 bundles, arrow-key navigation becomes tedious. Users expect to type to filter, like fzf, npm's interactive prompts, or VS Code's command palette.

**Fix:** Add type-to-filter. As the user types characters, filter the list to matching items. Backspace removes characters. This is a significant implementation effort but dramatically improves usability at scale.

---

#### m6: No multi-select in interactive mode

Users who want to install 3 bundles must run `ksm add --display` three times. The selector only supports single selection.

**Fix:** Add space-bar to toggle selection, Enter to confirm all selected items. Show checkmarks for selected items:

```
Select bundles to install (↑/↓ navigate, Space toggle, Enter confirm, q quit):

  [✓] my-bundle        [installed]
> [ ] other-bundle
  [ ] third-bundle
```

---

#### m7: `ksm` with no command shows argparse's default help

Running `ksm` alone shows the auto-generated argparse help, which is functional but not welcoming. First-time users deserve a better onboarding moment.

**Fix:** Replace with a curated help screen:

```
ksm — Kiro Settings Manager v0.1.0

Manage configuration bundles for Kiro IDE.

Commands:
  add <bundle>       Install a bundle to your project or globally
  rm <bundle>        Remove an installed bundle
  ls                 List installed bundles
  sync               Update installed bundles from registries
  registry add       Register a new bundle source
  registry ls        List registered sources
  registry rm        Remove a registered source

Quick start:
  ksm add                    Browse and install bundles interactively
  ksm add my-bundle          Install a specific bundle
  ksm ls                     See what's installed

Run `ksm <command> --help` for detailed usage.
```

---

### Suggestions

#### S1: Add a `ksm init` command

New users have no guided entry point. An `init` command could:
1. Create `.kiro/` in the current project if it doesn't exist
2. Optionally launch the interactive selector to pick starter bundles
3. Print a "you're set up" message with next steps

This is how `npm init`, `git init`, and `cargo init` work. It gives users a clear starting point.

---

#### S2: Add a `ksm info <bundle>` command

Users cannot inspect a bundle before installing it. They should be able to see:
- What subdirectories it contains
- How many files
- A description (if the bundle has a README or metadata)
- Which registry it comes from

```
$ ksm info my-bundle
my-bundle (source: default)
  steering/  2 files
  skills/    1 folder (refactor/)
  hooks/     1 file
  agents/    —
```

---

#### S3: Add `ksm search <query>`

Users cannot discover bundles by keyword. If registries grow, discoverability becomes critical. A search command that fuzzy-matches bundle names (and eventually descriptions) would help.

---

#### S4: Support `ksm add bundle@version` for versioned bundles

Currently there's no versioning concept. As registries mature, users will want to pin specific versions. Consider git tags or branches as version identifiers:

```
ksm add my-bundle@v2.1
ksm add my-bundle@main
```

This is forward-looking but worth designing the data model for now.

---

#### S5: Add shell completions

Generate completions for bash, zsh, and fish. This dramatically improves discoverability. argparse can be extended with `argcomplete` or completions can be generated statically.

---

#### S6: Show what changed after `add` and `sync`

Currently `add` produces no output on success. After installing a bundle, print:

```
Installed 'my-bundle' (local): 4 files
  + steering/code-review.md (new)
  + steering/testing.md (new)
  ~ skills/refactor/SKILL.md (updated)
  = hooks/pre-commit.json (unchanged)
```

The copier already tracks what was copied vs skipped — surface that information.

---

## Summary of Recommended Priority

| ID | Severity | Effort | Summary |
|----|----------|--------|---------|
| C1 | Critical | Low | Add confirmation prompt to `rm` |
| C2 | Critical | Low | Print feedback after `rm` succeeds |
| C3 | Critical | Low | Add header/instructions to interactive selectors |
| M1 | Major | Medium | Restructure `add-registry` → `registry add/ls/rm` |
| M2 | Major | Low | Replace `--*-only` flags with `--only <type>` |
| M3 | Major | Medium | Improve `ls` output with grouping, verbosity, filtering |
| M4 | Major | Medium | Make error messages actionable with context and suggestions |
| M5 | Major | Medium | Add registry list/remove/inspect commands |
| M6 | Major | Low | Auto-launch interactive selector when `ksm add` has no args |
| m1 | Minor | Medium | Add color support with NO_COLOR respect |
| m2 | Minor | Low | Rename `--display` to `--interactive` / `-i` |
| m3 | Minor | Medium | Add `--dry-run` to add/rm/sync |
| m4 | Minor | Low | Make sync confirmation message specific |
| m5 | Minor | High | Add type-to-filter in interactive selectors |
| m6 | Minor | High | Add multi-select to interactive selectors |
| m7 | Minor | Low | Curate the root `ksm` help output |
| S1 | Suggestion | Medium | Add `ksm init` command |
| S2 | Suggestion | Low | Add `ksm info <bundle>` command |
| S3 | Suggestion | Medium | Add `ksm search <query>` |
| S4 | Suggestion | High | Design versioning support |
| S5 | Suggestion | Medium | Add shell completions |
| S6 | Suggestion | Low | Show file-level diff after add/sync |

## Open Questions

1. **Should `--display` become the default for `ksm add` with no arguments?** I recommend yes, but this changes the non-interactive contract. Scripts that call `ksm add` with no args currently get an error (exit 1), which is correct for automation. Auto-launching interactive mode would break piped usage. Resolution: auto-launch only when stdin is a TTY.

2. **Should registries support metadata (descriptions, tags)?** If bundles are going to be discoverable via search, they need metadata beyond just a directory name. Consider a `bundle.toml` or `bundle.json` manifest inside each bundle directory.

3. **What happens when two registries contain a bundle with the same name?** Currently `resolve_bundle` returns the first match. This is undocumented and will surprise users. Document the precedence order, or error with "bundle 'x' found in multiple registries — specify with `--from`."

4. **Is the local/global scope model the right abstraction?** "Local" means `.kiro/` in the current working directory. If a user runs `ksm add` from a different directory, they get a different local scope. This is correct for project-level config but could confuse users who expect "local" to mean "my machine." Consider renaming to `--project` / `--global` for clarity.

5. **Windows support.** The interactive selector uses `tty`/`termios` which are Unix-only. The tool will crash on Windows. If Windows is a target platform, the selector needs a cross-platform input library (e.g., `prompt_toolkit`, `blessed`, or `msvcrt` fallback).
