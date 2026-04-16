# Contributing to Factorise

Thank you for contributing to `factorise`.

## Workflow

1. **Fork** the repository and clone it locally.
2. **Branch** off `master` for your work.
3. **Commit** your changes with clear, descriptive commit messages.
4. **Push** your branch to your fork.
5. **Open a Pull Request** against the `master` branch.

## Setup for Development

```bash
# Clone and enter the repository
git clone https://github.com/sachin/factorise.git
cd factorise

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the package with all development dependencies
pip install -e ".[dev]"

# Optionally install pre-commit hooks
pip install pre-commit
pre-commit install
```

## Coding Standards

### Tools

| Tool | Role |
|------|------|
| `ruff` | Linting, import sorting, format |
| `mypy` | Static type checking |
| `black` | Code formatting (via ruff) |
| `pytest` | Test execution |
| `pytest-cov` | Coverage reporting |

### Pre-commit Hooks

After installing dependencies, enable pre-commit hooks:

```bash
pre-commit install
```

On every commit, `ruff check`, `ruff format`, and `mypy src/` run automatically. Fix any failures before pushing.

### Local CI Checks

Before opening a PR, run all checks locally:

```bash
make ci
```

Or via the equivalent commands:

```bash
ruff check src/ tests/ benchmarks/
ruff format src/ tests/ benchmarks/
mypy src/ tests/ benchmarks/
pytest --cov=factorise --cov-fail-under=90 tests/
```

### Style Expectations

- **Type hints** on all public functions and classes (PEP 484).
- **Google-style docstrings** required on all public functions and classes.
- **No booleans as integers**: `validate_int()` enforces plain `int` only; `bool` is rejected explicitly.
- **No global state**: configuration is always passed explicitly via `FactoriserConfig`.
- **`FactoriserConfig` upper bounds**: `batch_size ≤ 10_000`, `max_iterations ≤ 1_000_000_000`, `max_retries ≤ 100`.

## Testing

```bash
# Run the full suite
pytest tests/ -v

# Run with coverage report
pytest --cov=factorise --cov-report=term-missing tests/

# Run benchmarks
pytest benchmarks/bench_timing.py --benchmark-only -v
pytest benchmarks/bench_memory.py -v

# Run the stress test (requires multiprocessing)
python -m benchmarks.stress_test
```

All new functionality requires tests. PRs with failing tests will not be merged. Coverage must not fall below 90%.

## Pull Request Quality

- All CI jobs must pass (`lint`, `typecheck`, `test`).
- New algorithms must include a supporting document in `docs/`.
- Large changes should be accompanied by a pass through the stress test (`python -m benchmarks.stress_test`).
- Commit messages should describe _why_, not _what_.

## Adding a New Algorithm

1. Implement as a plain function in `core.py`; accept `FactoriserConfig` if tuneable.
2. Return a factor or raise `RuntimeError` — do not return `None` silently on failure.
3. Add tests covering correct output, edge cases, and failure modes in `tests/test_core.py`.
4. Export from `__init__.py` if it is part of the public API.
5. Verify `ruff check`, `ruff format`, and `mypy src/` all pass.