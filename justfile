# factorise development commands

default: help

# List all available commands
help:
    @just --list

# Install all dependencies (dev + prod)
install:
    pip install -e ".[dev]"

# Run Ruff linter (code quality)
lint:
    ruff check src/ tests/ benchmarks/

# Apply Ruff auto-fixes then format
format:
    ruff check --fix src/ tests/ benchmarks/
    ruff format src/ tests/ benchmarks/

# Run mypy static type checker
type-check:
    mypy src/ tests/ benchmarks/

# Run dependency vulnerability scanning
security:
    pip-audit --strict

# Run the pytest test suite
test:
    pytest tests/ -v

# Run the pytest test suite with coverage enforcement
test-ci:
    pytest --cov=factorise --cov-fail-under=90 tests/ -v

# Clean build artifacts and caches
clean:
    rm -rf build/ dist/ *.egg-info/ src/*.egg-info/
    rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Build sdist and wheel artifacts
build: clean
    python -m build

# Run benchmarks
benchmark:
    pytest benchmarks/timing.py --benchmark-only -v

# Run memory benchmarks
benchmark-memory:
    pytest benchmarks/memory.py -v

# Run stress tests
stress-test:
    python -m benchmarks.stress

# Run all CI checks locally (fail-fast)
ci: lint type-check test-ci
    @echo "All fast CI checks passed."

# Extended CI checks including stress and security
ci-full: ci security stress-test
    @echo "Full CI suite passed."

# Run benchmarks with CI threshold checking
benchmark-ci:
    pytest benchmarks/timing.py --benchmark-only --benchmark-compare --benchmark-compare-fail=min:10% -v
