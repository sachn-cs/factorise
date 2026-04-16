# factorise

[![CI](https://github.com/sachin/factorise/actions/workflows/ci.yml/badge.svg)](https://github.com/sachin/factorise/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](https://github.com/sachin/factorise)

A pure-Python library for deterministic prime factorisation of arbitrary integers, built on **Miller-Rabin** primality testing and **Pollard's Rho (Brent)** for factor finding. Supports Python 3.10+, installable via pip, importable as a library, and accessible via CLI.

---

## Project Overview

### Problem It Solves

Decomposing an integer into its prime factors is foundational to number theory, cryptography, and algorithmics. For numbers large enough to make trial division impractical, `factorise` provides a fast, correct, and memory-efficient solution without C extensions or external native dependencies.

### Value Proposition

- **Deterministic:** Miller-Rabin with the Jaeschke witness set is proven deterministic for all integers below 2^64 — no probability of false positives.
- **Zero-dependency runtime:** Only `typer`, `rich`, and `loguru` at runtime; no C extensions, no GMP, no external services.
- **Explicit configuration:** No global state; every algorithm parameter is passed through `FactoriserConfig`.
- **Production-ready:** Structured logging, typed interfaces, comprehensive error handling, and graceful signal handling in the CLI.

---

## Architecture

```
Input validation (validate_int)
         │
         ▼
  Miller-Rabin primality test ◄──── gate for all recursive factorisation steps
         │
         ▼
  Pollard-Brent (single attempt)  ── batches GCD ops; returns None on cap hit
         │
         ▼
  Pollard-Brent (with retries)  ◄── fresh random seeds; raises RuntimeError on exhaustion
         │
         ▼
  _factor_yield (recursive splitter)  ── yields prime factors via generator
         │
         ▼
  factorise() ─────────────────────────► FactorisationResult (frozen dataclass)
```

**Key design decisions:**
- `FactoriserConfig` is a frozen dataclass — immutable after construction.
- `_factor_yield` is a generator function — memory-efficient for numbers with many repeated factors.
- `validate_int` enforces plain `int` only; `bool` is rejected explicitly.

---

## Features

### Core Algorithms

| Feature | Description |
|---------|-------------|
| **Deterministic Miller-Rabin** | Fixed 12-witness set proven sufficient for all n < 2^64 |
| **Brent's Pollard Rho** | Batched GCD computation reduces modular arithmetic calls vs classic Rho |
| **Trial division fast-path** | First checks against primes ≤ 73 before invoking Pollard-Brent |
| **Perfect square detection** | `math.isqrt` shortcut before expensive factorisation |
| **Configurable iteration cap** | Hard limit prevents infinite loops on pathological composite inputs |

### API Surface

| Symbol | Type | Description |
|--------|------|-------------|
| `factorise(n, config?)` | function | Primary entry point; returns `FactorisationResult` |
| `is_prime(n)` | function | Standalone primality test; no config required |
| `pollard_brent(n, config)` | function | Exposes the factor-finding loop directly |
| `FactorisationResult` | frozen dataclass | Immutable result container with `.expression()` |
| `FactoriserConfig` | frozen dataclass | Explicit parameter container; supports `from_env()` |

### CLI

| Flag | Description |
|------|-------------|
| `factorise N` | Factorise integer N |
| `--verbose`, `-v` | Show full prime product expression |
| `--log-level` | Set log level (DEBUG, INFO, WARNING, ERROR); respects `FACTORISE_LOG_LEVEL` env var |

---

## Tech Stack

| Role | Tool | Version |
|------|------|---------|
| Language | Python | 3.10+ |
| CLI framework | [typer](https://typer.tiangolo.com/) | ≥ 0.9 |
| Terminal output | [rich](https://github.com/Textualize/rich) | ≥ 13.0 |
| Logging | [loguru](https://github.com/Delgan/loguru) | ≥ 0.7.3 |
| Linting + formatting | [ruff](https://github.com/astral-sh/ruff) | ≥ 0.9.0 |
| Type checking | [mypy](https://mypy-lang.org/) | ≥ 1.8.0 |
| Formatting | [black](https://black.readthedocs.io/) | ≥ 24.0 |
| Testing | [pytest](https://pytest.org/) | ≥ 7.4.0 |
| Benchmarking | [pytest-benchmark](https://pytest-benchmark.readthedocs.io/) | ≥ 5.2.3 |
| Coverage | [pytest-cov](https://pytest-cov.readthedocs.io/) | ≥ 4.0.0 |
| Build | [hatchling](https://hatch.pypa.io/) | latest |

---

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip ≥ 23.0

### Installation

```bash
# Install latest release from PyPI
pip install factorise

# Install from source (editable)
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

### Environment Variables

Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `FACTORISE_BATCH_SIZE` | `128` | GCD operations batched per iteration |
| `FACTORISE_MAX_ITERATIONS` | `10_000_000` | Hard cap on inner steps per Pollard-Brent attempt |
| `FACTORISE_MAX_RETRIES` | `20` | Fresh random seeds before raising `RuntimeError` |
| `FACTORISE_LOG_LEVEL` | `WARNING` | CLI log verbosity (DEBUG, INFO, WARNING, ERROR) |

---

## Usage

### CLI

```bash
# Factorise a number
factorise 123456789

# Verbose output with full expression
factorise 123456789 --verbose

# Debug logging
factorise 123456789 --log-level DEBUG

# Help
factorise --help
```

**Output:**
```
      Factorisation of 123456789
┏━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Prime Factor ┃ Exponent ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│            3 │        2 │
│         3607 │        1 │
│         3803 │        1 │
└──────────────┴──────────┘

Full expression: 3^2 * 3607 * 3803
```

### Library

```python
from factorise import factorise, FactoriserConfig, FactorisationResult

# Default config (reads from environment)
result = factorise(123456789)

# Explicit config
config = FactoriserConfig(batch_size=256, max_retries=30)
result = factorise(123456789, config)

print(result.factors)      # [3, 3607, 3803]
print(result.powers)       # {3: 2, 3607: 1, 3803: 1}
print(result.is_prime)     # False
print(result.expression()) # '3^2 * 3607 * 3803'
```

**Primality check:**

```python
from factorise.core import is_prime

is_prime(2**31 - 1)  # True  (Mersenne prime M31)
is_prime(100)        # False
```

**Error handling:**

```python
from factorise import factorise

try:
    result = factorise(n)
except TypeError:
    # n is not a plain int (bool, float, str, etc.)
    raise
except RuntimeError:
    # Exhausted max_retries; increase max_iterations or max_retries
    raise
```

---

## Configuration

`FactoriserConfig` is a frozen dataclass. All fields are validated at construction time.

```python
from factorise import FactoriserConfig

# Direct construction
config = FactoriserConfig(
    batch_size=256,
    max_iterations=50_000_000,
    max_retries=50,
)

# From environment variables
config = FactoriserConfig.from_env()
```

**Field constraints:**

| Field | Validation |
|-------|------------|
| `batch_size` | must be ≥ 1 |
| `max_iterations` | must be ≥ 1 |
| `max_retries` | must be ≥ 1 |

Invalid values raise `ValueError` immediately at construction.

---

## Testing

```bash
# Run the full test suite
pytest tests/ -v

# Run with coverage report
pytest --cov=factorise --cov-report=term-missing tests/

# Run benchmarks (requires pytest-benchmark)
pytest benchmarks/bench_timing.py --benchmark-only -v

# Run type checker
mypy src/ tests/ benchmarks/

# Run linter
ruff check src/ tests/ benchmarks/

# Run formatter check
ruff format --check src/ tests/ benchmarks/
```

**Coverage:** 239 test cases across unit and integration suites, targeting 99%+ coverage.

**Test categories:**

| Suite | File | Scope |
|-------|------|-------|
| Unit | `test_core.py` | Core algorithms, config, result types |
| Integration | `test_cli.py` | CLI invocation, signal handling, error branches |
| Edge cases | `test_coverage_gap.py` | Iteration caps, backtracking, concurrency |

---

## CI/CD

Pipelines run on every push to `master` and every pull request.

| Job | Steps |
|-----|-------|
| **lint** | `ruff check`, `ruff format --check` |
| **typecheck** | `mypy src/ tests/ benchmarks/` |
| **test** | `pytest --cov=factorise` on Python 3.10, 3.11, 3.12 |

See [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for the full pipeline definition.

---

## Observability

### Logging

`loguru` is used throughout. Logging is **disabled by default** in library contexts to avoid noise; the CLI enables it based on `--log-level` / `FACTORISE_LOG_LEVEL`.

**Library opt-in:**

```python
from loguru import logger

logger.enable("factorise")
logger.add("factorise.log", level="DEBUG")
```

**Events:**

| Level | When |
|-------|------|
| `INFO` | `factorise` start and completion with factor list |
| `DEBUG` | Each Pollard-Brent attempt, seed values, and each recursive split |
| `WARNING` | Iteration cap or backtrack cap reached; attempt abandoned |
| `ERROR` | Invalid input or factorisation failure (CLI only) |

### Signal Handling (CLI)

The CLI registers `SIGINT` and `SIGTERM` handlers that log the signal name and exit cleanly with code `0`.

---

## Security

- **Input validation:** `validate_int` explicitly rejects `bool` and all non-`int` types before any computation.
- **No dynamic code execution:** No `eval`, `exec`, `compile`, or `__import__`.
- **No secrets in code:** All tuning parameters live in `FactoriserConfig` or environment variables; see `.env.example`.
- **Deterministic output:** The algorithm is pure-math deterministic for n < 2^64; no timing side-channels are claimed, but no secret-dependent branches exist.
- **Fuzzing-ready:** The core functions are pure and referentially transparent apart from `random` internals scoped to `pollard_brent`.

**Intended audience:** Mathematical and educational use. This library does not implement constant-time operations or side-channel protections and is not suitable for cryptographic production use without additional review.

---

## Project Structure

```
factorise/
├── src/factorise/
│   ├── __init__.py       # Public API exports
│   ├── core.py           # Algorithms, config, result types, validation
│   └── cli.py            # Typer CLI, display helpers, signal handlers
├── tests/
│   ├── test_core.py      # Core algorithm unit tests (225+ cases)
│   ├── test_cli.py      # CLI integration tests
│   └── test_coverage_gap.py  # Edge-case and concurrency tests
├── benchmarks/          # Latency and throughput benchmarks
├── docs/                # Detailed algorithm documentation (Mathematical notes)
│   ├── miller_rabin.md
│   ├── pollards_rho.md
│   └── pollards_rho_brent.md
├── .github/workflows/ci.yml  # GitHub Actions pipeline
├── .env.example         # Environment variable template
└── pyproject.toml       # Hatch build config, dependencies, tool settings
```

---

## Contributing

1. **Fork and branch:** Use feature branches; `master` is the integration branch.
2. **Style:** All code passes `ruff check` and `ruff format`. All public functions carry PEP 484 type hints.
3. **Tests:** All new functionality requires tests. PRs with failing tests will not be merged. Coverage must not regress.
4. **Docstrings:** Google-style docstrings required on all public functions and classes.
5. **Commits:** Conventional commits are not enforced, but messages should describe _why_, not _what_.
6. **No global state:** Configuration is always passed explicitly; no module-level mutable state.

### Adding a New Algorithm

1. Implement as a plain function in `core.py`; accept `FactoriserConfig` if tuneable.
2. Return a factor or raise `RuntimeError` — do not return `None` silently on failure.
3. Add tests covering correct output, edge cases, and failure modes in `test_core.py`.
4. Export from `__init__.py` if it is part of the public API.
5. Verify `ruff check`, `ruff format`, and `mypy src/` all pass.

---

## Versioning & Releases

**Strategy:** [Semantic Versioning (SemVer)](https://semver.org/).

- `MAJOR` version: Breaking changes to the public API.
- `MINOR` version: New backwards-compatible functionality.
- `PATCH` version: Bug fixes with no API changes.

**Release process:**

1. Update `__version__` in `src/factorise/__init__.py`.
2. Update `CHANGELOG.md` with changes since last release.
3. Create a signed tag: `git tag -s vX.Y.Z -m "Release X.Y.Z"`.
4. Build and publish: `pip build && twine upload dist/*`.

---

## Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Pure Python, no C extensions | Slower than GMP-based alternatives on very large numbers (>10^20) | Use `gmpy2` or `sympy` for large inputs |
| Recursive `_factor_yield` | Numbers with many small factors may approach `sys.getrecursionlimit()` | Increase recursion limit: `sys.setrecursionlimit(10_000)` |
| Negative CLI input | `typer` interprets leading `-` as an option flag; negatives cannot be passed directly | Use the library API or `--` separator |
| Probabilistic algorithm | Pollard-Brent is probabilistic per attempt; pathological inputs may need tuning | Increase `max_retries` or `max_iterations` in `FactoriserConfig` |
| Not cryptographically reviewed | No constant-time operations or side-channel hardening | Intended for mathematical/educational use only |

---

## License

MIT License. See [LICENSE](LICENSE).