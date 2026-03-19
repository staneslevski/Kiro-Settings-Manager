---
name: aws-cross-account
description: >
  Enables the agent to query AWS resources in other accounts within the same
  AWS Organization. Use when the user asks to read, list, describe, or inspect
  resources in a specific AWS account that is not the management account. The
  agent assumes a cross-account IAM role via a temporary shell script, then
  reports the results. Do not use for mutating resources in other accounts or
  for queries that only target the management account.
compatibility: >
  Requires the AWS CLI v2 installed and configured with credentials that can
  call sts:AssumeRole. Requires python3 (used to parse JSON credentials).
metadata:
  author: user
  version: 1.0.0
  tags: [aws, cross-account, organizations, assume-role, iam]
---

## Purpose

- Query AWS resources in member accounts of an AWS Organization.
- Bridge the gap where the MCP AWS API server only has credentials for the
  management account and cannot natively use assumed-role sessions.
- Provide a repeatable, auditable workflow: generate a script, get user
  approval, execute, then report findings.

## Prerequisites

- The agent's default credentials (via MCP) must have `sts:AssumeRole`
  permission on the target role ARN.
- The target account must contain an IAM role whose trust policy allows the
  agent's principal to assume it.
- The default cross-account read role is named `AccountReadOnly`. If the
  user specifies a different role name, use that instead.

## Workflow

### 1. Identify the target account

1. Use the MCP AWS API tool to list all accounts in the organization:
   `aws organizations list-accounts`
2. Present the account list to the user if they have not specified an
   account by name or ID.
3. Confirm the target account ID and name before proceeding.

### 2. Confirm the role

1. You must only ever assume the `AccountReadOnly` role. Never assume
   any other role, even if the user requests it.
2. Build the role ARN: `arn:aws:iam::<account-id>:role/AccountReadOnly`

### 3. Test the assume-role

1. Use the MCP AWS API tool to call:
   `aws sts assume-role --role-arn <arn> --role-session-name kiro-session`
2. If this succeeds, proceed to script generation.
3. If this fails with AccessDenied, explain the two-sided permission
   requirement to the user:
   - The role's trust policy must allow the agent's principal.
   - The agent's IAM user/role must have an `sts:AssumeRole` policy for
     the target role ARN.
4. Ask the user to fix permissions and retry before continuing.

### 4. Generate the query script

1. Create a shell script at `scripts/tmp/<descriptive-name>.sh`.
2. The script must follow this structure:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROLE_ARN="arn:aws:iam::<account-id>:role/<role-name>"
SESSION_NAME="kiro-<context>"
REGION="ap-northeast-1"  # Default region; only change if user specifies another

# Assume role and export temporary credentials
CREDS=$(aws sts assume-role \
  --role-arn "$ROLE_ARN" \
  --role-session-name "$SESSION_NAME" \
  --output json)

export AWS_ACCESS_KEY_ID=$(echo "$CREDS" | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['Credentials']['AccessKeyId'])")
export AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['Credentials']['SecretAccessKey'])")
export AWS_SESSION_TOKEN=$(echo "$CREDS" | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['Credentials']['SessionToken'])")

# --- Queries go here ---
aws <service> <operation> --region "$REGION" --output json
```

3. Only include read-only AWS CLI commands (list, describe, get, scan).
   Never include commands that create, update, or delete resources.
4. Default the region to `ap-northeast-1`. Only use a different region
   if the user explicitly states one.
4. Make the script executable with `chmod +x`.

### 5. Get user approval

1. Tell the user what the script will do and which account/region it
   targets.
2. Ask for explicit permission before executing.
3. Do not execute the script without user confirmation.

### 6. Execute and report

1. Run the script: `bash scripts/tmp/<script-name>.sh`
2. Parse the JSON output and present a clear, readable summary to the
   user (tables, bullet points, or prose as appropriate).
3. If the script fails, read the error output and help the user
   troubleshoot (expired credentials, missing permissions, wrong region).

### 7. Clean up

1. Leave the script in `scripts/tmp/` for future reference or re-runs.
2. If the user asks to clean up, delete the script.
3. Do not commit scripts in `scripts/tmp/` to version control.

## Constraints

- All cross-account operations must be read-only. Never generate scripts
  that mutate resources in other accounts.
- Always ask for user permission before executing a generated script.
- Temporary credentials expire after 1 hour by default. If a session has
  expired, re-run the script (it fetches fresh credentials each time).
- The `scripts/tmp/` directory is for ephemeral scripts only. Do not
  place permanent automation there.
- If the user needs to query multiple accounts, generate one script per
  account or a single script that loops through accounts with clear
  output separation.

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| AccessDenied on AssumeRole | Missing permission on either side | Check both the role trust policy and the caller's IAM policy |
| ExpiredToken | Session credentials timed out | Re-run the script to get fresh credentials |
| Empty results | Wrong region | Ask the user which region the resources are in |
| No such role | Role does not exist in target account | Verify the role name and account ID |
