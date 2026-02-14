# Python Standards

## Virtual Environment

### NON-NEGOTIABLE
1. ALL Python work MUST be completed in a virtual environment
2. Virtual environment MUST be named `.venv` in project root
3. NEVER install packages globally or outside the virtual environment

### Setup Process
1. Create virtual environment: `python -m venv .venv`
2. Activate before any work:
   - macOS/Linux: `source .venv/bin/activate`
   - Windows: `.venv\Scripts\activate`
3. Install dependencies within activated environment
4. Verify activation before running commands

### Requirements
- Always check if `.venv` exists before creating
- Include `.venv/` in `.gitignore`
- Document dependencies in `requirements.txt` or `pyproject.toml`
- All pip installs, script runs, and tests must use the virtual environment
