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

### Typing
- Always define types in the input and output of functions
- When testing, always check that types are respected and throw an error if an incorrect type is received.

### Formatting
1. Line length must be 99 characters or less. NO EXCPETIONS
2. All unused imports must be removed
3. After the unused imports are removed, re-run all the tests to ensure they still pass
4. W293 must be followed
