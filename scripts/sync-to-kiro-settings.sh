#!/bin/bash

# Sync allowed commands to Kiro settings
# Ensures all commands in allowed_commands.txt are in Kiro's settings.json

COMMANDS_FILE="settings/allowed_commands.txt"
KIRO_SETTINGS="$HOME/Library/Application Support/Kiro/User/settings.json"
BACKUP_FILE="$KIRO_SETTINGS.backup.$(date +%Y%m%d_%H%M%S)"

if [ ! -f "$COMMANDS_FILE" ]; then
    echo "Error: $COMMANDS_FILE not found"
    exit 1
fi

if [ ! -f "$KIRO_SETTINGS" ]; then
    echo "Error: Kiro settings file not found at $KIRO_SETTINGS"
    exit 1
fi

# Backup settings
cp "$KIRO_SETTINGS" "$BACKUP_FILE"
echo "✓ Backed up settings to $BACKUP_FILE"

# Read commands from file and build JSON array
commands_json=$(while IFS= read -r cmd || [ -n "$cmd" ]; do
    [ -z "$cmd" ] && continue
    echo "\"$cmd\""
done < "$COMMANDS_FILE" | paste -sd ',' -)

# Use Python to merge commands into settings.json
python3 << EOF
import json
import sys

with open("$KIRO_SETTINGS", "r") as f:
    settings = json.load(f)

new_commands = [$commands_json]
existing = settings.get("kiroAgent.trustedCommands", [])

# Merge: keep existing + add new (deduplicate)
merged = list(dict.fromkeys(existing + new_commands))
settings["kiroAgent.trustedCommands"] = merged

with open("$KIRO_SETTINGS", "w") as f:
    json.dump(settings, f, indent=4)

added = len(merged) - len(existing)
print(f"✓ Synced commands: {len(merged)} total ({added} added)")
EOF

if [ $? -eq 0 ]; then
    echo "✓ Successfully updated Kiro settings"
else
    echo "Error: Failed to update settings, restoring backup"
    cp "$BACKUP_FILE" "$KIRO_SETTINGS"
    exit 1
fi
