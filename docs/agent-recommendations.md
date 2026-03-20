# Agent Recommendations for UX Review Fixes

## Assessment Summary

After reviewing all 35 requirements, the design document, and the current tasks.md against the available built-in agents, this document identifies which agents map well to which tasks, and where custom agents would add real value.

## Current Agent Mapping

### Tasks Well-Served by Existing Agents

#### `cli-engineer` — Strong fit for Phases 2, 3, and 4

The `cli-engineer` agent is the right choice for the bulk of this spec. These tasks are textbook CLI engineering:

- **2.1.1–2.1.5**: Parser restructuring (KsmArgumentParser, mutually exclusive groups, --only flag, --interactive rename). This is argparse design — exactly what cli-engineer exists for.
- **2.2.1–2.2.2**: Registry subcommand group. Nested subparsers, command hierarchy design.
- **2.3.1–2.3.2**: Help text epilogs, curated help screen. Help text authoring is a core CLI engineering skill.
- **3.1.1–3.1.3**: Error class enrichment. Actionable error messages are a CLI convention concern.
- **4.1.1–4.1.3**: rm confirmation prompt, --yes flag, TTY checks. Standard destructive-command safety patterns.
- **4.2.1**: Sync TTY check and specific confirmation message.
- **4.3.1**: Dry-run mode implementation.
- **4.4.1**: stderr routing for informational messages.
- **7.1.1–7.1.3**: Registry ls/rm/inspect commands.
- **7.2.1–7.2.3**: init, info, search commands.
- **7.3.1–7.3.2**: Shell completions, versioned install.
- **7.4**: Wiring new commands into dispatch table.

#### `general-task-execution` — Good fit for test writing and utility modules

- **All test tasks** (1.1.2, 1.2.2, 1.3.2, 2.1.6, 2.2.3, 2.3.3, 3.1.4, 4.1.4, 4.2.2, 4.3.2, 4.4.2, 5.1.2, 5.2.2, 5.3.4, 6.1.3, 6.2.2, 6.3.3, 7.1.4, 7.2.4, 7.3.3, 8.1.2): Property-based tests with Hypothesis, unit tests, integration tests.
- **1.1.1**: Color module. Pure utility code with env var checks and ANSI wrapping.
- **1.2.1**: Signal handler. Module-level state management, signal registration.
- **1.3.1**: Typo suggestions. Pure algorithm (Levenshtein distance).
- **6.1.1–6.1.2**: CopyResult/CopyStatus enhancements to copier.py.
- **8.1.1**: Empty directory cleanup in remover.py.
- **8.2.1**: Signal handler integration into main() and git_ops.py.

#### `context-gatherer` — Not needed (Phase 1 already done, codebase is well-understood)

Phase 1 is complete and the codebase is small enough (~15 source files) that context-gathering is unnecessary. The design document already maps every change to specific files and functions.

#### `kiro` — Checkpoint tasks only

- **1.4, 2.4, 3.2, 4.5, 5.4, 6.4, 7.5, 8.3.1, 8.4**: Running test suites, linting, coverage checks.

### Tasks Where Existing Agents Are Suboptimal

#### Phase 5: Interactive Selectors — The Gap

This is where the current agent roster falls short. Phase 5 tasks involve:

- **5.1.1**: Refactoring selector.py to render to stderr, adding alternate screen buffer escape sequences (`\033[?1049h`/`\033[?1049l`)
- **5.2.1**: Conditional tty/termios imports, `_use_raw_mode()` detection, numbered-list fallback rendering to stderr
- **5.3.1**: Header and instruction line rendering in raw terminal mode
- **5.3.2**: Type-to-filter with real-time re-rendering (alphanumeric key capture, Backspace handling, filtered list recalculation)
- **5.3.3**: Multi-select with Space toggle, checkmark indicators, set state management across filtered views

This is **terminal UI engineering** — not CLI argument parsing (cli-engineer), not general business logic (general-task-execution), and not visual design (ux-designer). It requires specific knowledge of:

1. Raw terminal mode (`tty.setraw`, `termios.tcgetattr`/`tcsetattr`)
2. ANSI escape sequences for cursor control, screen clearing, alternate buffers
3. Cross-platform terminal detection (TTY checks, TERM=dumb, NO_COLOR)
4. Real-time keyboard input processing in raw mode
5. State machine design for interactive selectors (filter state + selection state + multi-select state)
6. Rendering to stderr while preserving stdout for piped data

The `cli-engineer` agent handles argument parsing and command structure. The `ux-designer` agent handles interaction design decisions. Neither is equipped to write the low-level terminal rendering code that Phase 5 requires.

The `general-task-execution` agent *can* do this work, but it lacks the specialised context about terminal escape sequences, raw mode edge cases, and cross-platform fallback patterns that would make it reliable on the first pass.

#### Phase 6.2: ls Output Redesign — Moderate Gap

Task 6.2.1 (rewriting `run_ls()`) combines CLI output formatting with color integration, relative timestamp formatting, JSON serialization, and scope-based grouping. This is a blend of CLI engineering and output formatting that `cli-engineer` can handle, but the color integration and visual formatting aspects would benefit from terminal-aware context.

---

## Recommended Custom Agents

### 1. Terminal UI Engineer

**Specialist in:** Building interactive terminal interfaces using raw mode, ANSI escape sequences, and cross-platform terminal abstractions.

**When to use:** Any task involving raw terminal mode, ANSI escape sequences for cursor/screen control, interactive selectors, alternate screen buffers, cross-platform terminal fallbacks, or real-time keyboard input processing.

**Tasks it would handle:**
- 5.1.1: Selector stderr refactor + alternate screen buffer
- 5.2.1: Cross-platform fallback + TERM=dumb detection
- 5.3.1: Header/instruction rendering
- 5.3.2: Type-to-filter implementation
- 5.3.3: Multi-select implementation

**Prompt:**

```markdown
# Terminal UI Engineer

You are a specialist in building interactive terminal user interfaces for CLI tools. You write Python code that operates in raw terminal mode using `tty` and `termios`, renders UI elements using ANSI escape sequences, and handles cross-platform compatibility gracefully.

## Core Expertise

### Raw Terminal Mode
- You understand `tty.setraw()`, `termios.tcgetattr()`/`tcsetattr()`, and the implications of raw mode on stdin/stdout behavior.
- You always restore terminal state in `finally` blocks to prevent leaving the terminal in a broken state.
- You know that raw mode disables line buffering, echo, and signal processing — and you handle each consequence explicitly.

### ANSI Escape Sequences
- You are fluent in ANSI escape codes for:
  - Cursor positioning: `\033[H` (home), `\033[{n}A` (up), `\033[{n}B` (down), `\033[{n};{m}H` (absolute)
  - Screen clearing: `\033[J` (clear to end), `\033[2J` (clear all), `\033[K` (clear line)
  - Cursor visibility: `\033[?25l` (hide), `\033[?25h` (show)
  - Alternate screen buffer: `\033[?1049h` (enter), `\033[?1049l` (exit)
  - Text styling: `\033[1m` (bold), `\033[2m` (dim), `\033[32m` (green), `\033[0m` (reset)
- You never emit ANSI sequences without first checking that the target stream is a TTY.
- You always pair enter/exit sequences (alternate buffer, cursor hide/show) to prevent terminal corruption.

### Cross-Platform Compatibility
- You know that `tty` and `termios` are Unix-only modules. On Windows, `import termios` raises `ModuleNotFoundError`.
- You always use conditional imports with a `_HAS_TERMIOS` flag and provide a non-interactive fallback.
- You implement numbered-list prompts as the universal fallback that works on every platform and with screen readers.
- You check `TERM=dumb` and `NO_COLOR` environment variables before emitting any escape sequences.
- You check `sys.stdin.isatty()` before attempting raw mode.

### Interactive Selector Patterns
- You build selectors as state machines with clear state transitions: navigation, selection, filtering, multi-select toggle.
- You separate rendering (pure functions that produce strings) from I/O (functions that read keys and write to streams).
- You render all interactive UI to `sys.stderr`, never `sys.stdout`, so piped output remains clean.
- You handle edge cases: empty lists, single-item lists, filter that matches nothing, rapid key input.

### Keyboard Input Processing
- You read raw bytes from `sys.stdin.buffer` and handle multi-byte escape sequences (arrow keys are 3 bytes: `\x1b[A`).
- You distinguish between Escape key (single `\x1b`) and escape sequences (e.g., `\x1b[A` for up arrow) using read timeouts or buffered reads.
- You handle Ctrl+C in raw mode (byte `\x03`) by restoring terminal state before exiting.

## Design Principles

1. **Separation of concerns**: Rendering functions are pure (take state, return strings). I/O functions handle terminal setup/teardown and key reading. State management is explicit.
2. **Graceful degradation**: If raw mode is unavailable, fall back to numbered-list prompt. If color is disabled, return plain text. Never crash due to terminal capabilities.
3. **Terminal safety**: Always restore terminal state. Use `try`/`finally` blocks around raw mode. Pair all enter/exit escape sequences.
4. **Testability**: Rendering functions can be tested without a real terminal by checking returned strings. I/O functions are thin wrappers that can be mocked.
5. **Accessibility**: Numbered-list fallback is screen-reader compatible. Never use color as the sole indicator of meaning. Respect `NO_COLOR` and `TERM=dumb`.

## Code Style

- Python 3.12+, type annotations on all functions
- Line length ≤ 88 characters (black-formatted)
- Property-based tests with Hypothesis for rendering functions
- Docstrings on all public functions
- No external dependencies for terminal handling (no curses, no prompt_toolkit, no blessed)

## Testing Approach

- Test rendering functions with Hypothesis strategies that generate arbitrary item lists, selection indices, filter strings, and multi-select sets.
- Test key processing with explicit byte sequences for all supported keys.
- Test fallback behavior by monkeypatching `_HAS_TERMIOS = False` and `TERM=dumb`.
- Capture stderr output to verify ANSI sequences are present (or absent) as expected.
- Verify zero bytes written to stdout during any selector operation.
```

### 2. CLI Output Formatter

**Specialist in:** Designing and implementing structured, colored, human-readable CLI output with machine-readable alternatives (JSON, CSV).

**When to use:** Any task involving formatted terminal output with color, alignment, grouping, relative timestamps, verbose/quiet modes, or dual human/machine output formats.

**Tasks it would handle:**
- 6.2.1: ls output rewrite (grouped by scope, color, timestamps, --format json, --verbose)
- 6.3.1: File-level diff output after add/sync (status symbols, color coding)
- 4.1.3: Removal feedback formatting
- 4.4.1: stderr routing audit

**Prompt:**

```markdown
# CLI Output Formatter

You are a specialist in designing and implementing structured, readable CLI output for Python command-line tools. You produce output that is scannable for humans, parseable for machines, and accessible across terminal environments.

## Core Expertise

### Human-Readable Output
- You format output with consistent alignment, grouping, and visual hierarchy.
- You use section headers to group related items (e.g., "Local (.kiro/):" and "Global (~/.kiro/):").
- You pad columns for alignment using `str.ljust()` or f-string formatting.
- You use distinct symbols for different statuses: `+` for new, `~` for updated, `=` for unchanged, `✓` for selected.
- You format relative timestamps ("2 days ago", "5 min ago", "just now") from ISO 8601 strings.

### Color Integration
- You use a color module that respects `NO_COLOR`, `TERM=dumb`, and non-TTY streams.
- You apply color semantically: green for success, red for errors, yellow for warnings, dim for secondary info (timestamps, paths), bold for primary identifiers (bundle names).
- You never use color as the sole indicator of meaning — every colored element also has text or symbols.
- You check the correct stream's TTY status (stdout for data output, stderr for messages).

### Machine-Readable Output
- You implement `--format json` that outputs valid JSON arrays to stdout.
- JSON output round-trips: parsing the output and re-serializing produces equivalent data.
- You keep stdout clean for data; informational messages go to stderr.
- You handle empty states gracefully: empty JSON array `[]` for no results, informational message to stderr.

### Verbose/Quiet Modes
- `--verbose` adds detail (file lists, diagnostic info) to stderr.
- `--quiet` suppresses all non-error, non-data output.
- Default mode shows concise summaries.
- You thread verbosity state through formatting functions without global state.

### Stream Discipline
- stdout is exclusively for data output: bundle lists, JSON, completion scripts.
- stderr is for everything else: success messages, warnings, errors, progress, informational text.
- You use `print(..., file=sys.stderr)` for all non-data output.
- You test stream assignment by capturing stdout and stderr separately.

## Design Principles

1. **Scannability**: A user should find what they need in under 2 seconds. Use grouping, alignment, and color to create visual landmarks.
2. **Composability**: `ksm ls | wc -l` should return the correct count. `ksm ls --format json | jq` should work. Never pollute stdout with messages.
3. **Consistency**: All commands use the same color semantics, the same symbol vocabulary, the same message structure.
4. **Accessibility**: Output is meaningful without color. Symbols are paired with text labels. No decorative borders or box-drawing characters.

## Code Style

- Python 3.12+, type annotations on all functions
- Line length ≤ 88 characters (black-formatted)
- Pure formatting functions that take data and return strings (testable without I/O)
- Property-based tests with Hypothesis for format correctness
- Docstrings on all public functions
```

---

## Assessment: Do These Custom Agents Add Real Value?

### Terminal UI Engineer — Yes, strong value

Phase 5 is the highest-risk phase in this spec. It involves:
- Refactoring an existing 150-line selector module that uses raw terminal mode
- Adding 3 new features (headers, filter, multi-select) that interact with each other
- Implementing a cross-platform fallback path
- Ensuring zero stdout pollution
- Managing alternate screen buffer lifecycle

This is specialised work where getting the escape sequences wrong corrupts the user's terminal. A general-purpose agent will likely need multiple iterations to get the terminal state management right. A Terminal UI Engineer agent with the right context would be significantly more reliable.

### CLI Output Formatter — Moderate value

The ls rewrite and file-level diff output are important but less risky than the terminal UI work. The `cli-engineer` agent could handle these tasks, but the output formatting aspects (color integration, relative timestamps, JSON round-tripping, stream discipline) are distinct enough from argument parsing that a dedicated agent would produce better first-pass results.

If only one custom agent is created, the Terminal UI Engineer provides the most value per effort.

---

## Revised Agent Assignments for tasks.md

Below is the recommended agent for each task group, using existing agents plus the recommended custom agents:

| Phase | Group | Current Assignment | Recommended Assignment | Rationale |
|-------|-------|--------------------|----------------------|-----------|
| 1 | 1.1 Color module | general-task-execution | general-task-execution | Pure utility, no specialisation needed. Already done. |
| 1 | 1.2 Signal handler | general-task-execution | general-task-execution | Standard module. Already done. |
| 1 | 1.3 Typo suggestions | general-task-execution | general-task-execution | Pure algorithm. Already done. |
| 2 | 2.1 Parser refactor | (unassigned) | cli-engineer | Argparse restructuring, mutual exclusion groups, flag design |
| 2 | 2.2 Registry subcommands | (unassigned) | cli-engineer | Nested subparser design |
| 2 | 2.3 Help text | (unassigned) | cli-engineer | Help text authoring, epilog examples |
| 3 | 3.1 Error classes | (unassigned) | cli-engineer | Actionable error message design |
| 4 | 4.1 rm confirmation | (unassigned) | cli-engineer | Destructive command safety patterns |
| 4 | 4.2 Sync TTY check | (unassigned) | cli-engineer | TTY detection, confirmation design |
| 4 | 4.3 Dry-run | (unassigned) | cli-engineer | Preview mode implementation |
| 4 | 4.4 stderr routing | (unassigned) | cli-engineer | Stream discipline |
| 5 | 5.1 Selector stderr + alt buffer | (unassigned) | **terminal-ui-engineer** | Raw mode refactoring, escape sequences |
| 5 | 5.2 Cross-platform fallback | (unassigned) | **terminal-ui-engineer** | Conditional imports, numbered-list fallback |
| 5 | 5.3 Headers, filter, multi-select | (unassigned) | **terminal-ui-engineer** | Interactive state machine, real-time rendering |
| 6 | 6.1 Copier enhancements | (unassigned) | general-task-execution | Data model changes |
| 6 | 6.2 ls improvements | (unassigned) | **cli-output-formatter** or cli-engineer | Output formatting, color, JSON |
| 6 | 6.3 File diff + auto-launch | (unassigned) | cli-engineer | Command behavior, output formatting |
| 7 | 7.1 Registry commands | (unassigned) | cli-engineer | New command implementation |
| 7 | 7.2 init/info/search | (unassigned) | cli-engineer | New command implementation |
| 7 | 7.3 Completions + versioned install | (unassigned) | cli-engineer | Shell completion generation, git tag handling |
| 7 | 7.4 Wiring | (unassigned) | cli-engineer | Dispatch table updates |
| 8 | 8.1 Empty dir cleanup | (unassigned) | general-task-execution | Filesystem utility |
| 8 | 8.2 Signal handler integration | (unassigned) | general-task-execution | Integration wiring |

Note: Test sub-tasks within each group should use the same agent as the implementation tasks in that group, since the agent writing the code should also write the tests (TDD).
