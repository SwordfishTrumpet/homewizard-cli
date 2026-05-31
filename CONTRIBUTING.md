# Contributing to homewizard-cli

## Development Setup

```bash
git clone https://github.com/SwordfishTrumpet/homewizard-cli
cd homewizard-cli
pip install uv
uv sync --all-extras
```

## Running Tests

```bash
uv run python -m pytest tests/ -v
```

## Code Quality

Before submitting a PR, run the full lint/typecheck/test suite:

```bash
uv run ruff check homewizard_cli/ tests/
uv run python -m mypy --check-untyped-defs homewizard_cli/ tests/
uv run python -m pytest tests/ -v
```

## Pre-commit Hooks

Install pre-commit hooks:

```bash
uv run pre-commit install
```

## Pull Request Process

1. Fork the repository and create a feature branch
2. Make your changes following the existing code style
3. Add tests for new functionality
4. Run the full test suite and ensure all checks pass
5. Update documentation if applicable
6. Submit a PR against the `main` branch

## Code Style

- Follow existing patterns in the codebase
- Use type annotations for all public functions
- Do not add comments unless necessary — the code should be self-documenting
- Follow the patterns documented in `AGENTS.md`
