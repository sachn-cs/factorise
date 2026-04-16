# factorise development commands

default: help

# Run ruff linter
lint:
    ruff check src/ tests/ benchmarks/

# Apply ruff formatting
format:
    ruff format src/ tests/ benchmarks/

# Run mypy type checker
typecheck:
    mypy src/ tests/ benchmarks/

# Run test suite
test:
    pytest tests/ -v

# Run tests with coverage report
test-cov:
    pytest --cov=factorise --cov-report=term-missing tests/

# Run tests with coverage enforcement (CI threshold)
test-ci:
    pytest --cov=factorise --cov-fail-under=90 tests/

# Run benchmarks
benchmark:
    pytest benchmarks/bench_timing.py --benchmark-only -v

# Run memory benchmarks
benchmark-memory:
    pytest benchmarks/bench_memory.py -v

# Run stress test (requires multiprocessing)
stress-test:
    python -m benchmarks.stress_test

# Install all dependencies (dev + prod)
dev-setup:
    pip install -e ".[dev]"

# Clean build artifacts and caches
clean:
    rm -rf build/ dist/ *.egg-info/ src/*.egg-info/
    rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Build sdist and wheel
build:
    pip install build && python -m build

# Run all CI checks locally
ci: lint format typecheck test-ci
    @echo "All CI checks passed."