.PHONY: help lint format typecheck test test-cov test-ci clean

help:
	@echo "factorise development commands"
	@echo ""
	@echo "  lint       Run ruff linter"
	@echo "  format     Apply ruff formatting"
	@echo "  typecheck  Run mypy type checker"
	@echo "  test       Run test suite"
	@echo "  test-cov   Run tests with coverage report"
	@echo "  test-ci    Run tests with coverage enforcement"
	@echo "  clean      Remove build artifacts and caches"

lint:
	ruff check src/ tests/ benchmarks/

format:
	ruff format src/ tests/ benchmarks/

typecheck:
	mypy src/ tests/ benchmarks/

test:
	pytest tests/ -v

test-cov:
	pytest --cov=factorise --cov-report=term-missing tests/

test-ci:
	pytest --cov=factorise --cov-fail-under=90 tests/

clean:
	rm -rf build/ dist/ *.egg-info/ src/*.egg-info/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true