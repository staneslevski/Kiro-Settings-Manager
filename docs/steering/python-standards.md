---
inclusion: fileMatch
fileMatchPattern: ["**/*.py"]
---


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
5. Upgrade pip to latest version after creating virtual environment

### Requirements
- Always check if `.venv` exists before creating
- Include `.venv/` in `.gitignore`
- Document dependencies in `requirements.txt` or `pyproject.toml`
- All pip installs, script runs, and tests must use the virtual environment

### Typing
- Always define types in the input and output of functions
- When testing, always check that types are respected and throw an error if an incorrect type is received

### Formatting
1. Line length must be 88 characters or less. NO EXCEPTIONS
2. All unused imports must be removed
3. After unused imports are removed, re-run all tests to ensure they still pass
4. You MUST NEVER add a comment to ignore a linting or formatting exception
5. When asked to fix a lining issue, you MUST change the code to follow the format requirement
6. NEVER add a comment to ignore a linting requirement

## Code Quality Tools

Use standard Python linters and formatters for compliance:

e.g.

```bash
# Format code (auto-fixes line length, style)
black tests/ scripts/ src/ your-module-name/ etc/

# Check style, unused imports, violations
flake8 tests/ scripts/ src/ your-module-name/ etc/

# Check type annotations
mypy tests/ scripts/ src/ your-module-name/ etc/

# Check test coverage
pytest --cov=tests --cov=scripts tests/ 
```

### Tool Configuration

**black**: Auto-configured to 88 character line length (PEP 8 default)

**flake8** (`.flake8` or `setup.cfg`):
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = .venv, .git, __pycache__, .hypothesis, .pytest_cache
```

**mypy** (`mypy.ini` or `pyproject.toml`):
```ini
[mypy]
python_version = 3.8
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
```

### Pre-Commit Workflow

Before committing code:
1. Run `black` to auto-format
2. Run `flake8` to check for issues
3. Run `mypy` to verify type annotations
4. Run tests with coverage
5. Fix any reported issues