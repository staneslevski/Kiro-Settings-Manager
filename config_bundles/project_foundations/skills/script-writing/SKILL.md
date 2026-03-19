---
name: script-writing
description: >
  Guides the creation of shell scripts that follow consistent naming, structure,
  and output conventions. Use when the user asks to write, create, or generate
  a shell script or bash script. Do not use for Python scripts, Node.js scripts,
  or non-shell automation.
metadata:
  author: your-name-here
  version: 1.0.0
  tags: [scripts, bash, shell, automation]
---

# Script Writing Standards

## File naming

1. Name every script with a descriptive, kebab-case name that communicates the task it performs (e.g. `deploy-staging-stack.sh`, `rotate-api-keys.sh`).
2. Always use the `.sh` extension.
3. Place scripts in the `scripts/` directory unless the user specifies otherwise.

## Script structure

Every script must follow this template:

```bash
#!/bin/bash

# Description: <one-line summary of what this script does>
# Usage: ./<script-name>.sh [arguments]

set -euo pipefail

# --- Configuration ---
# Define variables and defaults here

# --- Functions ---
# Define helper functions here

# --- Main ---
# Core logic here

echo "✓ <success message describing what completed>"
```

### Required elements

1. Start with `#!/bin/bash` shebang.
2. Include a comment block with a description and usage example.
3. Use `set -euo pipefail` for safe error handling.
4. Group code into configuration, functions, and main sections.
5. End successful execution with a clear success message prefixed with `✓`.

## User feedback

1. Print a `✓` prefixed message on success describing what was accomplished.
2. Print a `✗` prefixed error message on failure describing what went wrong.
3. Exit with a non-zero code on failure (`exit 1`).
4. For multi-step scripts, print progress messages so the user can follow along.

Example error handling pattern:

```bash
if [ $? -eq 0 ]; then
    echo "✓ Files copied successfully to $DEST_DIR"
else
    echo "✗ Error: failed to copy files to $DEST_DIR"
    exit 1
fi
```

## Size limit

1. Scripts must not exceed 100 lines.
2. If a script would exceed 100 lines, do not write it as a single file. Instead:
   - Explain to the user why the script is too complex for a single file.
   - Recommend ways to reduce complexity (remove duplication, simplify logic, reduce scope).
   - Propose breaking it into smaller, focused scripts that can be called independently or composed together.
   - Each sub-script must also follow these same standards.

## Additional conventions

1. Quote all variable expansions (`"$VAR"` not `$VAR`).
2. Use `[[ ]]` for conditionals instead of `[ ]`.
3. Validate required inputs early and exit with a helpful message if missing.
4. Make scripts executable after creation (`chmod +x`).
