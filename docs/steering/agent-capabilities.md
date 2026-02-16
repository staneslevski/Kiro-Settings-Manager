---
inclusion: always
---

# Agent Capabilities

## Built-in File Tools (Use These, Not Bash)

- `readFile` / `readMultipleFiles` - Read files
- `fsWrite` - Create/overwrite files (auto-creates directories)
- `fsAppend` - Append content
- `strReplace` - Edit text precisely
- `deleteFile` - Delete files
- `grepSearch` / `fileSearch` - Search files

## Never Use These Bash Commands

❌ `cat` → Use `readFile`
❌ `sed` → Use `strReplace`
❌ `echo >>` → Use `fsAppend`
❌ `echo >` → Use `fsWrite`
❌ `grep` → Use `grepSearch`
❌ `find` → Use `fileSearch`
❌ `mkdir` → Auto-created by `fsWrite`
❌ `cp` → Use `readFile` + `fsWrite`

## Commands You Can Execute

✅ (not an exhaustive list) `python`, `pytest`, `pip`, `git`, `aws`, `cfn-lint`, bash scripts in `scripts/`