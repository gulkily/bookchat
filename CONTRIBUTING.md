# Contributing to BookChat

This document outlines important conventions and guidelines for contributing to the BookChat project.

## Repository Structure

### Important Directories

- `messages/`: Contains message data files. This directory and its contents **should be committed** to the repository as it contains essential application data.
- `server/`: Contains the main server implementation
- `tests/`: Contains test files
- `templates/`: Contains HTML templates
- `static/`: Contains static assets (JS, CSS, etc.)

### Version Control

#### Files to Commit
- All source code files (*.py, *.js, *.html, etc.)
- Message data files in `messages/` directory
- Configuration files
- Documentation files

#### Files to Ignore
- Python bytecode files (*.pyc, *.pyo, __pycache__)
- Coverage reports (.coverage, htmlcov/)
- Virtual environment directories
- Environment files (.env*)
- IDE configuration files

## Development Guidelines

### Testing
- All new features should include appropriate tests
- Both unit tests and integration tests should be added where appropriate
- Tests should be placed in the `tests/` directory

### Code Organization
- Server-side code should be organized within the `server/` package
- Each module should have a clear, single responsibility
- Keep related files together in appropriate subdirectories

### Documentation
- Code should be well-documented with docstrings
- Major design decisions should be documented
- Update this guide when introducing new conventions or patterns
