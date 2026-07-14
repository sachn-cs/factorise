<p align="center">
  <h1 align="center">factorise</h1>
  <p align="center">Deterministic prime factorisation using Miller-Rabin and a multi-stage factorisation pipeline.</p>
  <p align="center">
    <a href="#installation"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
    <a href="https://github.com/sachncs/factorise/actions"><img src="https://img.shields.io/github/actions/workflow/status/sachncs/factorise/ci.yml?branch=master" alt="CI"></a>
    <a href="https://pypi.org/project/factorise/"><img src="https://img.shields.io/pypi/v/factorise" alt="PyPI"></a>
    <a href="https://github.com/sachncs/factorise/stargazers"><img src="https://img.shields.io/github/stars/sachncs/factorise" alt="Stars"></a>
  </p>
</p>

**factorise** is a Python SDK that performs deterministic prime factorisation
of integers using Miller-Rabin primality testing and a multi-stage factorisation
pipeline. It escalates from fast algorithms (Trial Division) to powerful ones
(ECM, Quadratic Sieve, SIQS) and ships with an adaptive hybrid engine that
chooses the right algorithm based on input size.

---

## Features

- **Zero runtime dependencies** — all algorithms implemented from scratch using only the Python standard library.
- **Multi-stage pipeline** — escalates from fast to powerful algorithms: Trial Division, Pollard p-1, Pollard's Rho (Brent), ECM, Quadratic Sieve, SIQS, and GNFS adapter.
- **Deterministic primality** — verified for all `n < 2^64` using Miller-Rabin.
- **Hybrid engine** — adaptive algorithm selection based on input size.
- **CLI tool** — operational use and debugging with structured logging.
- **Reproducible results** — optional deterministic seeding for Pollard-Brent retries.
- **Configurable** — environment variables or programmatic configuration.
- **Type-safe** — full type hints (PEP 484) and PEP 561 marker.

---

## Installation

### From PyPI

```bash
pip install factorise
```

### From source

```bash
git clone https://github.com/sachncs/factorise.git
cd factorise
pip install -e ".[dev]"
```

---

## Quick Start

### CLI

```bash
factorise 123456789
factorise 123456789 --verbose
factorise 123456789 --log-level INFO
```

### Python API

```python
from factorise import factorise, is_prime

result = factorise(123456789)
print(result.factors)       # [3, 3607, 3803]
print(result.powers)        # {3: 2, 3607: 1, 3803: 1}
print(result.expression())  # '3^2 * 3607 * 3803'

is_prime(97)  # True
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

---

## Configuration

All variables use the `FACTORISE_*` prefix. See [`.env.example`](.env.example) for a complete list.

| Setting | Env Variable | Default | Description |
|---------|--------------|---------|-------------|
| Log level | `FACTORISE_LOG_LEVEL` | `WARNING` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| Log format | `FACTORISE_LOG_FORMAT` | `human` | Log output format |
| Batch size | `FACTORISE_BATCH_SIZE` | `128` | GCD operations to batch per iteration |
| Max iterations | `FACTORISE_MAX_ITERATIONS` | `10000000` | Hard cap on inner steps per attempt |
| Max retries | `FACTORISE_MAX_RETRIES` | `20` | Fresh random seeds to try before giving up |
| Seed | `FACTORISE_SEED` | — | Optional deterministic seed for reproducible retries |
| Trial division bound | `FACTORISE_TRIAL_DIVISION_BOUND` | `10000` | Upper prime value for trial division |
| PM1 bound | `FACTORISE_PM1_BOUND` | `1000000` | Smoothness bound for Pollard p-1 |
| ECM curves | `FACTORISE_ECM_CURVES` | `20` | Number of ECM curves to try |
| GNFS timeout | `FACTORISE_GNFS_TIMEOUT` | `600` | GNFS subprocess timeout in seconds |
| GNFS binary | `FACTORISE_GNFS_BINARY` | `msieve` | GNFS binary name/path |

### Programmatic Configuration

```python
from factorise import FactoriserConfig, PipelineConfig

config = FactoriserConfig(
    batch_size=256,
    max_iterations=5_000_000,
    seed=42,
)
```

---

## API

| Symbol | Type | Description |
|--------|------|-------------|
| `factorise(n)` | function | Factor integer `n` and return a `FactorisationResult` |
| `is_prime(n)` | function | Deterministic Miller-Rabin primality test for `n < 2^64` |
| `FactorisationPipeline(config)` | class | Multi-stage factorisation pipeline |
| `PipelineConfig` | dataclass | Pipeline tuning (trial bound, PM1 bound, ECM curves, …) |
| `HybridFactorisationEngine(config)` | class | Adaptive engine selecting algorithm by input size |
| `HybridConfig` | dataclass | Hybrid engine thresholds and limits |
| `FactoriserConfig` | dataclass | Core factorisation settings (batch size, retries, seed) |
| `FactorisationResult` | dataclass | Result carrying `.factors`, `.powers`, `.expression()` |

---

## Examples

```python
from factorise import factorise, FactorisationPipeline, PipelineConfig

# Basic factorisation
result = factorise(60)
print(result.expression())  # '2^2 * 3 * 5'

# Multi-stage pipeline
pipeline = FactorisationPipeline(PipelineConfig(ecm_curves=50))
result = pipeline.attempt(10**18 + 9)
```

---

## Project Structure

```
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
└── pyproject.toml
```

---

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check factorise/ tests/ benchmarks/
ruff format factorise/ tests/ benchmarks/
mypy factorise/
```

The project uses [just](https://github.com/casey/just) as a task runner. Equivalent commands:

```bash
just install          # or: pip install -e ".[dev]"
just build            # or: python -m build
just test             # or: pytest tests/ -v
just test-ci          # pytest with coverage enforcement (≥90%)
just lint             # or: ruff check factorise/ tests/ benchmarks/
just format           # or: ruff format factorise/ tests/ benchmarks/
just type-check       # or: mypy factorise/ tests/ benchmarks/
just ci               # lint + type-check + test-ci
just ci-full          # ci + security + stress-test
```

---

## Testing

```bash
pytest
```

---

## Build

```bash
python -m build
```

---

## Release

Versions follow [Semantic Versioning](https://semver.org/). Releases are tagged
via `version:X.Y.Z` commits in [CHANGELOG.md](CHANGELOG.md) and published to
PyPI via the CI workflow.

---

## Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.10+ |
| Build | Hatchling |
| Linting | Ruff |
| Type Checking | mypy (strict) |
| Testing | pytest, Hypothesis |
| CI/CD | GitHub Actions |
| Task Runner | just |
| Security | pip-audit, CycloneDX SBOM |

---

## Roadmap

- Full in-repo GNFS implementation
- Parallel ECM curve execution
- Generated API reference docs
- Periodic benchmark trend checks in CI
- WebAssembly (Pyodide) support
- Additional factorisation algorithms (Lenstra's ECM variant, MPQS)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on development setup,
branch naming, commit conventions, and PR process.

## Code of Conduct

This project follows the [Contributor Covenant v2.1](CODE_OF_CONDUCT.md).

## Security

Report vulnerabilities to **sachncs@gmail.com** — see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © 2026 Sachin
