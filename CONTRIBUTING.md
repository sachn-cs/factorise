# Contributing to Factorise

Thank you for your interest in contributing to `factorise`. This guide outlines the workflow and standards for this repository.

## Workflow

1. **Issue first**: For larger changes, please open an issue first to discuss the design.
2. **Fork and Branch**: Fork the repo and create a feature branch off `master`.
3. **Draft PR**: Open a Draft Pull Request early to get feedback.
4. **Pass Checks**: Ensure all CI checks pass locally (`just ci`) before marking as ready for review.
5. **Review and Merge**: Address reviewer comments and maintain a clean commit history.

## Setup for Development

Prerequisites: Python 3.10+ and a virtual environment.

```bash
# Clone the repository
git clone https://github.com/sachn-cs/factorise.git
cd factorise

# Install development dependencies
pip install -e ".[dev]"

# Optional: Install pre-commit hooks
pre-commit install
```

We recommend using [just](https://github.com/casey/just) for task automation. Run `just --list` to see available commands.

## Quality Standards

### Linting and Type Checking
We use `ruff` for linting/formatting and `mypy` for static type checking.

```bash
# Run all quality checks
just lint
just type-check
```

### Style Expectations
- **Strict Typing**: All public APIs must have full type hints (PEP 484).
- **Documentation**: Use Google-style docstrings for all modules, classes, and functions.
- **No Global State**: Algorithm configuration must be handled via `FactoriserConfig`.
- **Validation**: Use `validate_int()` for public entry points to ensure plain integer inputs.

## Testing

Coverage must not fall below **90%**. All new functionality must include tests covering success and failure modes.

```bash
# Run the test suite
just test

# Run with coverage enforcement
just test-ci

# Run benchmarks and stress tests
just benchmark
just stress-test
```

## Pull Request Guidelines

- **Atomic Commits**: Keep commits focused and logically separated.
- **Passing CI**: PRs with failing linting or tests will not be merged.
- **Security**: Large changes must pass the stress test (`just stress-test`) to ensure algorithm stability.
- **Release Integrity**: Releases are published via OIDC and include SHA256 integrity files and CycloneDX SBOMs.

---
See `SECURITY.md` for our security policy and `CODE_OF_CONDUCT.md` for community standards.
