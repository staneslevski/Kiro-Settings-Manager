#!/bin/bash

# Update allowed commands for Kiro
# Reads trusted commands from Kiro settings and writes to allowed_commands.txt

KIRO_SETTINGS="$HOME/Library/Application Support/Kiro/User/settings.json"
COMMANDS_FILE="settings/allowed_commands.txt"

if [ ! -f "$KIRO_SETTINGS" ]; then
    echo "Error: Kiro settings file not found at $KIRO_SETTINGS"
    exit 1
fi

# Extract trusted commands from settings.json and write to file
grep -A 100 '"kiroAgent.trustedCommands"' "$KIRO_SETTINGS" | \
    grep -E '^\s*"[^"]+",?\s*$' | \
    sed 's/^[[:space:]]*"//; s/"[[:space:]]*,*[[:space:]]*$//' | \
    grep -v '^$' > "$COMMANDS_FILE"

if [ -s "$COMMANDS_FILE" ]; then
    echo "✓ Updated $COMMANDS_FILE with $(wc -l < "$COMMANDS_FILE" | tr -d ' ') commands"
else
    echo "Warning: No commands found or file is empty"
    exit 1
fi
