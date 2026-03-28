# Contributing to Factorise

First off, thank you for considering contributing to `factorise`!

## Workflow

1. **Fork** the repository and clone it locally.
2. **Branch** off `main` for your work.
3. **Commit** your changes with clear, descriptive commit messages.
4. **Push** your branch to your fork.
5. **Open a Pull Request** against the `main` branch.

## Setup for Development

To set up the repository for local development:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Coding Standards

### Python Style Guide
This project strictly follows the **Google Python Style Guide**:
- All variables and functions must be `snake_case`.
- Classes must be `PascalCase`.
- Constants must be `UPPER_CASE`.
- All functions *must* have Google-style docstrings (with `Args:`, `Returns:`, and `Raises:` when applicable).
- Avoid monolithic functions; extract logic whenever possible.
- Use explicit Type Hints everywhere (`int`, `str`, `list[int]`, etc.).

### Linter & Formatter Expectations
Before submitting a Pull Request, verify that your code passes all established checks:
```bash
isort src/ tests/ benchmarks/
black src/ tests/ benchmarks/
flake8 --extend-ignore=E501 src/ tests/ benchmarks/
pylint src/ tests/ benchmarks/
mypy src/ tests/ benchmarks/
```

### Testing
We enforce **100% line coverage** for the core mathematical engine on CI. Write `pytest` unit tests for any new behavior or bug fixes in `tests/`.

```bash
pytest --cov=factorise -v tests/
```

### Pull Request Quality
- Every PR must maintain a **10.00/10 Pylint score**.
- New algorithms must include a supporting document in `docs/`.
- Large changes should be accompanied by a pass through `benchmarks/stress_test.py`.
