---
inclusion: always
---


# Python Standards

## Virtual Environment

### NON-NEGOTIABLE
1. ALL Python work MUST be completed in a virtual environment
2. Virtual environment MUST be named `.venv` in project root
3. NEVER install packages globally or outside the virtual environment
4. ALL commands MUST be run by activating the venv first: `source .venv/bin/activate && YOUR_COMMAND`
5. NEVER call binaries directly from `.venv/bin/` (e.g. `.venv/bin/pip`, `.venv/bin/python`). Always activate then run.

### Command Format
Every Python-related command MUST follow this pattern:

```bash
source .venv/bin/activate && YOUR_COMMAND_GOES_HERE
```

Examples:
```bash
# Correct
source .venv/bin/activate && pip install -e ".[dev]"
source .venv/bin/activate && python my_script.py
source .venv/bin/activate && pytest tests/
source .venv/bin/activate && black src/

# WRONG — never do this
.venv/bin/pip install something
.venv/bin/python my_script.py
pip install -r requirements.txt
```

### Setup Process
1. Create virtual environment: `python3 -m venv .venv`
2. Activate and upgrade pip: `source .venv/bin/activate && pip install --upgrade pip`
3. Install dependencies: `source .venv/bin/activate && pip install -e .`
4. All subsequent commands follow the same `source .venv/bin/activate && ...` pattern

### Requirements
- Always check if `.venv` exists before creating
- Include `.venv/` in `.gitignore`
- Document dependencies in `pyproject.toml`
- All pip installs, script runs, and tests must activate the venv first

### Project Configuration
- Always use `pyproject.toml` as the single source of project metadata, dependencies, and tool configuration
- Do not use legacy configuration files such as `setup.py`, `setup.cfg`, `requirements.txt`, `.flake8`, `mypy.ini`, or `pytest.ini`
- Define all tool settings (black, flake8, mypy, pytest, etc.) in `pyproject.toml`
- Use `flake8-pyproject` as a dev dependency so flake8 reads config from `pyproject.toml`
- Install the project with `source .venv/bin/activate && pip install -e ".[dev]"` (dev extras for tooling)

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
source .venv/bin/activate && black tests/ scripts/ src/ your-module-name/ etc/

# Check style, unused imports, violations
source .venv/bin/activate && flake8 tests/ scripts/ src/ your-module-name/ etc/

# Check type annotations
source .venv/bin/activate && mypy tests/ scripts/ src/ your-module-name/ etc/

# Check test coverage
source .venv/bin/activate && pytest --cov=tests --cov=scripts tests/ 
```

### Tool Configuration

All tool configuration MUST live in `pyproject.toml`. Do not use standalone config files like `.flake8`, `setup.cfg`, `mypy.ini`, or `pytest.ini`.

Note: flake8 does not natively support `pyproject.toml`. Use `flake8-pyproject` (or `Flake8-pyproject`) as a dependency so flake8 reads its config from `pyproject.toml`.

Example `pyproject.toml` tool sections:

```toml
[tool.black]
line-length = 88

[tool.flake8]
max-line-length = 88
extend-ignore = ["E203", "W503"]
exclude = [".venv", ".git", "__pycache__", ".hypothesis", ".pytest_cache"]

[tool.mypy]
python_version = "3.13"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### Pre-Commit Workflow

Before committing code:
1. Run `black` to auto-format
2. Run `flake8` to check for issues
3. Run `mypy` to verify type annotations
4. Run tests with coverage
5. Fix any reported issues

## Property-Based Testing with Hypothesis

### NON-NEGOTIABLE
1. Property tests MUST use two-tier configuration for example counts
2. Local development MUST use 10-15 examples for fast feedback
3. CI/CD pipelines MUST use 50+ examples for thorough validation
4. NEVER run full example counts during local development

### Configuration Strategy

Use Hypothesis profiles to separate local and CI testing:

**conftest.py** (or test configuration file):
```python
from hypothesis import settings, Verbosity

# Local development profile: fast feedback
settings.register_profile(
    "dev",
    max_examples=15,
    verbosity=Verbosity.normal,
    deadline=None,
)

# CI/CD profile: thorough validation
settings.register_profile(
    "ci",
    max_examples=100,
    verbosity=Verbosity.verbose,
    deadline=None,
)

# Load profile from environment or default to dev
import os
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))
```

### Usage

**Local development** (fast, 10-15 examples):
```bash
source .venv/bin/activate && pytest tests/
```

**CI/CD pipeline** (thorough, 100 examples):
```bash
source .venv/bin/activate && HYPOTHESIS_PROFILE=ci pytest tests/
```

### Writing Property Tests

Always use the configured profile, never override in individual tests:

```python
from hypothesis import given
from hypothesis import strategies as st

@given(st.integers())
def test_property(value: int) -> None:
    # Test uses profile settings automatically
    assert some_property(value)
```

### Rationale

- 10-15 examples provide quick feedback during development
- 100 examples catch edge cases in CI without slowing local work
- Prevents 10-15 minute test suite runs during development
- Maintains thorough validation in automated pipelines
