# Contributing to mfup

Thanks for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/eshan-singh78/mfup.git
cd mfup
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Running Checks

```bash
# Tests
pytest -v

# Linting
ruff check .
ruff format --check .

# Type checking
mypy coremfup/mfup

# Build binary
pyinstaller --clean --noconfirm mfup.spec
./dist/mfup --version
```

## Pull Request Process

1. Fork the repo and create your branch from `main`.
2. Make sure tests pass and code is formatted.
3. Update `CHANGELOG.md` if applicable.
4. Open a PR with a clear description.

## Code Style

- Follow PEP 8.
- Use type hints on public functions.
- Write tests for new features and bug fixes.
- Keep the CLI user-friendly with clear error messages.
