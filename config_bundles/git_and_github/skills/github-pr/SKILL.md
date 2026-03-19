---
name: github-pr
description: >
  Guides the agent through creating a GitHub pull request. Use when the user
  asks to create a PR, open a pull request, submit changes for review, or
  push a branch and open a PR. The agent has read-only GitHub MCP access so
  it must use the bundled gh CLI script to create the PR. Do not use for
  reviewing, merging, or closing existing pull requests.
compatibility: >
  Requires the gh CLI (https://cli.github.com/) installed and authenticated.
  Requires git.
metadata:
  author: user
  version: 1.0.0
  tags: [github, pull-request, pr, git, review]
---

## Purpose

- Create GitHub pull requests from the current feature branch.
- Gather context (commits, diff, related issues) using the GitHub MCP read tools to build a well-structured PR title and body.
- Execute the PR creation via the bundled `scripts/create-pr.sh` script since the agent does not have write access through the GitHub MCP.

## Prerequisites

The `gh` CLI must be installed and authenticated. If the script reports that `gh` is missing or not authenticated, instruct the user to:

1. Install: `brew install gh` (macOS) or see https://cli.github.com/
2. Authenticate: `gh auth login`

## Workflow

### 1. Validate the branch

1. Check the current git branch. If on `main`, stop and ask the user which branch to work from or whether to create one.
2. Confirm there are commits on the branch that are not on the base branch. Run: `git log main..HEAD --oneline`
3. Check for uncommitted changes with `git status`. If there are uncommitted changes, ask the user whether to commit them first.

### 2. Gather context

1. Use `git log main..HEAD --oneline` to list the commits being proposed.
2. Use `git diff main...HEAD --stat` to summarise which files changed.
3. If the user mentions an issue number, use the GitHub MCP `mcp_github_issue_read` tool to fetch the issue title and body for context.
4. If the repository already has open PRs, optionally use `mcp_github_list_pull_requests` to check for duplicates targeting the same branch.

### 3. Compose the PR

Build a title and markdown body following this structure:

```
## Summary
<2-3 sentence overview of what this PR does>

## Changes
- <bullet list of key changes, derived from commits and diff>

## Related Issues
- Closes #<number> (if applicable)

## Testing
- <describe how the changes were tested, or note if tests are included>
```

Rules:
- Keep the title under 72 characters.
- Use imperative mood in the title (e.g. "Add login endpoint" not "Added login endpoint").
- Reference issue numbers with `Closes #N` or `Relates to #N` in the body.
- If the user provides a title or body, use their text. Only auto-generate when the user has not specified.

### 4. Push and create the PR

1. Ensure the branch is pushed to the remote. Run: `git push -u origin <branch-name>`
2. Locate the script. Check these paths in order and use the first that exists:
   - `~/.kiro/skills/github-pr/scripts/create-pr.sh` (global install)
   - `docs/skills/github-pr/scripts/create-pr.sh` (staging copy in repo)
3. Execute the script to create the PR:

```bash
<path-to-script>/create-pr.sh \
  --title "<title>" \
  --body "<body>" \
  --base main
```

Optional flags:
- Add `--draft` if the user asks for a draft PR.
- Add `--label "label1,label2"` if the user specifies labels.

4. If the script fails, read the error output and report it to the user with remediation steps.

### 5. Confirm and clean up

1. After successful creation, report the PR URL to the user (the `gh` CLI prints it).
2. Store the current branch name: `git branch --show-current`
3. Switch back to the main branch: `git checkout main`
4. Delete the old working branch locally: `git branch -D <branch-name>`
5. Offer to open the PR in the browser if needed: `gh pr view --web`

## Script reference

The PR creation script is at `scripts/create-pr.sh` within this skill folder. It wraps `gh pr create` with input validation and error handling. Run with `--help` or see the script source for full usage.

## Constraints

- The agent has read-only access to GitHub via MCP. All write operations (creating PRs) must go through the `gh` CLI script.
- Never attempt to use MCP tools to create or modify pull requests.
- Never commit directly to `main`. Always work from a feature branch.
