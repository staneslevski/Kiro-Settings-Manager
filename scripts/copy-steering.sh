#!/bin/bash

# Script to copy steering files to Kiro's global steering directory

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source directory (relative to script location)
SOURCE_DIR="$SCRIPT_DIR/../docs/steering"

# Destination directory
DEST_DIR="$HOME/.kiro/steering"

# Create destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Copy all files from source to destination
echo "Copying steering files from $SOURCE_DIR to $DEST_DIR..."
cp -r "$SOURCE_DIR"/* "$DEST_DIR/"

# Check if copy was successful
if [ $? -eq 0 ]; then
    echo "✓ Steering files copied successfully!"
    echo "Files copied to: $DEST_DIR"
else
    echo "✗ Error copying steering files"
    exit 1
fi
