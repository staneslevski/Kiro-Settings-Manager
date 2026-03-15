# MCP Availability

## MCP Servers

- **GitHub** (`github`) — Read-only access to repos, issues, PRs, code search, commits, branches, and releases.
- **AWS Documentation** (`awslabs.aws-documentation-mcp-server`) — Search and read official AWS docs. Prefer over general knowledge for AWS topics.
- **AWS Knowledge** (`aws-knowledge-mcp-server`) — Check regional availability of AWS services/APIs/CFN resources. Topic-based doc search.
- **AWS API** (`awslabs.aws-api-mcp-server`) — Execute AWS CLI commands. Read-only by default; mutations require consent.
- **AWS IaC** (`awslabs.aws-iac-mcp-server`) — Validate CFN templates (syntax, compliance), troubleshoot failed deployments, search CDK/CFN docs and samples.

## Powers

- **Terraform** (`terraform`) — Look up registry providers, modules, policies. Must activate before use.

## Quick Reference

| Task | Use |
|------|-----|
| AWS service docs | AWS Documentation / AWS Knowledge |
| Regional availability | AWS Knowledge |
| Run AWS CLI commands | AWS API |
| Validate/troubleshoot CFN | AWS IaC |
| CDK code/docs | AWS IaC |
| GitHub repos/PRs/issues | GitHub |
| Terraform providers/modules | Terraform power |
