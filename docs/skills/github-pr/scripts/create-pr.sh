#!/bin/bash

# Description: Create a GitHub pull request using the gh CLI
# Usage: ./create-pr.sh --title "PR title" --body "PR body" [--base main] [--draft] [--label "label1,label2"]

set -euo pipefail

# --- Configuration ---
TITLE=""
BODY=""
BASE="main"
DRAFT=false
LABELS=""

# --- Functions ---
usage() {
    echo "Usage: $0 --title <title> --body <body> [--base <branch>] [--draft] [--label <labels>]"
    echo ""
    echo "Options:"
    echo "  --title   PR title (required)"
    echo "  --body    PR body in markdown (required)"
    echo "  --base    Base branch to merge into (default: main)"
    echo "  --draft   Create as draft PR"
    echo "  --label   Comma-separated labels to apply"
    exit 1
}

check_prerequisites() {
    if ! command -v gh &> /dev/null; then
        echo "✗ Error: gh CLI is not installed. Install it from https://cli.github.com/"
        exit 1
    fi

    if ! gh auth status &> /dev/null; then
        echo "✗ Error: gh CLI is not authenticated. Run 'gh auth login' first."
        exit 1
    fi

    if ! git rev-parse --is-inside-work-tree &> /dev/null; then
        echo "✗ Error: not inside a git repository."
        exit 1
    fi
}

get_current_branch() {
    git branch --show-current
}

# --- Main ---
if [[ $# -eq 0 ]]; then
    usage
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --title)
            TITLE="$2"
            shift 2
            ;;
        --body)
            BODY="$2"
            shift 2
            ;;
        --base)
            BASE="$2"
            shift 2
            ;;
        --draft)
            DRAFT=true
            shift
            ;;
        --label)
            LABELS="$2"
            shift 2
            ;;
        *)
            echo "✗ Error: unknown option '$1'"
            usage
            ;;
    esac
done

if [[ -z "$TITLE" ]]; then
    echo "✗ Error: --title is required"
    usage
fi

if [[ -z "$BODY" ]]; then
    echo "✗ Error: --body is required"
    usage
fi

check_prerequisites

CURRENT_BRANCH=$(get_current_branch)

if [[ "$CURRENT_BRANCH" == "$BASE" ]]; then
    echo "✗ Error: current branch '$CURRENT_BRANCH' is the same as base branch '$BASE'. Switch to a feature branch first."
    exit 1
fi

echo "Creating PR: '$TITLE'"
echo "  From: $CURRENT_BRANCH → $BASE"

# Build the gh command
CMD=(gh pr create --title "$TITLE" --body "$BODY" --base "$BASE")

if [[ "$DRAFT" == true ]]; then
    CMD+=(--draft)
fi

if [[ -n "$LABELS" ]]; then
    IFS=',' read -ra LABEL_ARRAY <<< "$LABELS"
    for label in "${LABEL_ARRAY[@]}"; do
        CMD+=(--label "$label")
    done
fi

# Execute
"${CMD[@]}"

echo "✓ Pull request created successfully from '$CURRENT_BRANCH' into '$BASE'"
