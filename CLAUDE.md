# CLAUDE.md — AI Assistant Guide for kn0

This document provides guidance for AI assistants (Claude and others) working on this repository.

## Repository Overview

**kn0** is a Python project currently in its initial setup phase. The repository was initialized with a standard Python `.gitignore`, MIT license, and minimal README. Source code and configuration files are expected to be added as the project develops.

- **Language**: Python
- **License**: MIT
- **Owner**: aleknitka

## Repository Structure

```
kn0/
├── .gitignore       # Comprehensive Python project gitignore
├── LICENSE          # MIT License
├── README.md        # Project readme (minimal, to be expanded)
└── CLAUDE.md        # This file
```

As the project evolves, expect additions like:
- `src/` or package directory for source code
- `tests/` for test files
- `pyproject.toml` / `setup.py` / `requirements.txt` for dependencies
- `.env` for environment variables (never commit this)
- `docs/` for documentation

## Git Workflow

### Branches

- `main` — stable, production-ready code
- `master` — may be used interchangeably with `main` in this repo
- `claude/<description>-<id>` — AI-generated feature branches (e.g., `claude/add-claude-documentation-694lO`)

### Branch Conventions

- Feature branches follow the pattern: `claude/<short-description>-<session-id>`
- Always develop on the designated feature branch; never push directly to `main`/`master`
- Use descriptive commit messages that explain *why*, not just *what*

### Commit Messages

Write clear, imperative commit messages:
```
Add user authentication module
Fix pagination bug in search results
Update dependencies to resolve security vulnerabilities
```

### Push Commands

```bash
git push -u origin <branch-name>
```

## Python Development Conventions

### Package Management

This project may use any of the following (check for lockfiles to determine which is active):
- **uv** — modern, fast package manager (`uv.lock`)
- **Poetry** — dependency management (`poetry.lock`, `pyproject.toml`)
- **PDM** — PEP 517-compliant (`pdm.lock`)
- **pip** — fallback (`requirements.txt`)

When a lockfile is present, always install from it for reproducibility.

### Code Style

Based on the gitignore, the following tools are expected:
- **Ruff** — linting and formatting (check for `ruff.toml` or `[tool.ruff]` in `pyproject.toml`)
- **MyPy** — static type checking (check for `mypy.ini` or `[tool.mypy]` in `pyproject.toml`)

Run linting before committing:
```bash
ruff check .
ruff format .
mypy .
```

### Testing

Expected testing setup:
- **pytest** — primary test runner
- **tox** or **nox** — multi-environment testing

Run tests with:
```bash
pytest
# or
pytest -v --tb=short
```

## Framework Notes

The `.gitignore` includes patterns for common Python web frameworks. Once a framework is chosen, update this section with:
- How to run the development server
- Database migration commands
- Environment variable requirements

### If Django is used
```bash
python manage.py runserver
python manage.py migrate
python manage.py test
```

### If Flask is used
```bash
flask run
flask db upgrade    # if Flask-Migrate is used
pytest
```

## Environment Variables

- Never commit `.env` or `.envrc` files
- Document required environment variables here as they are defined
- Use `.env.example` as a template for local setup

## AI Assistant Instructions

When working on this repository:

1. **Explore before editing** — read relevant files before making changes
2. **Minimal changes** — only modify what is necessary; avoid scope creep
3. **Preserve conventions** — follow existing code style, naming, and structure once established
4. **No secret leakage** — never hardcode credentials, tokens, or keys
5. **Test awareness** — if tests exist, ensure they pass after changes
6. **Update documentation** — keep README and this file current when making significant structural changes
7. **Branch hygiene** — always develop on the designated feature branch

## Common Commands (to be updated as project grows)

```bash
# Install dependencies (adapt based on package manager found)
pip install -r requirements.txt
# or
uv sync
# or
poetry install

# Run linter
ruff check .

# Run formatter
ruff format .

# Run type checker
mypy .

# Run tests
pytest

# Run tests with coverage
pytest --cov
```

## Notes for Future Development

- This file should be updated whenever major architectural decisions are made (framework choice, database, deployment strategy)
- Add CI/CD configuration details here once GitHub Actions or similar is set up
- Document any non-obvious design decisions or constraints
