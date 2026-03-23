#!/bin/bash
#
# publish-to-pypi.sh — Build and publish kiro-settings-manager to PyPI
#
# Usage:
#   ./scripts/publish-to-pypi.sh              # publish to real PyPI
#   ./scripts/publish-to-pypi.sh --test       # publish to TestPyPI
#
# Prerequisites:
#   - PyPI account with API token (https://pypi.org/manage/account/token/)
#   - For TestPyPI: separate account at https://test.pypi.org
#   - Credentials in ~/.pypirc or entered interactively
#
# Exit codes:
#   0 — published successfully
#   1 — build or upload failed
#   2 — script misconfiguration (missing venv, tools, etc.)

set -euo pipefail

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
VENV_DIR=".venv"
DIST_DIR="dist"

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
info()  { echo "ℹ  $*"; }
ok()    { echo "✓  $*"; }
fail()  { echo "✗  $*" >&2; }

# -------------------------------------------------------------------
# Parse arguments
# -------------------------------------------------------------------
REPOSITORY="pypi"
TWINE_ARGS=()

if [[ "${1:-}" == "--test" ]]; then
    REPOSITORY="testpypi"
    TWINE_ARGS+=("--repository" "testpypi")
    info "Publishing to TestPyPI"
else
    info "Publishing to PyPI"
fi

# -------------------------------------------------------------------
# Pre-flight checks
# -------------------------------------------------------------------
if [ ! -d "$VENV_DIR" ]; then
    fail "Virtual environment not found at $VENV_DIR"
    fail "Create one first: python3.13 -m venv $VENV_DIR"
    exit 2
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

for cmd in python twine; do
    if ! command -v "$cmd" &>/dev/null; then
        fail "$cmd is not installed in the virtual environment"
        fail "Install it: source $VENV_DIR/bin/activate && pip install -e \".[dev]\""
        exit 2
    fi
done

# -------------------------------------------------------------------
# Clean previous builds
# -------------------------------------------------------------------
if [ -d "$DIST_DIR" ]; then
    info "Cleaning previous build artifacts"
    rm -rf "$DIST_DIR"
fi

# -------------------------------------------------------------------
# Build
# -------------------------------------------------------------------
info "Building distribution"
python -m build

if [ ! -d "$DIST_DIR" ] || [ -z "$(ls -A "$DIST_DIR")" ]; then
    fail "Build produced no artifacts in $DIST_DIR"
    exit 1
fi

ok "Build complete"
ls -lh "$DIST_DIR"/

# -------------------------------------------------------------------
# Upload
# -------------------------------------------------------------------
info "Uploading to $REPOSITORY"
twine upload "${TWINE_ARGS[@]}" "$DIST_DIR"/*

ok "Published to $REPOSITORY successfully"

if [[ "$REPOSITORY" == "testpypi" ]]; then
    info "Test install with:"
    info "  pip install --index-url https://test.pypi.org/simple/ kiro-settings-manager"
else
    info "Install with:"
    info "  pip install kiro-settings-manager"
fi
