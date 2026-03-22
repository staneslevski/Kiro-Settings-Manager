---
name: aws-environment-explorer
description: >
  Enables the agent to inspect, review, and explore AWS resources across any
  account in the user's AWS Organization. Use when the user asks to look at
  what is deployed, review infrastructure, describe resources, check
  configurations, or understand the state of any AWS environment. The agent
  obtains short-term read-only credentials via the Tempura MCP server and
  queries accounts using the AWS API.
compatibility: >
  Requires the Tempura MCP server and the AWS API MCP server to be configured
  in the Kiro IDE.
metadata:
  author: user
  version: 2.0.0
  tags: [aws, cross-account, organizations, read-only, tempura, mcp]
---

## Purpose

Read and understand AWS environments across an AWS Organization. The Tempura
MCP server provides short-term read-only credentials for any account. Once
you have credentials, use the AWS API MCP server to inspect resources in
that account.

## How It Works

1. The Tempura MCP server has a single tool: `get_credentials`. Call it
   with an `account_id` and it writes temporary read-only credentials to
   the `[TargetReadOnly]` profile in `~/.aws/credentials`.
2. After obtaining credentials, use the AWS API MCP server with
   `--profile TargetReadOnly` to run read-only AWS CLI commands against
   that account.
3. Credentials are short-lived. If they expire, call `get_credentials`
   again for the same account.

## When to Activate This Skill

- User asks to look at, review, inspect, or describe resources in an AWS
  account.
- User asks what is deployed in an environment.
- User provides an AWS account ID and wants to understand what is in it.
- User asks to compare resources across accounts.
- User asks about the structure of their AWS Organization.

## Workflow

### 1. Identify the target account

- If the user provides an account ID, use it directly.
- If the user is unsure which account to look at, get credentials for
  the management account (`737317631059`) and query AWS Organizations:
  ```
  aws organizations list-accounts --profile TargetReadOnly
  ```
- Present the account list and let the user choose.

### 2. Get credentials

Call the Tempura MCP tool:

```
get_credentials(account_id="<target-account-id>")
```

This writes temporary read-only credentials to the `[TargetReadOnly]`
AWS CLI profile.

### 3. Query the environment

Use the AWS API MCP server to run read-only commands with
`--profile TargetReadOnly`. Examples:

```
aws s3 ls --profile TargetReadOnly
aws ec2 describe-instances --region ap-northeast-1 --profile TargetReadOnly
aws lambda list-functions --region ap-northeast-1 --profile TargetReadOnly
```

Default region is `ap-northeast-1` unless the user specifies otherwise.

### 4. Follow the trail

If something in one account points to another account (e.g. a
cross-account role, a shared resource, a peering connection), call
`get_credentials` for that second account and continue investigating.
You can switch between accounts as many times as needed.

### 5. Report findings

Summarise what you found in a clear, readable format. Use tables, bullet
points, or prose as appropriate for the content.

## Constraints

- All operations are read-only. Never attempt to create, update, or
  delete resources in any account.
- Credentials are scoped to the `AccountReadOnly` role. You cannot
  escalate beyond read permissions.
- If credentials expire mid-investigation, call `get_credentials` again.
