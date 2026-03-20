commit 19fa7adaf2b649d4b299ffa1906c68cdf145db70
Author: Tom Stanley <tom@ilingu.com>
Date:   Fri Mar 20 15:06:57 2026 +0800

    feat(ksm): add enhancement spec with agent recommendations and project updates
    
    - Add KSM enhancements specification with requirements, design, and task breakdown
    - Include agent recommendations for hypothesis-test-writer and argparse-cli-refactorer
    - Add LICENSE file to project
    - Update README with project overview and setup instructions
    - Bump project version in pyproject.toml
    - Enhance scanner.py with improved registry scanning logic
    - Add comprehensive test coverage for registry addition and scanner functionality
    - Configure Kiro workflow for requirements-first feature development

diff --git a/.kiro/specs/ksm-enhancements/design.md b/.kiro/specs/ksm-enhancements/design.md
new file mode 100644
index 0000000..0119693
--- /dev/null
+++ b/.kiro/specs/ksm-enhancements/design.md
@@ -0,0 +1,779 @@
+# Design Document: KSM Enhancements
+
+## Overview
+
+This design covers 14 enhancements to the ksm (Kiro Settings Manager) CLI tool. The changes fall into four categories:
+
+1. **CLI restructuring** — Full-word command aliases (`list`/`remove`), registry subcommand group restructuring (`registry add/remove/list/inspect`), deprecation of legacy `add-registry`, and renaming `--display` to `-i`/`--interactive`.
+2. **Registry add/remove improvements** — Cache directory conflict handling with `--force`, duplicate URL detection, custom `--name` flag, and improved remove feedback.
+3. **Bundle resolution** — Qualified bundle name syntax (`registry_name/bundle_name`), multi-registry disambiguation, and resolver changes to scan all registries.
+4. **Flag and message standardisation** — Consolidating `--*-only` into `--only`, standardised three-line error format, and registry inspect output specification.
+
+The design prioritises refactoring existing modules over creating new ones. All changes target the existing file structure under `src/ksm/`.
+
+## Architecture
+
+### Current Architecture
+
+```
+cli.py (_build_parser → argparse → dispatch table)
+  ├── commands/add.py        → resolver.py → scanner.py → installer.py
+  ├── commands/rm.py         → manifest.py → remover.py
+  ├── commands/registry_add.py → git_ops.py → registry.py
+  ├── commands/registry_rm.py  → registry.py
+  ├── commands/registry_ls.py  → registry.py → scanner.py
+  ├── commands/registry_inspect.py → registry.py → scanner.py
+  └── commands/add_registry.py (legacy, duplicates registry_add.py)
+```
+
+### Changed Architecture
+
+```
+cli.py (_build_parser → argparse with aliases → dispatch table)
+  ├── commands/add.py        → resolver.py (multi-match) → scanner.py
+  ├── commands/rm.py         → manifest.py → remover.py
+  ├── commands/registry_add.py → git_ops.py → registry.py (--force, --name, conflict detection)
+  ├── commands/registry_rm.py  → registry.py (improved feedback)
+  ├── commands/registry_ls.py  → registry.py → scanner.py
+  ├── commands/registry_inspect.py → registry.py → scanner.py (enhanced output)
+  ├── commands/add_registry.py (legacy, prints deprecation, delegates to registry_add)
+  ├── errors.py (format_error, format_warning, format_deprecation helpers)
+  └── selector.py (qualified name display for ambiguous bundles)
+```
+
+### Key Design Decisions
+
+1. **No new modules** — All changes are refactors of existing files. The `errors.py` module gains formatting helpers; no new command files are created.
+2. **Legacy `add_registry.py` becomes a thin wrapper** — It prints a deprecation warning then delegates to `registry_add.run_registry_add()`, eliminating code duplication.
+3. **Resolver returns all matches** — `resolve_bundle()` changes from returning the first match to returning a `ResolvedBundleResult` containing all matches, enabling ambiguity detection at the call site.
+4. **argparse aliases for subcommands** — Uses argparse's built-in `aliases` parameter on `add_parser()` to support `list`/`ls`, `remove`/`rm` without duplicate parser definitions.
+5. **`--display` hidden but retained** — Uses `argparse.SUPPRESS` for help text while keeping the flag functional, plus a deprecation warning on use.
+
+## Components and Interfaces
+
+### 1. `cli.py` — Parser Restructuring
+
+**Changes to `_build_parser()`:**
+
+```python
+def _build_parser() -> argparse.ArgumentParser:
+    # Top-level aliases: "list" primary with "ls" alias, "remove" primary with "rm" alias
+    sub.add_parser("list", aliases=["ls"], help="List installed bundles (ls)")
+    sub.add_parser("remove", aliases=["rm"], help="Remove an installed bundle (rm)")
+
+    # add command: replace --display with -i/--interactive, add --only
+    add_p.add_argument("-i", "--interactive", action="store_true", help="Launch interactive selector")
+    add_p.add_argument("--display", action="store_true", help=argparse.SUPPRESS)  # hidden, deprecated
+    add_p.add_argument("--only", action="append", default=None, help="Subdirectory types to install (skills,agents,steering,hooks)")
+    # Remove individual --*-only from visible help, keep with SUPPRESS
+    add_p.add_argument("--skills-only", action="store_true", help=argparse.SUPPRESS)
+    # ... same for agents-only, steering-only, hooks-only
+
+    # rm/remove command: same -i/--interactive treatment
+    rm_p.add_argument("-i", "--interactive", action="store_true", help="Launch interactive selector")
+    rm_p.add_argument("--display", action="store_true", help=argparse.SUPPRESS)
+
+    # registry subcommand group
+    reg_sub.add_parser("add", help="Add a registry")
+    reg_sub.add_parser("remove", aliases=["rm"], help="Remove a registry (rm)")
+    reg_sub.add_parser("list", aliases=["ls"], help="List registries (ls)")
+    reg_sub.add_parser("inspect", help="Inspect a registry")
+
+    # registry add flags
+    reg_add_p.add_argument("git_url", nargs="?", help="Git URL of the registry")
+    reg_add_p.add_argument("-f", "--force", action="store_true", help="Replace existing cache directory")
+    reg_add_p.add_argument("--name", dest="custom_name", default=None, help="Custom registry name")
+    reg_add_p.add_argument("-i", "--interactive", action="store_true", help="Interactive registry add")
+
+    # legacy add-registry: same flags
+    ar_p.add_argument("-f", "--force", action="store_true", help=argparse.SUPPRESS)
+    ar_p.add_argument("--name", dest="custom_name", default=None, help=argparse.SUPPRESS)
+```
+
+**Changes to dispatch table:**
+
+```python
+_DISPATCH_NAMES: dict[str, str] = {
+    "add": "_dispatch_add",
+    "list": "_dispatch_ls",    # primary full-word
+    "ls": "_dispatch_ls",      # alias
+    "sync": "_dispatch_sync",
+    "add-registry": "_dispatch_add_registry",
+    "remove": "_dispatch_rm",  # primary full-word
+    "rm": "_dispatch_rm",      # alias
+    "registry": "_dispatch_registry",
+    "init": "_dispatch_init",
+    "info": "_dispatch_info",
+    "search": "_dispatch_search",
+    "completions": "_dispatch_completions",
+}
+```
+
+**Help text deduplication:** The `aliases` parameter on `add_parser()` handles this natively — argparse shows one entry with the alias noted. For the top-level commands where we use separate `add_parser` calls (since argparse doesn't support top-level aliases directly), we register both names but only show the full-word form in help by using `help=argparse.SUPPRESS` on the short alias parser.
+
+### 2. `errors.py` — Standardised Message Formatting
+
+**New helper functions:**
+
+```python
+def format_error(what: str, why: str, fix: str) -> str:
+    """Format a three-line error message.
+    
+    Returns:
+        Error: {what}
+          {why}
+          {fix}
+    """
+    return f"Error: {what}\n  {why}\n  {fix}"
+
+
+def format_warning(what: str, detail: str) -> str:
+    """Format a warning message.
+    
+    Returns:
+        Warning: {what}
+          {detail}
+    """
+    return f"Warning: {what}\n  {detail}"
+
+
+def format_deprecation(old: str, new: str, since: str, removal: str) -> str:
+    """Format a deprecation message.
+    
+    Returns:
+        Deprecated: {old} is deprecated, use {new} instead.
+          Deprecated in {since}, will be removed in {removal}.
+    """
+    return (
+        f"Deprecated: `{old}` is deprecated, use `{new}` instead.\n"
+        f"  Deprecated in {since}, will be removed in {removal}."
+    )
+```
+
+These helpers are used across all commands to enforce the three-line format from Requirement 13. Existing ad-hoc error prints are migrated to use these helpers.
+
+### 3. `resolver.py` — Multi-Match Resolution
+
+**Current:** Returns first match via `ResolvedBundle`.
+
+**New:** Returns all matches, caller decides.
+
+```python
+@dataclass
+class ResolvedBundleResult:
+    """Result of resolving a bundle name across registries."""
+    matches: list[ResolvedBundle]
+    searched: list[str]
+
+
+def resolve_bundle(
+    bundle_name: str,
+    registry_index: RegistryIndex,
+) -> ResolvedBundleResult:
+    """Search all registries for a bundle by name.
+    
+    Returns ALL matches (not just the first). The caller is
+    responsible for handling ambiguity (multiple matches) or
+    not-found (zero matches).
+    """
+
+def resolve_qualified_bundle(
+    qualified_name: str,
+    registry_index: RegistryIndex,
+) -> ResolvedBundle:
+    """Resolve a qualified bundle name (registry_name/bundle_name).
+    
+    Raises BundleNotFoundError if the registry or bundle is not found.
+    """
+```
+
+**Qualified name parsing** is done in `resolve_qualified_bundle()`:
+
+```python
+def parse_qualified_name(spec: str) -> tuple[str | None, str]:
+    """Parse 'registry/bundle' or plain 'bundle'.
+    
+    Returns (registry_name, bundle_name). registry_name is None
+    for unqualified names.
+    """
+    if "/" in spec and not spec.startswith("/"):
+        parts = spec.split("/", 1)
+        return parts[0], parts[1]
+    return None, spec
+```
+
+### 4. `commands/registry_add.py` — Conflict Handling, --force, --name
+
+**Refactored `run_registry_add()`:**
+
+```python
+def run_registry_add(
+    args: argparse.Namespace,
+    *,
+    registry_index: RegistryIndex,
+    registry_index_path: Path,
+    cache_dir: Path,
+) -> int:
+    git_url: str = args.git_url
+    force: bool = getattr(args, "force", False)
+    custom_name: str | None = getattr(args, "custom_name", None)
+
+    # 1. Duplicate URL check (Req 2) — print existing name, return 0
+    for entry in registry_index.registries:
+        if entry.url == git_url:
+            print(
+                format_error(
+                    f"Registry already registered as '{entry.name}'.",
+                    f"URL: {git_url}",
+                    "Use `ksm registry list` to see registered registries.",
+                ),
+                file=sys.stderr,
+            )
+            return 0
+
+    # 2. Determine name (Req 11)
+    name = custom_name if custom_name else _derive_name(git_url)
+
+    # 3. Check custom name collision with existing registry name (Req 11.4)
+    for entry in registry_index.registries:
+        if entry.name == name:
+            print(
+                format_error(
+                    f"Registry name '{name}' is already in use.",
+                    f"Existing registry '{name}' has URL: {entry.url}",
+                    "Use `--name <custom-name>` to specify a different name.",
+                ),
+                file=sys.stderr,
+            )
+            return 1
+
+    # 4. Cache directory conflict detection (Req 1)
+    target = cache_dir / name
+    if target.exists():
+        # Check if same URL re-add (Req 1.1–1.3)
+        existing_entry = _find_entry_by_cache(target, registry_index)
+        if existing_entry and existing_entry.url == git_url:
+            if not force:
+                print(
+                    format_error(
+                        f"Cache directory already exists: {target}",
+                        f"Registry '{name}' was previously cloned here.",
+                        "Use `--force` to replace the existing cache.",
+                    ),
+                    file=sys.stderr,
+                )
+                return 1
+        elif existing_entry:
+            # Different URL owns this cache dir (Req 1.4)
+            print(
+                format_error(
+                    f"Cache directory name collision: {target}",
+                    f"Directory belongs to registry '{existing_entry.name}' ({existing_entry.url}).",
+                    "Use `--name <custom-name>` to specify a different cache directory name.",
+                ),
+                file=sys.stderr,
+            )
+            return 1
+
+        # --force: remove existing cache (Req 1.5)
+        if force:
+            shutil.rmtree(target)
+
+    # 5. Clone (Req 1.7)
+    try:
+        clone_repo(git_url, target)
+    except GitError as e:
+        if force:
+            # Rollback warning (Req 1.6)
+            print(
+                format_error(
+                    f"Clone failed: {e}",
+                    "The previous cache directory was removed.",
+                    "Re-add the registry to restore: `ksm registry add <url>`",
+                ),
+                file=sys.stderr,
+            )
+        else:
+            print(format_error(f"Clone failed", str(e), "Check the URL and try again."), file=sys.stderr)
+        return 1
+
+    # 6. Register
+    registry_index.registries.append(
+        RegistryEntry(name=name, url=git_url, local_path=str(target), is_default=False)
+    )
+    save_registry_index(registry_index, registry_index_path)
+    print(f"Registered registry '{name}' from {git_url}", file=sys.stderr)
+    return 0
+
+
+def _find_entry_by_cache(cache_path: Path, registry_index: RegistryIndex) -> RegistryEntry | None:
+    """Find a registry entry whose local_path matches the given cache path."""
+    for entry in registry_index.registries:
+        if Path(entry.local_path) == cache_path:
+            return entry
+    return None
+```
+
+### 5. `commands/registry_rm.py` — Improved Feedback
+
+**Refactored `run_registry_rm()`:**
+
+```python
+def run_registry_rm(
+    args: argparse.Namespace,
+    *,
+    registry_index: RegistryIndex,
+    registry_index_path: Path,
+) -> int:
+    name: str = args.registry_name
+
+    match = _find_registry(name, registry_index)
+    if match is None:
+        registered = [e.name for e in registry_index.registries]
+        print(
+            format_error(
+                f"Registry '{name}' not found.",
+                f"Registered registries: {', '.join(registered)}",
+                "Run `ksm registry list` to see all registries.",
+            ),
+            file=sys.stderr,
+        )
+        return 1
+
+    if match.is_default:
+        print(
+            format_error(
+                "Cannot remove the default registry.",
+                f"'{name}' is the built-in default registry.",
+                "Only user-added registries can be removed.",
+            ),
+            file=sys.stderr,
+        )
+        return 1
+
+    # Remove from index first
+    registry_index.registries = [e for e in registry_index.registries if e.name != name]
+    save_registry_index(registry_index, registry_index_path)
+
+    # Clean cache directory (Req 3.1–3.3)
+    cache_path = Path(match.local_path)
+    if cache_path.exists():
+        try:
+            shutil.rmtree(cache_path)
+            print(f"Removed registry '{name}'. Cache directory cleaned: {cache_path}", file=sys.stderr)
+        except PermissionError:
+            print(
+                format_warning(
+                    f"Could not remove cache directory: {cache_path}",
+                    "Permission denied. The registry was removed but the cache remains.",
+                ),
+                file=sys.stderr,
+            )
+    else:
+        print(f"Removed registry '{name}'. Cache directory was already absent.", file=sys.stderr)
+
+    return 0
+```
+
+### 6. `commands/add.py` — Qualified Names, --only, -i Handling
+
+**Key changes:**
+
+```python
+def run_add(args: argparse.Namespace, ...) -> int:
+    # Handle -i/--interactive vs --display deprecation (Req 5)
+    interactive = getattr(args, "interactive", False)
+    display = getattr(args, "display", False)
+    if display:
+        print(format_deprecation("--display", "-i/--interactive", "v0.2.0", "v1.0.0"), file=sys.stderr)
+        interactive = True
+
+    bundle_spec = getattr(args, "bundle_spec", None)
+
+    # If bundle_spec provided AND -i, ignore -i (Req 5.9)
+    if bundle_spec and interactive:
+        print("Warning: -i ignored because a bundle was specified.", file=sys.stderr)
+        interactive = False
+
+    # Build subdirectory filter from --only (Req 12)
+    subdirectory_filter = _build_subdirectory_filter(args)
+
+    if interactive:
+        bundle_name = _handle_display(registry_index, manifest)
+        if bundle_name is None:
+            return 0
+        bundle_spec = bundle_name
+
+    # Parse qualified name (Req 10)
+    registry_name, bundle_name = parse_qualified_name(bundle_spec)
+
+    if registry_name:
+        resolved = resolve_qualified_bundle(f"{registry_name}/{bundle_name}", registry_index)
+    else:
+        result = resolve_bundle(bundle_name, registry_index)
+        if len(result.matches) == 0:
+            raise BundleNotFoundError(bundle_name, result.searched)
+        if len(result.matches) > 1:
+            # Ambiguity error (Req 4.3–4.4)
+            registries = [m.registry_name for m in result.matches]
+            print(
+                format_error(
+                    f"Bundle '{bundle_name}' found in multiple registries.",
+                    f"Found in: {', '.join(registries)}",
+                    f"Use qualified name: ksm add <registry>/{bundle_name}",
+                ),
+                file=sys.stderr,
+            )
+            return 1
+        resolved = result.matches[0]
+    ...
+```
+
+**Refactored `_build_subdirectory_filter()`:**
+
+```python
+VALID_ONLY_VALUES = {"skills", "agents", "steering", "hooks"}
+
+def _build_subdirectory_filter(args: argparse.Namespace) -> set[str] | None:
+    """Build subdirectory filter from --only or deprecated --*-only flags."""
+    only_raw: list[str] | None = getattr(args, "only", None)
+    result: set[str] = set()
+
+    if only_raw:
+        for item in only_raw:
+            for val in item.split(","):
+                val = val.strip()
+                if val not in VALID_ONLY_VALUES:
+                    print(
+                        format_error(
+                            f"Invalid --only value: '{val}'",
+                            f"Valid values: {', '.join(sorted(VALID_ONLY_VALUES))}",
+                            "Example: --only skills,hooks",
+                        ),
+                        file=sys.stderr,
+                    )
+                    raise SystemExit(2)
+                result.add(val)
+        return result
+
+    # Deprecated --*-only flags (Req 12.7)
+    deprecated_map = {
+        "skills_only": "skills",
+        "steering_only": "steering",
+        "hooks_only": "hooks",
+        "agents_only": "agents",
+    }
+    for attr, value in deprecated_map.items():
+        if getattr(args, attr, False):
+            print(
+                format_deprecation(f"--{attr.replace('_', '-')}", f"--only {value}", "v0.2.0", "v1.0.0"),
+                file=sys.stderr,
+            )
+            result.add(value)
+
+    return result if result else None
+```
+
+### 7. `commands/add_registry.py` — Legacy Wrapper
+
+**Refactored to delegate:**
+
+```python
+def run_add_registry(
+    args: argparse.Namespace,
+    *,
+    registry_index: RegistryIndex,
+    registry_index_path: Path,
+    cache_dir: Path,
+) -> int:
+    """Legacy add-registry command. Delegates to registry_add."""
+    print(
+        format_deprecation("ksm add-registry", "ksm registry add", "v0.2.0", "v1.0.0"),
+        file=sys.stderr,
+    )
+    from ksm.commands.registry_add import run_registry_add
+    return run_registry_add(
+        args,
+        registry_index=registry_index,
+        registry_index_path=registry_index_path,
+        cache_dir=cache_dir,
+    )
+```
+
+### 8. `selector.py` — Qualified Name Display
+
+**Changes to `render_add_selector()`:**
+
+```python
+def render_add_selector(
+    bundles: list[BundleInfo],
+    installed_names: set[str],
+    selected: int,
+    filter_text: str = "",
+    multi_selected: set[int] | None = None,
+) -> list[str]:
+    # Detect ambiguous names (Req 4.1–4.2)
+    name_counts: dict[str, int] = {}
+    for b in bundles:
+        name_counts[b.name] = name_counts.get(b.name, 0) + 1
+    ambiguous_names = {n for n, c in name_counts.items() if c > 1}
+
+    # When rendering each bundle:
+    for i, bundle in enumerate(sorted_bundles):
+        if bundle.name in ambiguous_names:
+            display_name = f"{bundle.registry_name}/{bundle.name}"
+        else:
+            display_name = bundle.name
+        ...
+```
+
+### 9. `commands/registry_inspect.py` — Enhanced Output
+
+**Refactored to include URL and default status (Req 14):**
+
+```python
+def run_registry_inspect(args, *, registry_index) -> int:
+    ...
+    lines.append(bold(f"Registry: {name}"))
+    lines.append(f"  URL:     {match.url or '(local)'}")
+    lines.append(f"  Path:    {match.local_path}")
+    lines.append(f"  Default: {'yes' if match.is_default else 'no'}")
+    lines.append(f"  Bundles: {len(bundles)}")
+    lines.append("")
+
+    for bundle in bundles:
+        lines.append(f"  {bold(bundle.name)}")
+        for subdir in bundle.subdirectories:
+            subdir_path = bundle.path / subdir
+            items = sorted(p.name for p in subdir_path.iterdir() if p.is_dir() or p.is_file())
+            lines.append(f"    {subdir}/ ({len(items)} items)")
+        ...
+```
+
+### 10. `commands/rm.py` — -i/--interactive Handling
+
+Same pattern as `add.py`: check for `--display` deprecation, handle `-i` flag, ignore `-i` when `bundle_name` is provided (Req 5.10).
+
+## Data Models
+
+### Existing Models (unchanged)
+
+- `RegistryEntry(name, url, local_path, is_default)` — No changes needed.
+- `RegistryIndex(registries: list[RegistryEntry])` — No changes needed.
+- `BundleInfo(name, path, subdirectories, registry_name)` — Already has `registry_name` field.
+
+### New/Modified Models
+
+**`ResolvedBundleResult`** (new, in `resolver.py`):
+
+```python
+@dataclass
+class ResolvedBundleResult:
+    matches: list[ResolvedBundle]
+    searched: list[str]
+```
+
+This replaces the current single-return pattern. `ResolvedBundle` itself is unchanged.
+
+### Data Flow Changes
+
+```mermaid
+graph TD
+    A[CLI Parser] -->|qualified name| B[parse_qualified_name]
+    B -->|registry/bundle| C[resolve_qualified_bundle]
+    B -->|plain bundle| D[resolve_bundle]
+    D -->|ResolvedBundleResult| E{matches count}
+    E -->|0| F[BundleNotFoundError]
+    E -->|1| G[proceed with install]
+    E -->|>1| H[ambiguity error with suggestion]
+    C --> G
+```
+
+
+
+## Correctness Properties
+
+*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*
+
+### Property 1: Cache conflict same-URL error contains path and --force suggestion
+
+*For any* git URL and registry state where the cache directory already exists and belongs to the same URL, calling `run_registry_add` without `--force` should return exit code 1 and produce an error message that contains both the cache directory path and the string `--force`.
+
+**Validates: Requirements 1.1, 1.2, 1.3**
+
+### Property 2: Cache conflict different-URL error suggests --name and omits --force
+
+*For any* git URL and registry state where the cache directory already exists but belongs to a different registered registry, calling `run_registry_add` should return exit code 1 and produce an error message that contains `--name` and does NOT contain `--force`.
+
+**Validates: Requirements 1.4**
+
+### Property 3: Duplicate URL detection returns existing name and exit code 0
+
+*For any* git URL that is already registered in the registry index, calling `run_registry_add` should return exit code 0 and produce stderr output containing the name of the existing registry entry.
+
+**Validates: Requirements 2.1, 2.2**
+
+### Property 4: Registry remove feedback matches cache state
+
+*For any* registered non-default registry name, calling `run_registry_rm` should: (a) if the cache directory existed, print a message containing "Cache directory cleaned:" and the path; (b) if the cache directory was already absent, print a message containing "Cache directory was already absent"; and in both cases the registry should be removed from the index and exit code should be 0.
+
+**Validates: Requirements 3.1, 3.2**
+
+### Property 5: Registry remove not-found error lists all registered names
+
+*For any* registry name that does not exist in the registry index, calling `run_registry_rm` should return exit code 1 and produce an error message that contains every registered registry name.
+
+**Validates: Requirements 3.4**
+
+### Property 6: Selector qualifies ambiguous bundle names and leaves unique names unqualified
+
+*For any* list of BundleInfo objects where some bundle names appear in multiple registries, `render_add_selector` should render ambiguous bundles using `registry_name/bundle_name` format and render unique bundles using just the bundle name (no `/` separator).
+
+**Validates: Requirements 4.1, 4.2, 10.5, 10.6**
+
+### Property 7: Ambiguous bundle resolution error lists all registries and suggests qualified syntax
+
+*For any* bundle name that exists in two or more registries, `resolve_bundle` should return a `ResolvedBundleResult` with all matches, and the add command's ambiguity handling should produce an error containing all registry names and the `<registry>/<bundle>` suggestion syntax.
+
+**Validates: Requirements 4.3, 4.4, 4.6**
+
+### Property 8: Qualified name round-trip parsing
+
+*For any* valid registry name (non-empty, no `/`) and valid bundle name (non-empty, no `/`), `parse_qualified_name(f"{registry_name}/{bundle_name}")` should return `(registry_name, bundle_name)`. For any plain bundle name (no `/`), `parse_qualified_name(bundle_name)` should return `(None, bundle_name)`.
+
+**Validates: Requirements 10.2**
+
+### Property 9: Full-word and short command aliases produce identical dispatch
+
+*For any* valid argument list, parsing with the full-word command (`list`, `remove`) and the short alias (`ls`, `rm`) should dispatch to the same handler function.
+
+**Validates: Requirements 9.5, 9.6**
+
+### Property 10: _derive_name produces consistent URL-derived names
+
+*For any* git URL string, `_derive_name` should return a non-empty string with `.git` suffix stripped and trailing slashes removed. Calling it twice on the same URL should return the same result.
+
+**Validates: Requirements 11.3**
+
+### Property 11: --only comma-separated parsing produces correct filter set
+
+*For any* comma-separated string composed of valid values from {skills, agents, steering, hooks}, `_build_subdirectory_filter` should produce a set containing exactly those values.
+
+**Validates: Requirements 12.2**
+
+### Property 12: --only rejects invalid values with exit code 2
+
+*For any* string that is not in {skills, agents, steering, hooks}, providing it as an `--only` value should cause `_build_subdirectory_filter` to raise `SystemExit(2)` and produce an error message listing all valid values.
+
+**Validates: Requirements 12.5**
+
+### Property 13: Deprecated --*-only flags produce deprecation warning and equivalent filter
+
+*For any* old-style flag (`--skills-only`, `--agents-only`, `--steering-only`, `--hooks-only`), `_build_subdirectory_filter` should produce the same filter set as the equivalent `--only` value and emit a deprecation warning to stderr.
+
+**Validates: Requirements 12.7**
+
+### Property 14: Message formatters produce correctly prefixed output
+
+*For any* non-empty input strings, `format_error(what, why, fix)` should produce output starting with `Error: ` and containing three lines; `format_warning(what, detail)` should start with `Warning: `; `format_deprecation(old, new, since, removal)` should start with `Deprecated: ` and contain both version strings.
+
+**Validates: Requirements 13.1, 13.3, 13.4, 13.5**
+
+### Property 15: Registry inspect output contains all required fields and bundles
+
+*For any* registered registry with bundles, `run_registry_inspect` output should contain the registry name, URL (or "(local)"), local cache path, default status, and every bundle name with its subdirectory types.
+
+**Validates: Requirements 14.1, 14.2, 14.4**
+
+### Property 16: Cache directory uses registry name as namespace
+
+*For any* registry name (whether derived or custom), the cache directory path should be `cache_dir / name`, ensuring different registry names produce different cache paths.
+
+**Validates: Requirements 1.8**
+
+## Error Handling
+
+### Standardised Error Format (Requirement 13)
+
+All error output uses the three helpers in `errors.py`:
+
+| Scenario | Helper | Example |
+|---|---|---|
+| Cache conflict (same URL) | `format_error` | `Error: Cache directory already exists: /path\n  Registry 'x' was previously cloned here.\n  Use --force to replace the existing cache.` |
+| Cache conflict (different URL) | `format_error` | `Error: Cache directory name collision: /path\n  Directory belongs to registry 'y' (url).\n  Use --name <custom-name> to specify a different cache directory name.` |
+| Clone failure after --force | `format_error` | `Error: Clone failed: ...\n  The previous cache directory was removed.\n  Re-add the registry to restore: ksm registry add <url>` |
+| Duplicate URL | `format_error` | `Error: Registry already registered as 'name'.\n  URL: ...\n  Use ksm registry list to see registered registries.` |
+| Registry not found | `format_error` | `Error: Registry 'x' not found.\n  Registered registries: a, b, c\n  Run ksm registry list to see all registries.` |
+| Ambiguous bundle | `format_error` | `Error: Bundle 'x' found in multiple registries.\n  Found in: a, b\n  Use qualified name: ksm add <registry>/x` |
+| Permission error on cache removal | `format_warning` | `Warning: Could not remove cache directory: /path\n  Permission denied. The registry was removed but the cache remains.` |
+| --display used | `format_deprecation` | `Deprecated: --display is deprecated, use -i/--interactive instead.\n  Deprecated in v0.2.0, will be removed in v1.0.0.` |
+| --*-only used | `format_deprecation` | `Deprecated: --skills-only is deprecated, use --only skills instead.\n  Deprecated in v0.2.0, will be removed in v1.0.0.` |
+| add-registry used | `format_deprecation` | `Deprecated: ksm add-registry is deprecated, use ksm registry add instead.\n  Deprecated in v0.2.0, will be removed in v1.0.0.` |
+| Invalid --only value | `format_error` | `Error: Invalid --only value: 'foo'\n  Valid values: agents, hooks, skills, steering\n  Example: --only skills,hooks` |
+
+### Exit Codes
+
+| Code | Meaning |
+|---|---|
+| 0 | Success (including duplicate URL detection — idempotent) |
+| 1 | Operational error (conflict, not found, clone failure) |
+| 2 | Usage error (invalid flag value, missing subcommand) |
+
+## Testing Strategy
+
+### Property-Based Testing
+
+- **Library:** [Hypothesis](https://hypothesis.readthedocs.io/) (already in use in the project, as evidenced by `.hypothesis/` directory)
+- **Configuration:** Use Hypothesis profiles — `dev` profile with 15 examples for local development, `ci` profile with 100 examples for CI
+- **Each property test** references its design property with a comment tag: `# Feature: ksm-enhancements, Property N: <title>`
+- **Each correctness property** maps to exactly one property-based test function
+
+### Property Test Coverage
+
+| Property | Test Target | Strategy |
+|---|---|---|
+| 1: Cache conflict same-URL | `run_registry_add` | Generate random URLs + pre-existing cache dirs, verify error message content |
+| 2: Cache conflict different-URL | `run_registry_add` | Generate states with mismatched cache ownership, verify --name suggestion |
+| 3: Duplicate URL detection | `run_registry_add` | Generate registry states with duplicate URLs, verify name in output + exit 0 |
+| 4: Remove feedback | `run_registry_rm` | Generate registries with/without cache dirs, verify message format |
+| 5: Remove not-found | `run_registry_rm` | Generate registry states + non-existent names, verify all names in error |
+| 6: Selector qualification | `render_add_selector` | Generate bundle lists with duplicate/unique names, verify display format |
+| 7: Ambiguous resolution | `resolve_bundle` + add command | Generate multi-registry states with same bundle name |
+| 8: Qualified name parsing | `parse_qualified_name` | Generate random name pairs, verify round-trip |
+| 9: Alias dispatch | `_build_parser` | Parse both alias forms, verify same dispatch target |
+| 10: _derive_name | `_derive_name` | Generate random URL strings, verify idempotence and .git stripping |
+| 11: --only parsing | `_build_subdirectory_filter` | Generate valid comma-separated combinations |
+| 12: --only rejection | `_build_subdirectory_filter` | Generate invalid strings, verify SystemExit(2) |
+| 13: Deprecated flags | `_build_subdirectory_filter` | Generate old-style flag combinations, verify equivalence |
+| 14: Message formatters | `format_error`, `format_warning`, `format_deprecation` | Generate random strings, verify prefix and structure |
+| 15: Inspect output | `run_registry_inspect` | Generate registry entries with bundles, verify field presence |
+| 16: Cache namespace | cache path construction | Generate random names, verify path structure |
+
+### Unit Test Coverage
+
+Unit tests complement property tests for specific examples, edge cases, and integration points:
+
+- **CLI parser tests:** Verify each subcommand parses correctly, aliases work, help text shows/hides expected flags
+- **Deprecation examples:** `--display` prints warning, `add-registry` prints warning with version numbers
+- **Edge cases:** Empty registry index, permission errors on cache removal, clone failure after --force
+- **Integration:** End-to-end flow for `registry add` with --force, `registry remove` with feedback messages
+- **Selector rendering:** Specific examples of ambiguous vs unique bundle display
+
+### Test Organisation
+
+Tests mirror the source structure under `tests/`:
+
+```
+tests/
+  test_cli.py              — parser construction, alias dispatch, help text
+  test_errors.py           — format_error, format_warning, format_deprecation
+  test_resolver.py         — resolve_bundle multi-match, parse_qualified_name
+  test_selector.py         — render_add_selector with ambiguous names
+  commands/
+    test_registry_add.py   — conflict handling, --force, --name, duplicate URL
+    test_registry_rm.py    — feedback messages, not-found error
+    test_registry_inspect.py — output format, field presence
+    test_add.py            — -i handling, --only parsing, qualified names
+    test_rm.py             — -i handling, deprecation warnings
+    test_add_registry.py   — legacy wrapper deprecation
+```
