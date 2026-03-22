# UX Visual Design Recommendation: ksm

## Context

ksm is a CLI tool for managing Kiro IDE configuration bundles. It has two visual surfaces: standard CLI output (colors, formatting, spacing) and Textual TUI selectors (interactive pickers for add/rm/scope). The current visual design is functional but flat — basic ANSI colors (green/red/yellow/dim/bold), no TUI theming, and minimal output formatting. The tool looks like a prototype, not a product.

This document provides a concrete, implementable design system to bring ksm's visual identity to a modern, polished standard inspired by tools like Toad (Textual-based terminal UI with rich color, elegant borders, syntax highlighting, and contextual key hints).

## Goals

1. Make ksm output immediately scannable — users should find what they need in under 2 seconds
2. Create a cohesive color palette that works across light and dark terminals
3. Transform the TUI selectors from bare lists into polished, branded interactive experiences
4. Ensure all visual enhancements degrade gracefully (NO_COLOR, TERM=dumb, non-TTY, 8-color terminals)
5. Make the tool feel like it belongs alongside modern CLI tools (gh, cargo, pnpm)

## Design Principles

1. Color supports meaning, never replaces it — every colored element must also be distinguishable without color (symbols, indentation, text labels)
2. Whitespace is a design tool — consistent spacing creates visual hierarchy without clutter
3. Less is more — use color sparingly so it draws the eye to what matters
4. Terminal-native — no Unicode box-drawing that breaks on Windows cmd.exe; prefer ASCII-safe alternatives with Unicode upgrades when detected

---

## 1. Color Palette

### Current State (5 functions)

| Function | ANSI Code | Usage |
|----------|-----------|-------|
| `green`  | `\033[32m` | Success |
| `red`    | `\033[31m` | Errors |
| `yellow` | `\033[33m` | Warnings/deprecation |
| `dim`    | `\033[2m`  | Secondary info |
| `bold`   | `\033[1m`  | Headers |

### Problems

- Standard ANSI green/red/yellow are harsh and dated on most terminal themes
- No cyan/blue for informational or accent use — everything is either "good," "bad," or "muted"
- No way to combine styles (e.g., bold + dim, bold + cyan)
- Missing: underline for links/paths, italic for hints, strikethrough for removed items

### Recommended Palette

Use 16-color ANSI codes (not 256-color) for maximum terminal compatibility. The 16-color palette adapts to the user's terminal theme, so "bright cyan" looks good in both Dracula and Solarized Light.

| Semantic Role | ANSI Code | Escape | Usage |
|---------------|-----------|--------|-------|
| `success` | Bright Green | `\033[92m` | Installed, synced, created, checkmarks |
| `error` | Bright Red | `\033[91m` | Error prefix, failed operations |
| `warning` | Bright Yellow | `\033[93m` | Warning/deprecation prefix |
| `accent` | Bright Cyan | `\033[96m` | Bundle names in lists, registry names, interactive highlights |
| `info` | Bright Blue | `\033[94m` | Informational labels, scope badges, section markers |
| `muted` | Dim | `\033[2m` | Timestamps, paths, secondary metadata |
| `emphasis` | Bold | `\033[1m` | Section headers, command names in help |
| `subtle` | Dim + Italic | `\033[2;3m` | Hints, suggestions, "run this command" text |
| `path` | Underline | `\033[4m` | File paths in diff output (optional, for clarity) |

### Why Bright Variants

Standard ANSI colors (30-37) render differently across terminals — green can be dark olive, red can be maroon. Bright variants (90-97) are more consistent and vibrant across terminal themes. They're still part of the base 16-color set, so they work everywhere that supports color at all.

### Composability

Add a `style()` function that accepts multiple codes:

```python
def style(text: str, *codes: str, stream: TextIO | None = None) -> str:
    """Apply multiple ANSI style codes to text.
    
    Example: style("hello", "1", "96") → bold bright cyan
    """
    if not _color_enabled(stream):
        return text
    combined = ";".join(codes)
    return f"\033[{combined}m{text}\033[0m"
```

### Semantic Wrappers (New color.py API)

```python
# Keep existing for backward compat, add semantic layer:
def success(text: str, stream: TextIO | None = None) -> str:
    """Bright green — success states."""
    return _wrap(text, "92", stream)

def error_style(text: str, stream: TextIO | None = None) -> str:
    """Bright red — error states."""
    return _wrap(text, "91", stream)

def warning_style(text: str, stream: TextIO | None = None) -> str:
    """Bright yellow — warnings."""
    return _wrap(text, "93", stream)

def accent(text: str, stream: TextIO | None = None) -> str:
    """Bright cyan — bundle names, highlights."""
    return _wrap(text, "96", stream)

def info(text: str, stream: TextIO | None = None) -> str:
    """Bright blue — informational labels."""
    return _wrap(text, "94", stream)

def muted(text: str, stream: TextIO | None = None) -> str:
    """Dim — secondary information."""
    return _wrap(text, "2", stream)

def subtle(text: str, stream: TextIO | None = None) -> str:
    """Dim italic — hints and suggestions."""
    return _wrap(text, "2;3", stream)
```

Keep `green`, `red`, `yellow`, `dim`, `bold` as aliases for backward compatibility. Migrate command files to use semantic names over time.

---

## 2. CLI Output Formatting

### 2.1 Section Headers

Use a consistent pattern for section headers across all commands. Do not use box-drawing characters — they add visual noise without information.

**Pattern:**
```
<Bold header text>
<content indented 2 spaces>
```

**Before (ls):**
```
Local bundles:
  my-bundle  (default)  2 days ago
```

**After (ls):**
```
Local bundles:
  my-bundle       default       2 days ago
  other-bundle    my-registry   5 min ago

Global bundles:
  shared-config   default       1 week ago
```

Changes:
- Column-aligned output using calculated padding
- Registry name without parentheses (cleaner)
- Relative timestamps right-aligned or consistently spaced

### 2.2 `ksm list` — Detailed Before/After

**Current output:**
```
Local bundles:
  my-bundle  (default)  2 days ago
  other-bundle  (my-registry)  5 min ago

Global bundles:
  shared-config  (default)  1 week ago
```

**Recommended output (color annotations in brackets):**
```
[bold]Local bundles:[/bold]
  [accent]my-bundle[/accent]       [muted]default[/muted]       [muted]2 days ago[/muted]
  [accent]other-bundle[/accent]    [muted]my-registry[/muted]   [muted]5 min ago[/muted]

[bold]Global bundles:[/bold]
  [accent]shared-config[/accent]   [muted]default[/muted]       [muted]1 week ago[/muted]
```

**With `-v` (verbose):**
```
[bold]Local bundles:[/bold]
  [accent]my-bundle[/accent]       [muted]default[/muted]       [muted]2 days ago[/muted]
    [muted]steering/code-review.md[/muted]
    [muted]steering/testing.md[/muted]
    [muted]skills/refactor/SKILL.md[/muted]
  [accent]other-bundle[/accent]    [muted]my-registry[/muted]   [muted]5 min ago[/muted]
    [muted]hooks/pre-commit.json[/muted]
```

**Implementation notes:**
- Calculate `max_name_width` and `max_registry_width` from the entry set
- Use `str.ljust()` for column alignment
- Bundle names get `accent` (bright cyan) — this is the primary information
- Registry and timestamp get `muted` — secondary context
- Verbose file paths indented 4 spaces, all `muted`

### 2.3 `ksm add` — Success Output

**Current:**
```
Installed: 'my-bundle'
  + /path/to/steering/code-review.md (new)
  ~ /path/to/skills/refactor/SKILL.md (updated)
  = /path/to/hooks/pre-commit.json (unchanged)
```

**Recommended:**
```
[success]✓[/success] Installed [accent]my-bundle[/accent] [muted]→ .kiro/ (local)[/muted]
  [success]+[/success] steering/code-review.md [muted](new)[/muted]
  [warning]~[/warning] skills/refactor/SKILL.md [muted](updated)[/muted]
  [muted]=[/muted] hooks/pre-commit.json [muted](unchanged)[/muted]
```

Changes:
- Leading `✓` symbol (with ASCII fallback `*` for non-Unicode terminals)
- Scope shown inline after arrow — user immediately knows where files went
- File paths are relative to `.kiro/`, not absolute — shorter, more meaningful
- Status symbols colored, labels muted
- No quotes around bundle name — the accent color distinguishes it

### 2.4 `ksm rm` — Confirmation and Result

**Confirmation prompt (recommended):**
```
Remove [accent]my-bundle[/accent] from [info]local[/info] scope?
  [muted]4 files in .kiro/:[/muted]
    [muted]steering/code-review.md[/muted]
    [muted]steering/testing.md[/muted]
    [muted]skills/refactor/SKILL.md[/muted]
    [muted]hooks/pre-commit.json[/muted]

Continue? [bold][y/n][/bold] 
```

**Result (recommended):**
```
[success]✓[/success] Removed [accent]my-bundle[/accent] [muted]— 4 files deleted (local)[/muted]
```

**With skipped files:**
```
[success]✓[/success] Removed [accent]my-bundle[/accent] [muted]— 3 files deleted, 1 already missing (local)[/muted]
```

### 2.5 `ksm sync` — Confirmation and Result

**Confirmation (recommended):**
```
Sync [bold]3[/bold] bundles?
  [accent]my-bundle[/accent]       [muted]local  · 4 files[/muted]
  [accent]other-bundle[/accent]    [muted]local  · 1 file[/muted]
  [accent]shared-config[/accent]   [muted]global · 3 files[/muted]

This will overwrite configuration files. Continue? [bold][y/n][/bold] 
```

**Per-bundle result:**
```
[success]✓[/success] Synced [accent]my-bundle[/accent]
  [success]+[/success] steering/new-file.md [muted](new)[/muted]
  [warning]~[/warning] steering/code-review.md [muted](updated)[/muted]
  [muted]=[/muted] skills/refactor/SKILL.md [muted](unchanged)[/muted]
```

### 2.6 Error Messages

**Current format (good structure, needs color refinement):**
```
Error: Bundle 'foo' not found.
  Searched 2 registries: default, my-registry
  Run `ksm registry list` to see available registries.
```

**Recommended:**
```
[error]error:[/error] Bundle [accent]foo[/accent] not found
  [muted]Searched 2 registries: default, my-registry[/muted]
  [subtle]Run `ksm registry list` to see available registries.[/subtle]
```

Changes:
- Lowercase `error:` prefix (matches cargo, rustc, gh conventions — less shouty)
- Bundle name highlighted with accent color
- "Why" line is muted
- "Fix" line is subtle (dim italic) — visually distinct from the explanation
- No period at end of first line (convention in modern CLIs)

### 2.7 Warning and Deprecation Messages

**Warning (recommended):**
```
[warning]warning:[/warning] -i ignored because a bundle was specified
  [muted]Proceeding with the specified bundle.[/muted]
```

**Deprecation (recommended):**
```
[warning]deprecated:[/warning] [muted]`--display` is deprecated, use `-i/--interactive` instead[/muted]
  [subtle]Deprecated in v0.2.0, will be removed in v1.0.0.[/subtle]
```

### 2.8 `ksm info` Output

**Current:**
```
my-bundle
  Registry: default
  Path:     /path/to/registry/my-bundle
  Contents:
    steering/ (2 items)
  Installed: local
```

**Recommended:**
```
[accent]my-bundle[/accent]
  Registry   [muted]default[/muted]
  Contents   [muted]steering/[/muted] 2 items · [muted]skills/[/muted] 1 item
  Installed  [success]local[/success]
```

Changes:
- Remove `Path:` line — internal implementation detail, not useful to users
- Flatten contents to a single line with `·` separator
- Align labels without colons (cleaner, matches modern CLI style like `gh repo view`)
- Installed scope gets success color when installed, muted "no" when not

### 2.9 `ksm search` Output

**Current:**
```
  my-bundle  (default)  steering, skills
```

**Recommended:**
```
[accent]my-bundle[/accent]         [muted]default[/muted]    [muted]steering, skills[/muted]
[accent]other-bundle[/accent]      [muted]custom[/muted]     [muted]hooks[/muted]
```

Column-aligned, accent on names, muted on metadata. If no results:

```
No bundles matching [accent]foo[/accent]
[subtle]Try a broader search or run `ksm registry inspect <name>` to browse.[/subtle]
```

### 2.10 `ksm registry ls` Output

**Current:**
```
  default
    URL:     (local)
    Path:    /path/to/registry
    Bundles: 3 bundles
```

**Recommended:**
```
[accent]default[/accent]          [muted](local)[/muted]          [muted]3 bundles[/muted]
[accent]my-registry[/accent]     [muted]github.com/...[/muted]   [muted]5 bundles[/muted]
```

Changes:
- Single-line per registry (scannable)
- Remove `Path:` — internal detail
- Column-aligned
- Add `--verbose` to show full URL and path if needed

### 2.11 `ksm registry inspect` Output

**Current (good structure, needs color):**
```
Registry: my-registry
  URL:     https://github.com/...
  Path:    /path/to/cache
  Default: no
  Bundles: 3

  my-bundle
    steering/ (2 items)
      code-review.md
      testing.md
```

**Recommended:**
```
[bold]my-registry[/bold]  [muted]https://github.com/...[/muted]

  [accent]my-bundle[/accent]
    [muted]steering/[/muted]  code-review.md, testing.md
    [muted]skills/[/muted]    refactor/
  [accent]other-bundle[/accent]
    [muted]hooks/[/muted]     pre-commit.json
```

Changes:
- Flatten item lists to comma-separated on one line (scannable)
- Remove Default/Path/Bundles count metadata (noise for most users)
- Items listed inline after subdirectory name

### 2.12 `ksm init` Output

**Current:**
```
Initialised .kiro/ directory.
```

**Recommended:**
```
[success]✓[/success] Initialised [info].kiro/[/info] in current directory
[subtle]Run `ksm add` to install your first bundle.[/subtle]
```

If already exists:
```
[muted]Already initialised — .kiro/ exists.[/muted]
```

---

## 3. Typography and Spacing

### Spacing Rules

Apply these consistently across all command output:

1. **Section gap:** One blank line between scope groups in `ls`, between bundles in `inspect`
2. **Indentation:** 2 spaces for first-level content, 4 spaces for nested content (file lists)
3. **No trailing blank lines** — trim them (already done in most commands, keep it)
4. **Column alignment:** Calculate max width per column and `ljust()` — do this for `ls`, `search`, `registry ls`, and any tabular output
5. **Separator character:** Use `·` (middle dot, U+00B7) for inline metadata separation: `local · 4 files`. Fallback to `-` for non-Unicode terminals.

### Column Alignment Implementation

```python
def _align_columns(
    rows: list[tuple[str, ...]],
    gap: int = 2,
) -> list[str]:
    """Align columns with consistent padding.
    
    Each row is a tuple of column values. Returns formatted
    lines with columns padded to align.
    """
    if not rows:
        return []
    col_count = len(rows[0])
    widths = [0] * col_count
    for row in rows:
        for i, val in enumerate(row):
            # Strip ANSI codes for width calculation
            plain = _strip_ansi(val)
            widths[i] = max(widths[i], len(plain))
    
    lines = []
    for row in rows:
        parts = []
        for i, val in enumerate(row):
            if i < col_count - 1:  # Don't pad last column
                plain_len = len(_strip_ansi(val))
                padding = widths[i] - plain_len + gap
                parts.append(val + " " * padding)
            else:
                parts.append(val)
        lines.append("".join(parts))
    return lines


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences for width calculation."""
    import re
    return re.sub(r'\033\[[0-9;]*m', '', text)
```

### Unicode Detection

```python
import locale
import os

def _supports_unicode() -> bool:
    """Check if the terminal likely supports Unicode."""
    if os.environ.get("TERM") == "dumb":
        return False
    encoding = locale.getpreferredencoding(False)
    return encoding.lower() in ("utf-8", "utf8")

# Use throughout:
CHECK = "✓" if _supports_unicode() else "*"
ARROW = "→" if _supports_unicode() else "->"
DOT = "·" if _supports_unicode() else "-"
```

---

## 4. Textual TUI Theme

### Current State

The three TUI apps (BundleSelectorApp, RemovalSelectorApp, ScopeSelectorApp) use minimal CSS:
- `text-style: bold` and `text-style: dim` on a few classes
- `height: 1fr` on OptionList
- `dock: top` on Input, `dock: bottom` on selected-count
- No borders, no color theme, no focus styling, no custom scrollbar

This produces a functional but visually bare experience — black background, white text, no visual hierarchy.

### Recommended Textual CSS Theme

The following CSS creates a polished, Toad-inspired look. Key design decisions:
- Dark background with subtle contrast layers (not pure black)
- Cyan accent color for focus and selection (matches CLI palette)
- Rounded borders on the main container
- Footer bar with contextual key hints (Toad's signature pattern)
- Smooth focus transitions

#### BundleSelectorApp and RemovalSelectorApp (shared theme)

```python
CSS: ClassVar[str] = """
Screen {
    background: $surface;
    layout: vertical;
}

#container {
    border: round $accent;
    border-title-color: $accent;
    border-title-style: bold;
    padding: 0 1;
    margin: 1 2;
    height: 1fr;
}

.selector-header {
    text-style: bold;
    color: $text;
    padding: 0 0 1 0;
}

.selector-instructions {
    color: $text-muted;
    padding: 0 0 1 0;
}

Input {
    dock: top;
    margin: 0 0 1 0;
    border: tall $accent 30%;
    background: $surface-darken-1;
    color: $text;
    padding: 0 1;
}

Input:focus {
    border: tall $accent;
}

Input.-invalid {
    border: tall $error;
}

OptionList {
    height: 1fr;
    background: transparent;
    border: none;
    scrollbar-color: $accent 30%;
    scrollbar-color-hover: $accent 60%;
    scrollbar-color-active: $accent;
    padding: 0;
}

OptionList > .option-list--option-highlighted {
    background: $accent 15%;
    color: $text;
    text-style: bold;
}

OptionList > .option-list--option-hover {
    background: $accent 8%;
}

OptionList:focus > .option-list--option-highlighted {
    background: $accent 25%;
}

#selected-count {
    dock: bottom;
    text-style: bold;
    color: $accent;
    padding: 1 0 0 0;
    text-align: right;
}

#footer-bar {
    dock: bottom;
    height: 1;
    background: $accent 15%;
    color: $text-muted;
    padding: 0 1;
}

.key-hint {
    text-style: bold;
    color: $accent;
}
"""
```

#### ScopeSelectorApp (simpler, no filter)

```python
CSS: ClassVar[str] = """
Screen {
    background: $surface;
    align: center middle;
}

#scope-container {
    border: round $accent;
    border-title-color: $accent;
    border-title-style: bold;
    padding: 1 2;
    width: 40;
    height: auto;
    max-height: 12;
}

.selector-header {
    text-style: bold;
    color: $text;
    padding: 0 0 1 0;
}

.selector-instructions {
    color: $text-muted;
    padding: 0 0 1 0;
}

OptionList {
    height: auto;
    max-height: 4;
    background: transparent;
    border: none;
}

OptionList > .option-list--option-highlighted {
    background: $accent 20%;
    color: $text;
    text-style: bold;
}

OptionList:focus > .option-list--option-highlighted {
    background: $accent 30%;
}
"""
```

### Structural Changes to TUI Apps

To support the new theme, wrap content in a container widget and add a footer bar:

#### BundleSelectorApp.compose() — recommended:

```python
def compose(self) -> ComposeResult:
    with Container(id="container"):
        yield Static(
            "Select a bundle to install",
            classes="selector-header",
        )
        yield Input(placeholder="Type to filter...")
        yield OptionList()
        yield Static("", id="selected-count")
    yield Static(
        " [key-hint]↑↓[/] Navigate  "
        "[key-hint]Space[/] Toggle  "
        "[key-hint]Enter[/] Confirm  "
        "[key-hint]Esc[/] Cancel",
        id="footer-bar",
    )
```

This moves the instructions from a Static text widget into a Toad-style footer bar with highlighted key names. The `[key-hint]` markup uses Textual's Rich markup to apply the `.key-hint` CSS class.

#### Container border title:

```python
def on_mount(self) -> None:
    container = self.query_one("#container")
    container.border_title = "ksm"
    self._refresh_options()
    self.query_one(OptionList).focus()
```

### Color Variables (Textual Design System)

Define a custom Textual theme that maps to the CLI palette:

```python
from textual.theme import Theme

KSM_THEME = Theme(
    name="ksm",
    primary="#56b6c2",      # Cyan accent
    secondary="#61afef",    # Blue info
    accent="#56b6c2",       # Cyan
    success="#98c379",      # Soft green
    warning="#e5c07b",      # Soft yellow  
    error="#e06c75",        # Soft red
    surface="#282c34",      # Dark background
    panel="#21252b",        # Slightly darker panels
)
```

Register this theme in each App's `__init__`:

```python
def __init__(self, ...):
    super().__init__()
    self.register_theme(KSM_THEME)
    self.theme = "ksm"
```

These colors are inspired by the One Dark theme family — widely used, proven readable, and aesthetically cohesive. They match the "modern, clean" aesthetic of Toad without copying it directly.

### OptionList Item Formatting

Replace plain text options with Rich markup for visual hierarchy:

**Current:**
```python
ol.add_option(Option(f"{check}{display}{badge}", id=str(i)))
```

**Recommended:**
```python
# Use Rich Text for styled options
from rich.text import Text

label = Text()
label.append(check, style="bold")
label.append(display, style="bold cyan" if highlighted else "")
if badge:
    label.append(badge, style="dim")
ol.add_option(Option(label, id=str(i)))
```

This gives bundle names color and installed badges a muted appearance, even within the OptionList widget.

---

## 5. Graceful Degradation

### Degradation Tiers

| Environment | Behavior |
|-------------|----------|
| Full color TTY | All colors, Unicode symbols, Textual TUI |
| 8-color terminal | Fall back to standard ANSI (30-37) instead of bright (90-97) |
| `NO_COLOR` set | No ANSI codes, plain text, symbols still used |
| `TERM=dumb` | No ANSI codes, no Unicode symbols, ASCII fallbacks |
| Non-TTY (piped) | No ANSI codes, no Unicode, no interactive TUI |
| Textual unavailable | Numbered-list fallback (already implemented) |

### Implementation

The existing `_color_enabled()` function handles NO_COLOR, TERM=dumb, and non-TTY. Extend it:

```python
def _color_level(stream: TextIO | None = None) -> int:
    """Determine color support level.
    
    Returns:
        0: No color (NO_COLOR, TERM=dumb, non-TTY)
        1: Basic 8-color ANSI
        2: 16-color (bright variants)
        3: 256-color
        4: True color (24-bit)
    """
    if not _color_enabled(stream):
        return 0
    colorterm = os.environ.get("COLORTERM", "")
    if colorterm in ("truecolor", "24bit"):
        return 4
    term = os.environ.get("TERM", "")
    if "256color" in term:
        return 3
    return 2  # Default to 16-color for TTY

def _wrap(text: str, code: str, stream: TextIO | None = None) -> str:
    """Wrap text with ANSI escape code if color is enabled.
    
    For bright codes (90-97), falls back to standard (30-37)
    on 8-color terminals.
    """
    level = _color_level(stream)
    if level == 0:
        return text
    if level == 1:
        # Downgrade bright to standard
        code_int = int(code.split(";")[-1]) if ";" in code else int(code)
        if 90 <= code_int <= 97:
            code = str(code_int - 60)
    return f"\033[{code}m{text}\033[0m"
```

---

## 6. Symbol System

Define a consistent symbol vocabulary used across all commands:

| Symbol | Unicode | ASCII Fallback | Meaning |
|--------|---------|----------------|---------|
| ✓ | U+2713 | `*` | Success/complete |
| ✗ | U+2717 | `x` | Failure |
| + | `+` | `+` | New file |
| ~ | `~` | `~` | Updated file |
| = | `=` | `=` | Unchanged file |
| → | U+2192 | `->` | Direction/target |
| · | U+00B7 | `-` | Inline separator |
| ▸ | U+25B8 | `>` | Current selection (TUI fallback) |

Centralize these in `color.py`:

```python
_UNICODE = _supports_unicode()

SYM_CHECK = "✓" if _UNICODE else "*"
SYM_CROSS = "✗" if _UNICODE else "x"
SYM_ARROW = "→" if _UNICODE else "->"
SYM_DOT = "·" if _UNICODE else "-"
SYM_NEW = "+"
SYM_UPDATED = "~"
SYM_UNCHANGED = "="
```

---

## 7. Implementation Plan

### Phase 1: Color System (Low effort, high impact)

1. Extend `color.py` with semantic color functions (`success`, `accent`, `info`, `muted`, `subtle`), `style()` composability, `_color_level()` for degradation, `_strip_ansi()` for width calculation, `_supports_unicode()` and symbol constants
2. Add `_align_columns()` utility to `color.py` (or a new `formatting.py`)
3. Update `errors.py` to use lowercase prefixes (`error:`, `warning:`, `deprecated:`) and semantic colors
4. Update `format_diff_summary` in `copier.py` to use relative paths and semantic colors

### Phase 2: Command Output (Medium effort, high impact)

5. Update `ls.py` — column-aligned output, accent on bundle names, muted metadata
6. Update `add.py` — `✓ Installed` format with scope indicator
7. Update `rm.py` — improved confirmation prompt and result format
8. Update `sync.py` — per-bundle listing in confirmation, `✓ Synced` format
9. Update `info.py` — flattened contents, removed path line
10. Update `search.py` — column-aligned, accent names
11. Update `registry_ls.py` — single-line per registry
12. Update `registry_inspect.py` — inline item lists
13. Update `init.py` — success symbol and next-step hint

### Phase 3: TUI Theme (Medium effort, high impact)

14. Create `KSM_THEME` in `tui.py` and register it in all three apps
15. Update CSS for BundleSelectorApp and RemovalSelectorApp (container, borders, footer bar, focus states, scrollbar)
16. Update CSS for ScopeSelectorApp (centered container, rounded border)
17. Update `compose()` methods to use Container wrapper and footer bar
18. Add Rich Text formatting to OptionList items

### Phase 4: Polish (Low effort, medium impact)

19. Add `--verbose` to `registry ls` for full URL/path display
20. Ensure all empty states have helpful next-step hints
21. Test across terminal themes: Dracula, Solarized Light, Solarized Dark, One Dark, macOS Terminal default, Windows Terminal default
22. Test degradation: NO_COLOR, TERM=dumb, piped output, 8-color terminal

---

## 8. Rationale: Why This Approach

### Why 16-color ANSI, not 256-color or true color?

256-color and true color look great in modern terminals but break badly in older ones, SSH sessions, and CI environments. The 16-color palette adapts to the user's terminal theme — bright cyan in Dracula is different from bright cyan in Solarized, but both look intentional. This is a feature, not a limitation. The tool respects the user's aesthetic choices.

### Why semantic color names, not visual ones?

`success()` instead of `bright_green()` because the meaning matters more than the implementation. If we later decide success should be blue (unlikely, but possible), we change one function. Every call site already expresses intent.

### Why lowercase error/warning prefixes?

Modern CLI tools (cargo, rustc, gh, pnpm) use lowercase prefixes. It reads as conversational rather than alarming. `error: bundle not found` feels like a helpful message. `Error: Bundle not found` feels like a system dialog from 2005. This is a small change with outsized impact on perceived quality.

### Why Toad-style footer bar in TUI?

The footer bar pattern (key hints at the bottom of the screen) is the single most impactful TUI design pattern. It eliminates the "what do I press?" problem entirely. Toad does this well, and so do vim, htop, and midnight commander. It's a proven pattern that costs almost nothing to implement in Textual.

### Why not Rich library for CLI output?

Rich is excellent but adds a dependency and a different rendering model. ksm's output is simple enough that ANSI codes + `_align_columns()` handle everything needed. The Textual TUI already uses Rich internally, so Rich markup is available there. For CLI output, keeping it lightweight with direct ANSI codes means fewer dependencies and faster startup.

### Why One Dark-inspired colors for the TUI theme?

One Dark is the most popular dark theme family across VS Code, terminal emulators, and code editors. Users of Kiro IDE are likely already familiar with this aesthetic. The specific values chosen (`#56b6c2` cyan, `#98c379` green, `#e06c75` red) are proven readable at terminal font sizes and have sufficient contrast ratios against dark backgrounds.

---

## 9. Open Questions

1. **Should `ksm` adopt Rich for CLI output in the future?** If output complexity grows (tables, progress bars, markdown rendering), Rich becomes worth the dependency. For now, ANSI codes suffice. Revisit when adding features like `ksm diff` or `ksm status`.

2. **Should the TUI theme respect the user's terminal theme or enforce its own?** The current recommendation enforces a dark theme via `KSM_THEME`. An alternative is to use Textual's default theme (which inherits terminal colors). The enforced theme is more polished but may clash with light terminal users. Consider offering `ksm --light` or detecting `COLORFGBG` environment variable.

3. **Should column alignment account for CJK wide characters?** If bundle names or registry names contain CJK characters, `len()` undercounts display width. Use `unicodedata.east_asian_width()` or `wcwidth` library for accurate column alignment. This is a polish item — implement if internationalization becomes a concern.

4. **Should the `✓` symbol be used on Windows?** Windows Terminal supports Unicode, but legacy cmd.exe and PowerShell ISE may not. The `_supports_unicode()` check should handle this, but test on Windows before shipping.

---

## 10. Summary of Changes by File

| File | Changes |
|------|---------|
| `src/ksm/color.py` | Add `success`, `accent`, `info`, `muted`, `subtle`, `style()`, `_color_level()`, `_strip_ansi()`, `_supports_unicode()`, `_align_columns()`, symbol constants |
| `src/ksm/errors.py` | Lowercase prefixes, use semantic colors, accent on bundle names in messages |
| `src/ksm/copier.py` | Use semantic colors in `format_diff_summary`, relative paths |
| `src/ksm/tui.py` | Add `KSM_THEME`, new CSS for all three apps, Container wrapper, footer bar, Rich Text options |
| `src/ksm/selector.py` | Update `render_add_selector` and `render_removal_selector` to use new color functions |
| `src/ksm/commands/ls.py` | Column-aligned output, accent bundle names, muted metadata |
| `src/ksm/commands/add.py` | `✓ Installed` format, scope indicator, relative paths |
| `src/ksm/commands/rm.py` | Improved confirmation, `✓ Removed` format |
| `src/ksm/commands/sync.py` | Per-bundle confirmation listing, `✓ Synced` format |
| `src/ksm/commands/info.py` | Flattened contents, removed path, semantic colors |
| `src/ksm/commands/search.py` | Column-aligned, accent names, helpful empty state |
| `src/ksm/commands/init.py` | Success symbol, next-step hint |
| `src/ksm/commands/registry_ls.py` | Single-line format, column-aligned |
| `src/ksm/commands/registry_inspect.py` | Inline item lists, cleaner header |
