---
inclusion: always
---

# Testing Standards

## Testing vs Linting

### Testing
- Tests check the FUNCTIONALITY of BUSINESS LOGIC
- Write tests for application code, libraries, modules, and functions
- DO NOT write tests to test test code itself
- Testing applies to: business logic, application code, utilities, libraries

### Linting
- Linting checks code FORMATTING and STYLE
- Linting is quick, automated, and applies to ALL code
- Linting applies to: business logic AND test code
- Use tools like black, flake8, mypy, eslint, prettier, etc.

## NON-NEGOTIABLE
1. ALL business logic MUST be tested - no exceptions
2. ALL tests MUST pass before task completion
3. ≥95% code coverage required for business logic (statements, branches, functions, lines)
4. NEVER skip, disable, or comment out tests
5. Task is incomplete until tests pass with ≥95% coverage
6. ALWAYS follow Test-Driven Development (TDD)
7. ALL code (business logic AND test code) MUST pass linting

## Core Requirements

### Test-Driven Development (TDD)
- Write tests BEFORE writing business logic
- Work in small batches: write tests → run tests (they fail) → write code → tests pass
- Tests define the standards and requirements for code to work
- Never write implementation code without tests first
- Refactor only after tests pass

### Test Everything (Business Logic)
- Every business logic function, method, and module must have tests
- Test both success paths and error conditions
- Test edge cases and boundary conditions
- Test validation logic thoroughly
- DO NOT write tests for test code - tests validate business logic only
- If there are more than 500 test executions in a script, it should show a status bar to the user to confirm that tests are still running

### Assess Coverage Appropriately
- Before writing new tests, assess whether the functionality you want to assess is already covered by existing tests.

### Coverage Standards
- Minimum 95% coverage across all metrics for business logic
- Measure statements, branches, functions, and lines
- Use appropriate coverage tools for your language
- No task is complete below 95% threshold
- Coverage applies to business logic, not test code

### Test Quality
- Tests must validate actual functionality
- Use descriptive test names that explain behavior
- Keep tests focused and independent
- Avoid brittle tests that break with minor changes

## When Tests Fail
1. Investigate the root cause
2. Fix the code OR fix the test
3. Re-run until all tests pass
4. Never complete a task with failing tests

## Fix Warnings
1. If code outputs warnings during linting or testing, these should be treated seriously
2. Do not ignore warnings
3. Only accept warnings if fixing them would cause more errors
4. You must attempt to fix warnings
5. If you cannot fix a warning you MUST explicitly explain to a user why you cannot fix the warning
6. Linting warnings apply to ALL code (business logic and test code)

## When Coverage <95%
1. Identify uncovered code paths
2. Add tests for missing coverage
3. Test edge cases and error handling
4. Achieve ≥95% before marking task complete

## Task Completion Criteria
A task is only complete when:
- All tests pass
- Coverage is ≥95% for business logic
- No tests are skipped or disabled
- All code (business logic and test code) passes linting
