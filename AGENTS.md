# Agent Guidelines for This Project

## Project Overview

This is a Python project. The entry point is configured as `main.py`.

## Build, Lint, and Test Commands

```bash
# Run the application
python main.py

# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run a single test
pytest tests/test_file.py::test_function_name
pytest tests/test_file.py::TestClass::test_method

# Run tests with verbose output
pytest -v

# Run tests matching a pattern
pytest -k "test_pattern"

# Linting with flake8
flake8 .

# Linting with ruff
ruff check .

# Type checking with mypy
mypy .

# Format code with black
black .

# Format and sort imports with isort
isort .
```

If a Makefile exists:
```bash
make install    # Install dependencies
make lint       # Run linters
make test       # Run tests
make format     # Format code
```

## Code Style Guidelines

### General Principles
- Write clean, readable, and maintainable code
- Follow PEP 8 style guide for Python
- Keep functions small and focused (single responsibility)
- Write docstrings for all public modules, functions, and classes

### Imports
- Use absolute imports over relative imports when possible
- Group imports in order: standard library, 3rd party, local application
- Sort imports alphabetically within each group
- Use `isort` to automatically sort imports

### Formatting
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 88 characters (Black default)
- Use blank lines to separate logical sections
- No trailing whitespace

### Types
- Use type hints for all function signatures and variables
- Use `Any` sparingly; prefer specific types when possible
- Use `Optional[T]` instead of `T | None` for Python < 3.10

### Naming Conventions
- **Modules**: `snake_case` (e.g., `user_service.py`)
- **Classes**: `PascalCase` (e.g., `UserService`)
- **Functions/variables**: `snake_case` (e.g., `get_user_by_id`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRY_COUNT`)
- **Private methods/variables**: Prefix with underscore (e.g., `_internal_method`)

### Error Handling
- Use specific exception types
- Never catch bare `Exception` or `BaseException`
- Always log errors before re-raising
- Use context managers (`with`) for resource management

### Testing
- Place tests in a `tests/` directory
- Name test files as `test_<module_name>.py`
- Use descriptive test names: `test_<method>_<expected_behavior>`
- Use pytest fixtures for setup/teardown
- Aim for high test coverage on business logic

### Documentation
- Use Google-style or NumPy-style docstrings
- Include type hints in docstrings for clarity
- Document behavior, not implementation details

### File Structure
```
project/
├── main.py              # Entry point
├── requirements.txt     # Dependencies
├── setup.py             # Package setup
├── myapp/               # Application code
│   ├── __init__.py
│   ├── models/
│   ├── services/
│   └── utils/
├── tests/               # Test files
│   ├── __init__.py
│   └── test_*.py
└── docs/                # Documentation
```

## Cursor/Copilot Rules
No Cursor or Copilot rules found in this project.

## Notes for Agents
- Verify all changes work by running tests before considering complete
- Run linting tools before committing
- Keep dependencies updated but test thoroughly before upgrading