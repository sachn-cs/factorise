# Contributing to Factorise

Thank you for your interest in contributing to `factorise`. This guide outlines the workflow and standards for this repository.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Branch Naming](#branch-naming)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Code Quality Standards](#code-quality-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

This project adheres to the [Contributor Covenant v2.1](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

1. **Issue first**: For larger changes, please [open an issue](https://github.com/sachncs/factorise/issues/new/choose) first to discuss the design.
2. **Fork and Branch**: Fork the repo and create a feature branch from `master`.
3. **Draft PR**: Open a Draft Pull Request early to get feedback.
4. **Pass Checks**: Ensure all CI checks pass locally before marking as ready for review.
5. **Review and Merge**: Address reviewer comments and maintain a clean commit history.

## Development Setup

### Prerequisites

- Python 3.10+
- [just](https://github.com/casey/just) task runner (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/sachncs/factorise.git
cd factorise

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Using the Setup Script

```bash
./setup.sh
```

This will automatically detect Python 3.10+, create a virtual environment, install dependencies, and set up pre-commit hooks.

## Branch Naming

Use descriptive branch names with the following prefixes:

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feat/` | New features | `feat/add-parallel-ecm` |
| `fix/` | Bug fixes | `fix/pollard-rho-determinism` |
| `docs/` | Documentation | `docs/update-api-reference` |
| `refactor/` | Code restructuring | `refactor/pipeline-stages` |
| `test/` | Test additions/fixes | `test/add-edge-case-coverage` |
| `chore/` | Maintenance tasks | `chore/update-dependencies` |
| `perf/` | Performance improvements | `perf/optimize-gcd-batching` |

## Commit Conventions

This project follows [Conventional Commits](https://www.conventionalcommits.org/). All commits must use the format:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only changes |
| `style` | Code style changes (formatting, missing semi-colons, etc.) |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Code change that improves performance |
| `test` | Adding missing tests or correcting existing tests |
| `chore` | Changes to the build process or auxiliary tools |
| `ci` | Changes to CI configuration files and scripts |

### Scope

Optional scope should be placed in parentheses:

- `feat(pipeline)`: Changes to the factorisation pipeline
- `fix(ecm)`: Fixes in the ECM stage
- `docs(api)`: API documentation updates
- `test(cli)`: CLI test additions

### Examples

```
feat(pipeline): add parallel ECM curve execution
fix(pollard-rho): handle edge case for n=2
docs(api): update factorise() return type documentation
refactor(stages): extract common GCD utilities
test(ecm): add property-based tests for curve operations
chore(deps): update pytest to 8.0.0
ci(github): add Python 3.14 to test matrix
```

### Breaking Changes

For breaking changes, add `!` after the type/scope and include a `BREAKING CHANGE:` footer:

```
feat(api)!: change FactorisationResult.factors to return dict

BREAKING CHANGE: FactorisationResult.factors now returns a dict
mapping prime factors to their exponents instead of a list.
```

## Pull Request Process

### Before Opening a PR

1. Ensure your branch is up to date with `master`:
   ```bash
   git fetch origin
   git rebase origin/master
   ```

2. Run the full CI suite:
   ```bash
   just ci
   ```

3. Verify tests pass with coverage:
   ```bash
   just test-ci
   ```

### PR Requirements

- **Title**: Must follow Conventional Commits format
- **Description**: Clear summary of changes and motivation
- **Related Issue**: Link to the issue being addressed
- **Tests**: Include tests for new functionality
- **Documentation**: Update docs if changing public API
- **No Failing CI**: All checks must pass

### PR Template

Use the provided [PR template](.github/PULL_REQUEST_TEMPLATE.md) when creating your pull request.

### Review Process

1. PRs require at least one approval from a maintainer
2. All CI checks must pass
3. Address review comments promptly
4. Squash and merge for clean history

## Code Quality Standards

### Linting and Formatting

We use `ruff` for linting and formatting:

```bash
just lint          # Check for issues
just format        # Auto-format code
```

### Type Checking

We use `mypy` with strict mode:

```bash
just type-check    # Run type checking
```

### Style Expectations

- **Strict Typing**: All public APIs must have full type hints (PEP 484)
- **Documentation**: Use Google-style docstrings for all modules, classes, and functions
- **No Global State**: Algorithm configuration must be handled via `FactoriserConfig`
- **Validation**: Use `validate_int()` for public entry points to ensure plain integer inputs
- **Imports**: Use absolute imports; sort with `isort` (enforced by ruff)

### Pre-commit Hooks

Pre-commit hooks automatically run:

- Trailing whitespace removal
- End-of-file fixer
- YAML/TOML validation
- Ruff linting and formatting
- mypy type checking

## Testing

Coverage must not fall below **90%**. All new functionality must include tests covering success and failure modes.

### Running Tests

```bash
just test              # Run test suite
just test-ci          # Run with coverage enforcement
just benchmark        # Run benchmarks
just stress-test      # Run stress tests
```

### Test Organization

| Directory | Purpose |
|-----------|---------|
| `tests/test_core_*.py` | Unit tests for core algorithms |
| `tests/test_pipeline.py` | Pipeline integration tests |
| `tests/test_cli*.py` | CLI tests |
| `tests/test_hybrid.py` | Hybrid engine tests |
| `tests/test_properties.py` | Property-based tests (Hypothesis) |
| `tests/test_concurrency_*.py` | Concurrency smoke tests |
| `benchmarks/` | Performance benchmarks |

### Writing Tests

- Use descriptive test names
- Test both success and failure paths
- Use `pytest.mark.parametrize` for parameterized tests
- Use Hypothesis for property-based testing of invariants
- Mock external dependencies (e.g., GNFS binary)

## Documentation

### Code Documentation

- All public functions, classes, and modules must have docstrings
- Use Google-style docstrings format
- Include type hints for all parameters and return values
- Document exceptions that may be raised

### Algorithm Documentation

Algorithm-specific documentation lives in `docs/`. When adding or modifying algorithms:

1. Update or create the corresponding doc in `docs/`
2. Include mathematical background where appropriate
3. Add references to academic papers

### API Changes

When modifying public API:

1. Update docstrings
2. Update `docs/` if applicable
3. Add entry to `CHANGELOG.md`
4. Consider backward compatibility

---

## Questions?

Feel free to [open an issue](https://github.com/sachncs/factorise/issues/new/choose) for any questions about contributing.
