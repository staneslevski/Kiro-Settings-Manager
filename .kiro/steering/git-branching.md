---
inclusion: always
---

# Git Branching

## Rules

1. Never commit directly to `main`.
2. The default branch is always called `main`.
3. All work must be done on a separate branch and merged via pull request.
4. Branch names must follow the format: `<type>/<short-description>` where type is one of:
   - `feature/` — new functionality
   - `bugfix/` — fixing a bug
   - `chore/` — maintenance or non-functional changes

5. Always commit changes instead of stashing them unless that would create merge conflicts. 

## Before Starting Work

- Check if there are open pull requests
- check if there are any branches which do not have an open pull request
- If a branch has no open pull requests, check if it has and commits which are ahead of main.
- if a branch has any changes which are ahead of main and there is no open pull request, make a pull request for that branch and tell the user to review and approve it before starting work. 
- Always pull the latest changes from remote before creating a new branch: `git pull origin main`.
- If on `main`, create and switch to a new branch before making any changes.
- If not on main, ask the user if you need to use a new branch
- If a branch does not match the naming convention, rename it before pushing.

DO NOT JUST STASH ALL YOUR CHANGES. If you do this it will just mean that we forget about work and lose it. You need to make sure it gets recorded and merged back to main.

check all local branches for uncommitted changes and commit them. 



You should only have the main branch (which you should not commit to) and a single working branch. If you have more than one working branch, you should merge your changes into a single branch and then work on that.