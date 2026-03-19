# KSM CLI Engineering Review

Reviewer: CLI Engineer
Scope: Full codebase review of `ksm` (Kiro Settings Manager) v0.1.0
Method: Source audit, live `--help` inspection, error path testing, convention analysis

---

## Severity Definitions

- CRITICAL — Blocks usage or violates a fundamental CLI contract
- MAJOR — Significant friction, convention violation, or accessibility failure
- MINOR — Polish, consistency, or missing convenience
- GOOD — Worth calling out as done well

---

## 1. What Works Well

GOOD: Exit code discipline. Commands return 0/1/2 consistently. `main()` raises `SystemExit` with the code. argparse defaults to 2 for usage errors. This is correct.

GOOD: Errors to stderr. Every `print(..., file=sys.stderr)` in the codebase writes errors and warnings to stderr. stdout stays clean for data. This is the right call.

GOOD: Lazy imports. Dispatch functions import command modules on demand. This keeps `ksm --help` fast. Users notice startup latency; this avoids it.

GOOD: Skip-if-identical in copier.py. Byte-for-byte comparison before copying is a smart optimisation that prevents unnecessary file writes during sync.

GOOD: Manifest-based tracking. Recording installed files with timestamps and scope enables reliable removal and sync. This is the right data model.

GOOD: `--yes` flag on sync. Destructive operations prompt for confirmation and provide a scriptable bypass. This follows the forgiveness principle correctly.

GOOD: Dot notation design. `bundle.subdirectory.item` is a clean, composable addressing scheme. The parser and validator are well-separated.

---

## 2. Critical Issues

### C1: No `--help` examples section

Severity: CRITICAL
File: `src/ksm/cli.py`, `_build_parser()`

Every `--help` output is bare-bones argparse defaults. No examples, no environment variable docs, no "Use ksm <command> --help" footer. The top-level help is:

```
usage: ksm [-h] [--version] {add,ls,sync,add-registry,rm} ...

Kiro Settings Manager — manage configuration bundles

positional arguments:
  {add,ls,sync,add-registry,rm}
    add                 Install a bundle
    ls                  List installed bundles
    ...
```

This fails discoverability. A user who types `ksm add --help` gets flag names but no idea how to actually use them. The `--from` flag shows `FROM_URL` as its metavar — that's argparse's auto-generated placeholder, not a helpful description.

Fix: Add an `epilog` to every subparser with 2-3 concrete examples. Use `formatter_class=argparse.RawDescriptionHelpFormatter` so the formatting is preserved. Add a footer to the top-level parser: `Use "ksm <command> --help" for more information about a command.`

Example for `add`:
```python
add_p = sub.add_parser(
    "add",
    help="Install a bundle",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=textwrap.dedent("""\
        examples:
          ksm add my-bundle
          ksm add my-bundle --skills-only
          ksm add my-bundle.steering.code-review
          ksm add my-bundle --from https://github.com/org/repo.git
          ksm add --display
    """),
)
```

### C2: No typo suggestion for unknown commands

Severity: CRITICAL
File: `src/ksm/cli.py`

When a user types `ksm delpoy`, they get:
```
ksm: error: argument command: invalid choice: 'delpoy' (choose from add, ls, sync, add-registry, rm)
```

This is argparse's default. It lists valid choices but does not suggest the closest match. For a tool with 5 commands, Levenshtein-based suggestion is trivial and high-value.

Fix: Override `argparse.ArgumentParser.error()` or use a custom subparser action. Compute edit distance against known commands and suggest the closest match:
```
Error: Unknown command "delpoy"
  Did you mean "add"?
  Run "ksm --help" to see all available commands.
```

### C3: Interactive selector writes to stdout, not stderr

Severity: CRITICAL
File: `src/ksm/selector.py`, lines with `sys.stdout.write`

The interactive selector renders its UI to stdout using ANSI escape sequences (`\033[?25l`, `\033[H`, `\033[J`). This means if someone pipes `ksm add --display`, the escape sequences corrupt the pipe. Interactive UI must go to stderr.

Fix: Write all selector rendering to `sys.stderr`. The final selected value (the bundle name) is the only thing that should touch stdout — and even that is handled by the caller, not the selector.

### C4: Interactive selector is Unix-only with no fallback

Severity: CRITICAL
File: `src/ksm/selector.py`

`tty` and `termios` are Unix-only modules. On Windows, `import termios` raises `ModuleNotFoundError`. There is no try/except, no fallback, no platform check. The `--display` flag silently becomes a crash on Windows.

Fix: At minimum, catch the import error and fall back to a numbered-list prompt:
```
Available bundles:
  1. my-bundle
  2. other-bundle [installed]
Select a bundle [1-2]:
```

This works everywhere, is screen-reader compatible, and requires no terminal manipulation.

### C5: `-l` and `-g` flags are not mutually exclusive

Severity: CRITICAL
File: `src/ksm/cli.py`, `_build_parser()`

Running `ksm add -l -g mybundle` does not error. Both flags are accepted. The code silently picks "global" because it checks `global_` first. This violates least surprise — the user thinks they're installing locally because they also passed `-l`.

Fix: Use argparse's `add_mutually_exclusive_group()`:
```python
scope_group = add_p.add_mutually_exclusive_group()
scope_group.add_argument("-l", "--local", ...)
scope_group.add_argument("-g", "--global", ...)
```

This gives a clear error: `error: argument -g/--global: not allowed with argument -l/--local`

---

## 3. Major Issues

### M1: `ls` output is not machine-readable

Severity: MAJOR
File: `src/ksm/commands/ls.py`

`ksm ls` outputs:
```
git_and_github        [local]  (source: default)
kiro_skill_authoring  [local]  (source: default)
```

This cannot be reliably parsed. The brackets, parentheses, and variable padding make `grep`, `awk`, and `cut` fragile. There is no `--format json` or `--format csv` option.

Fix: Add `--format` flag with `text` (default), `json`, and optionally `csv`. JSON output should be:
```json
[
  {"name": "git_and_github", "scope": "local", "source": "default"},
  ...
]
```

### M2: `rm` has no confirmation prompt

Severity: MAJOR
File: `src/ksm/commands/rm.py`

`ksm rm mybundle` deletes files immediately with no confirmation. `sync` prompts before overwriting, but `rm` — the more destructive operation — does not. This is inconsistent and dangerous.

Fix: Add a confirmation prompt to `rm` (matching sync's pattern) and a `--yes`/`-y` flag to bypass it:
```
This will remove bundle 'mybundle' and delete 3 files. Continue? [y/n]
```

### M3: No `--verbose` or `--quiet` global flags

Severity: MAJOR
File: `src/ksm/cli.py`

There are no global verbosity controls. Operations like `add` and `sync` produce no stdout output on success — which is correct for the default case — but there's no way to get diagnostic detail when something goes wrong, and no way to suppress warnings in scripts.

Fix: Add `--verbose`/`-v` and `--quiet`/`-q` to the top-level parser. `--verbose` enables detailed progress output to stderr. `--quiet` suppresses warnings and informational messages. These are the two most universally expected global flags after `--help` and `--version`.

### M4: `add-registry` command naming breaks the verb-noun pattern

Severity: MAJOR
File: `src/ksm/cli.py`

The command tree mixes patterns:
- `add` (verb) — adds a bundle
- `rm` (verb) — removes a bundle
- `ls` (verb) — lists bundles
- `sync` (verb) — syncs bundles
- `add-registry` (verb-noun) — adds a registry

This is inconsistent. `add-registry` looks like it should be `registry add` (noun-verb with subcommand grouping). But more importantly, there's no `rm-registry` or `ls-registry` — so registries are a second-class citizen with an orphaned command.

Fix (short-term): Rename to `registry add` and add `registry ls` and `registry rm` as a subcommand group. This follows the `<tool> <noun> <verb>` pattern used by `docker`, `kubectl`, and `aws`.

Fix (if keeping flat): At minimum add `rm-registry` and `ls-registry` for symmetry.

### M5: No `NO_COLOR` or `TERM=dumb` handling

Severity: MAJOR
File: `src/ksm/selector.py`

The selector emits ANSI escape sequences unconditionally. It does not check:
- `NO_COLOR` environment variable
- `TERM=dumb`
- Whether stdout/stderr is a TTY (`os.isatty()`)

A screen reader will read every escape code character-by-character. A `TERM=dumb` terminal will display garbage.

Fix: Check `os.isatty(sys.stdin.fileno())` before entering raw mode. If not a TTY, fall back to the numbered-list prompt. Respect `NO_COLOR` and `TERM=dumb` by disabling cursor manipulation.

### M6: Selector clears the entire screen

Severity: MAJOR
File: `src/ksm/selector.py`

`\033[H` moves cursor to home position and `\033[J` clears from cursor to end of screen. This wipes the user's terminal history. Tools like `fzf` and `gum` use alternate screen buffers (`\033[?1049h` / `\033[?1049l`) to preserve history, or render inline without clearing.

Fix: Use the alternate screen buffer, or render only the lines needed and clear only those lines on each update.

### M7: `sync` confirmation prompt reads from stdin unconditionally

Severity: MAJOR
File: `src/ksm/commands/sync.py`

```python
response = input("This will overwrite current configuration files. Continue? [y/n] ")
```

`input()` reads from stdin. If stdin is piped (e.g., `echo "data" | ksm sync --all`), this consumes the piped data as the confirmation response. The `EOFError` catch helps, but the prompt itself should not appear when stdin is not a TTY.

Fix: Check `os.isatty(sys.stdin.fileno())` before prompting. If not interactive and `--yes` was not passed, fail with a clear error:
```
Error: confirmation required but stdin is not a terminal
  Use --yes to skip confirmation in non-interactive mode
```

### M8: `--*-only` flags should be a single `--only` flag

Severity: MAJOR
File: `src/ksm/cli.py`

Four separate boolean flags (`--skills-only`, `--agents-only`, `--steering-only`, `--hooks-only`) is verbose and doesn't scale. If a new subdirectory type is added, a new flag must be added.

Fix: Replace with a single repeatable flag:
```
ksm add mybundle --only skills --only hooks
```

Or use comma-separated values:
```
ksm add mybundle --only skills,hooks
```

This is how `--exclude`, `--include`, and `--filter` work in most CLI tools.

---

## 4. Minor Issues

### m1: No shell completion support

Severity: MINOR

No `--completion` flag, no completion scripts, no integration with `argcomplete` or similar. Shell completion is the single highest-ROI discoverability feature for CLI tools.

Fix: Add `argcomplete` as an optional dependency. It integrates with argparse with minimal code and supports bash, zsh, and fish.

### m2: `ls` prints "No bundles currently installed." to stdout

Severity: MINOR
File: `src/ksm/commands/ls.py`

This informational message goes to stdout. If someone runs `ksm ls | wc -l`, they get `1` instead of `0`. Informational messages about empty state should go to stderr.

Fix: `print("No bundles currently installed.", file=sys.stderr)`

### m3: `add-registry` prints success to stdout

Severity: MINOR
File: `src/ksm/commands/add_registry.py`

`print(f"Registered registry '{name}' from {git_url}")` goes to stdout. Status messages are diagnostics and belong on stderr.

Fix: Add `file=sys.stderr` to all status/progress messages.

### m4: `--display` is an unusual flag name

Severity: MINOR
File: `src/ksm/cli.py`

`--display` suggests "show something" not "enter interactive mode." Every other CLI tool uses `--interactive` or `-i` for this.

Fix: Rename to `--interactive` / `-i`. This matches `git add -i`, `npm init -i`, etc.

### m5: No `--dry-run` flag

Severity: MINOR

`add`, `rm`, and `sync` all modify the filesystem. There is no way to preview what will happen without doing it.

Fix: Add `--dry-run` to `add`, `rm`, and `sync`. Print what would be copied/deleted without doing it.

### m6: `rm` does not clean up empty directories

Severity: MINOR
File: `src/ksm/remover.py`

The comment says "Empty subdirectories are left in place." This is a deliberate choice but leaves clutter. After removing a bundle, the user may have empty `steering/`, `skills/`, etc. directories.

Fix: After removing files, walk up and remove empty parent directories up to the `.kiro/` boundary.

### m7: Error messages lack recovery instructions

Severity: MINOR

Most errors follow the pattern `Error: <what happened>` but omit the recovery step. For example:

```
Error: Bundle not found: mybundle
```

Should be:
```
Error: Bundle not found: mybundle
  No registry contains a bundle with this name.
  Run "ksm ls" to see installed bundles, or check available
  bundles with "ksm add --display".
```

### m8: `--from` flag name collides with Python keyword

Severity: MINOR
File: `src/ksm/cli.py`

`--from` is mapped to `dest="from_url"` because `from` is a Python reserved word. This works but is a code smell. More importantly, `--from` is ambiguous — "from where?" could mean many things.

Fix: Rename to `--registry` or `--source`. These are more descriptive and avoid the keyword collision:
```
ksm add mybundle --registry https://github.com/org/repo.git
```

### m9: Version is duplicated

Severity: MINOR
Files: `src/ksm/__init__.py`, `pyproject.toml`

Version `0.1.0` is hardcoded in both places. These will drift.

Fix: Use `importlib.metadata.version("kiro-settings-manager")` in `__init__.py` to read from the installed package metadata, or use `setuptools-scm` for single-source versioning.

### m10: No signal handling

Severity: MINOR

`SIGINT` (Ctrl+C) during a git clone or file copy will leave partial state. There's no cleanup handler.

Fix: Register a `signal.signal(signal.SIGINT, handler)` that cleans up temp directories and prints a brief message to stderr before exiting 130.

---

## 5. Exit Code Audit

| Scenario | Current | Expected | Verdict |
|---|---|---|---|
| Success | 0 | 0 | Correct |
| General error | 1 | 1 | Correct |
| Usage error (argparse) | 2 | 2 | Correct |
| No command given | 2 | 0 (show help) | Debatable — 2 is defensible since no action was taken, but showing help and exiting 0 is more user-friendly |
| `_resolve_subdirs` all miss | `SystemExit(1)` | 1 | Correct but uses `raise SystemExit(1)` directly instead of returning an exit code — breaks the return-code pattern used everywhere else |
| Permission denied | Not handled | 77 | Missing — file operations don't catch `PermissionError` |
| Git not installed | Not handled | 69 | Missing — `subprocess.CalledProcessError` wraps it but the error message won't say "git is not installed" |

Fix: Catch `PermissionError` in copier/installer and return a clear error. Check for `git` binary existence before attempting git operations.

---

## 6. Composability Audit

| Test | Result | Notes |
|---|---|---|
| `ksm ls \| wc -l` | Incorrect count | "No bundles" message pollutes stdout |
| `ksm ls \| grep local` | Works | But fragile due to bracket formatting |
| `ksm ls --format json \| jq` | Not supported | No machine-readable output |
| `echo "y" \| ksm sync --all` | Works | But prompt appears in non-TTY context |
| `ksm add --display \| ...` | Broken | ANSI escapes corrupt pipe |
| `NO_COLOR=1 ksm add --display` | Not respected | Escape sequences still emitted |
| `TERM=dumb ksm add --display` | Not respected | Raw terminal mode still entered |

---

## 7. Accessibility Audit

| Requirement | Status | Notes |
|---|---|---|
| Screen reader safe output | FAIL | Selector uses cursor manipulation and screen clearing |
| `NO_COLOR` respected | FAIL | Not checked anywhere |
| `TERM=dumb` respected | FAIL | Not checked anywhere |
| Symbols paired with text | PASS | No bare symbols used (no ✓/✗ without labels) |
| No decorative borders | PASS | Clean, minimal output |
| Non-TTY fallback | FAIL | Selector crashes or produces garbage |
| Valid UTF-8 output | PASS | All output is plain ASCII/UTF-8 |

---

## 8. Recommended Command Tree (Redesign)

Current:
```
ksm add <bundle> [-l|-g] [--display] [--from URL] [--skills-only] ...
ksm ls
ksm sync [names...] [--all] [--yes]
ksm add-registry <url>
ksm rm <bundle> [-l|-g] [--display]
```

Proposed:
```
ksm add <bundle> [-l|-g] [-i] [--source URL] [--only skills,hooks]
ksm remove <bundle> [-l|-g] [-i] [--yes]
ksm list [--format text|json]
ksm sync [names...] [--all] [--yes] [--dry-run]
ksm registry add <url>
ksm registry list
ksm registry remove <name>

Global flags (all commands):
  -v, --verbose    Verbose output
  -q, --quiet      Suppress non-error output
  -h, --help       Show help
  --version        Show version
  --no-color       Disable color (also: NO_COLOR env var)
```

Key changes:
1. `add-registry` → `registry add/list/remove` subcommand group
2. `--display` → `-i`/`--interactive`
3. `--*-only` → `--only <types>`
4. `--from` → `--source`
5. `rm` → `remove` (unambiguous, matches `docker`, `npm`)
6. `ls` → `list` (keep `ls` as alias for muscle memory)
7. Global `--verbose`, `--quiet`, `--no-color`
8. `--dry-run` on mutating commands
9. `--format` on `list`

---

## 9. Priority Implementation Order

1. C5: Make `-l`/`-g` mutually exclusive (5 min, prevents data loss)
2. C3: Move selector rendering to stderr (30 min)
3. C4: Add non-TTY fallback for selector (1 hr)
4. M7: Add TTY check before sync prompt (15 min)
5. M5: Add `NO_COLOR` and `TERM=dumb` checks (30 min)
6. C1: Add examples to all `--help` output (1 hr)
7. M1: Add `--format json` to `ls` (1 hr)
8. M2: Add confirmation to `rm` (30 min)
9. C2: Add typo suggestions (1 hr)
10. M3: Add `--verbose`/`--quiet` (2 hr)
11. M4: Restructure registry commands (2 hr)
12. M8: Replace `--*-only` with `--only` (1 hr)
