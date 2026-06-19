# factorise

[![CI](https://github.com/sachn-cs/factorise/actions/workflows/ci.yml/badge.svg)](https://github.com/sachn-cs/factorise/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/sachn-cs/factorise/branch/master/graph/badge.svg)](https://codecov.io/gh/sachn-cs/factorise)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/factorise.svg)](https://pypi.org/project/factorise/)
[![PyPI version](https://img.shields.io/pypi/v/factorise.svg)](https://pypi.org/project/factorise/)
[![Downloads](https://img.shields.io/pypi/dm/factorise.svg)](https://pypi.org/project/factorise/)
[![Security Policy](https://img.shields.io/badge/Security-MIT-red.svg)](SECURITY.md)

Deterministic prime factorisation for Python using Miller-Rabin primality testing and a multi-stage factorisation pipeline.

## Features

- **Zero runtime dependencies** — all algorithms implemented from scratch using only the Python standard library
- **Multi-stage pipeline** — escalates from fast to powerful algorithms: Trial Division, Pollard p-1, Pollard's Rho (Brent), ECM, Quadratic Sieve, SIQS, and GNFS adapter
- **Deterministic primality** — verified for all `n < 2^64` using Miller-Rabin
- **Hybrid engine** — adaptive algorithm selection based on input size
- **CLI tool** — operational use and debugging with structured logging
- **Reproducible results** — optional deterministic seeding for Pollard-Brent retries
- **Configurable** — environment variables or programmatic configuration
- **Type-safe** — full type hints (PEP 484) and PEP 561 marker

## Installation

```bash
pip install factorise
```

Or install from source:

```bash
git clone https://github.com/sachn-cs/factorise.git
cd factorise
pip install -e ".[dev]"
```

## Usage

### Library API

```python
from factorise import factorise, is_prime

# Factorise a number
result = factorise(123456789)
print(result.factors)       # [3, 3607, 3803]
print(result.powers)        # {3: 2, 3607: 1, 3803: 1}
print(result.expression())  # '3^2 * 3607 * 3803'

# Check primality
is_prime(97)  # True
```

### CLI

```bash
factorise 123456789
factorise 123456789 --verbose
factorise 123456789 --log-level INFO
```

### Pipeline

```python
from factorise import FactorisationPipeline, PipelineConfig

config = PipelineConfig(
    trial_division_bound=10_000,
    pm1_bound=10**6,
    ecm_curves=20,
)
pipeline = FactorisationPipeline(config)
result = pipeline.attempt(123456789)
```

### Hybrid Engine

```python
from factorise import HybridConfig, HybridFactorisationEngine

engine = HybridFactorisationEngine(HybridConfig())
result = engine.attempt(123456789)
```

## Configuration

### Environment Variables

All variables use the `FACTORISE_*` prefix. See [`.env.example`](.env.example) for a complete list.

| Variable | Default | Description |
|----------|---------|-------------|
| `FACTORISE_LOG_LEVEL` | `WARNING` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `FACTORISE_LOG_FORMAT` | `human` | Log output format |
| `FACTORISE_BATCH_SIZE` | `128` | GCD operations to batch per iteration |
| `FACTORISE_MAX_ITERATIONS` | `10000000` | Hard cap on inner steps per attempt |
| `FACTORISE_MAX_RETRIES` | `20` | Fresh random seeds to try before giving up |
| `FACTORISE_SEED` | — | Optional deterministic seed for reproducible retries |
| `FACTORISE_TRIAL_DIVISION_BOUND` | `10000` | Upper prime value for trial division |
| `FACTORISE_PM1_BOUND` | `1000000` | Smoothness bound for Pollard p-1 |
| `FACTORISE_ECM_CURVES` | `20` | Number of ECM curves to try |
| `FACTORISE_GNFS_TIMEOUT` | `600` | GNFS subprocess timeout in seconds |
| `FACTORISE_GNFS_BINARY` | `msieve` | GNFS binary name/path |

### Programmatic Configuration

```python
from factorise import FactoriserConfig, PipelineConfig

config = FactoriserConfig(
    batch_size=256,
    max_iterations=5_000_000,
    seed=42,
)
```

## Project Structure

```text
factorise/
├── factorise/           # Main package
│   ├── __init__.py      # Public exports and version
│   ├── core.py          # Algorithms, validation, domain exceptions
│   ├── config.py        # Configuration dataclasses with validation
│   ├── pipeline.py      # Multi-stage pipeline, FactorStage interface
│   ├── hybrid.py        # Adaptive hybrid engine with threshold routing
│   ├── cli.py           # CLI command, display, logging, signal handling
│   ├── utils.py         # Shared utilities (prime sieve)
│   ├── py.typed         # PEP 561 marker
│   └── stages/          # Pluggable algorithm stages
│       ├── trial_division.py
│       ├── improved_pm1.py
│       ├── pollard_rho.py
│       ├── ecm.py
│       ├── ecm_two_pass.py
│       ├── ecm_shared.py
│       ├── quadratic_sieve.py
│       ├── siqs.py
│       ├── qs_shared.py
│       └── gnfs_optimized.py
├── tests/               # Test suite (90%+ coverage)
├── benchmarks/          # Timing, memory, and stress benchmarks
├── docs/                # Algorithm documentation
└── .github/             # CI/CD workflows and templates
```

## Development

### Prerequisites

- Python 3.10+
- [just](https://github.com/casey/just) task runner (recommended)

### Commands

```bash
# Install dependencies
just install          # or: pip install -e ".[dev]"

# Development server (not applicable — library only)

# Build
just build            # or: python -m build

# Test
just test             # or: pytest tests/ -v
just test-ci          # pytest with coverage enforcement (≥90%)

# Lint
just lint             # or: ruff check factorise/ tests/ benchmarks/

# Format
just format           # or: ruff format factorise/ tests/ benchmarks/

# Type check
just type-check       # or: mypy factorise/ tests/ benchmarks/

# Full CI suite
just ci               # lint + type-check + test-ci
just ci-full          # ci + security + stress-test
```

### Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| Build | Hatchling |
| Linting | Ruff |
| Type Checking | mypy (strict) |
| Testing | pytest, Hypothesis |
| CI/CD | GitHub Actions |
| Task Runner | just |
| Pre-commit | pre-commit |
| Security | pip-audit, CycloneDX SBOM |

## Roadmap

- [ ] Full in-repo GNFS implementation
- [ ] Parallel ECM curve execution
- [ ] Generated API reference docs
- [ ] Periodic benchmark trend checks in CI
- [ ] WebAssembly (Pyodide) support
- [ ] Additional factorisation algorithms (Lenstra's ECM variant, MPQS)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Development setup
- Branch naming and commit conventions
- Pull request process
- Code quality standards

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards.

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting and security policy.

**Reporting vulnerabilities**: Please email sachncs@gmail.com for any security-related issues. Do not report vulnerabilities through public GitHub issues.

## License

[MIT](LICENSE) © 2026 Sachin
