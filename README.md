# factorise

[![CI](https://github.com/sachn-cs/factorise/actions/workflows/ci.yml/badge.svg)](https://github.com/sachn-cs/factorise/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/downloads/)

Deterministic prime factorisation for Python using Miller-Rabin primality testing and a multi-stage factorisation pipeline supporting Trial Division, Pollard's p−1, Pollard's Rho (Brent), ECM, Quadratic Sieve, and a GNFS adapter for very large inputs.

## 1. Project Overview

`factorise` provides:
- A library API for prime decomposition of signed integers.
- Deterministic primality checks for all `n < 2^64`.
- Bounded retry/iteration controls to avoid unbounded runtime.
- A configurable multi-stage pipeline that escalates from fast to powerful algorithms.
- A CLI for operational use and debugging.

Multi-stage factorisation pipeline order:

```
validate_int
  -> is_prime (Miller-Rabin)
  -> Pipeline (stages in order)
       1. Trial Division  (small primes, O(π(b)))
       2. Pollard p−1       (smooth factors, p−1 method)
       3. Pollard's Rho     (Brent variant, general-purpose)
       4. ECM               (Elliptic Curve Method, medium factors)
       5. Quadratic Sieve   (medium-to-large, up to ~100 digits)
       6. GNFS              (external adapter, very large inputs)
  -> factorise()
```

Key capabilities:
- `factorise(n, config=None)` returns a structured `FactorisationResult`.
- `is_prime(n)` is available as a standalone function.
- Optional reproducibility via `seed` / `FACTORISE_SEED`.
- CLI with validated log levels.
- **Pipeline mode**: set `config.use_pipeline = True` or `FACTORISE_USE_PIPELINE=1`
  to use the multi-stage pipeline instead of direct Pollard-Brent.

## 2. Quick Start

```bash
# Install
pip install factorise

# Using the library (requires Python 3.14+)
python -c "from source import factorise; print(factorise(123456789).expression())"

# Using the CLI
factorise 123456789 --verbose

# Using the pipeline mode (recommended for large composites)
from source import FactoriserConfig
config = FactoriserConfig(use_pipeline=True)
result = factorise(123456789, config)
```

## 3. Repository Structure

```text
source/
  __init__.py     Public exports and version.
  core.py         Algorithms, config, validation, domain exceptions.
  pipeline.py     Multi-stage pipeline, FactorStage interface, PipelineConfig.
  stages/
    pollard_rho.py   Pollard-Rho (Brent) stage.
    ecm.py           Elliptic Curve Method stage.
    quadratic_sieve.py  Quadratic Sieve stage.
    gnfs.py          GNFS external tool adapter stage.
  cli.py          CLI command, display, logging, signal handling.
  py.typed        PEP 561 marker.

tests/
  conftest.py               Shared test constants.
  test_core_config.py       Config, model, and validation behavior.
  test_core_primality.py    Primality behavior and edge cases.
  test_core_factorisation.py Factorisation semantics and determinism.
  test_core_pollard.py      Pollard-Brent and flattening behavior.
  test_core_edge_cases.py   Internal algorithm edge paths.
  test_pipeline.py          Multi-stage pipeline tests.
  test_cli.py               CLI user behavior.
  test_cli_errors.py        CLI error and logging-mode behavior.

benchmarks/
  timing.py       Timing benchmarks.
  memory.py       Allocation/memory benchmarks.
  stress.py       Process-based stress checks and CI gate.
  inputs.py       Shared benchmark datasets.

.github/workflows/ci.yml
  Lint, typecheck, tests, stress gate, security audit, build/release checks.
```

## 4. Multi-Stage Pipeline

The pipeline (`FactorisationPipeline`) coordinates multiple factorisation algorithms,
each as a `FactorStage`. Stages are tried in order until one finds a factor;
the pipeline then recurses on both the factor and co-factor until everything
is prime.

### Stage: Trial Division

Finds small prime factors by testing divisibility against a fixed list of small
primes (up to 229 by default). Very fast for numbers with small factors.

### Stage: Pollard p−1

Finds factors `p` where `p−1` is smooth (has only small prime factors). Uses
stage 1 of Pollard's p−1 method: compute `a^B mod n` for smoothness bound `B`,
then `gcd(a^B − 1, n)`. Effective as an intermediate stage between trial division
and Pollard's Rho.

### Stage: Pollard's Rho (Brent)

General-purpose factorisation using Brent's improvement to Pollard's Rho algorithm.
Batches GCD computations for throughput. The primary workhorse for small-to-medium
composites. Exposed via `PollardRhoStage`.

### Stage: ECM (Elliptic Curve Method)

Modern general-purpose factorisation using elliptic curve operations. Most effective
for finding factors in the 10–40 digit range. Runs a configurable number of curves
(each with a different random curve). Exposed via `ECMStage`.

### Stage: Quadratic Sieve

Fast for medium-to-large inputs up to ~100 digits. This simplified implementation
is suitable for educational purposes and medium-sized inputs. Exposed via
`QuadraticSieveStage`.

### Stage: GNFS (General Number Field Sieve)

Full in-repo adapter wrapping external GNFS tools (msieve, CADO-NFS) with strict
isolation: input validation, timeout handling, output parsing, and failure
isolation. Silently skipped if the binary is not on PATH. For very large inputs
(~100+ digits). Exposed via `GNFSStage`.

## 5. Configuration

`PipelineConfig` controls the pipeline:

```python
from source.pipeline import PipelineConfig, FactorisationPipeline

config = PipelineConfig(
    bound_small=10**12,      # Skip p-1/ECM below this
    bound_medium=10**20,     # Skip ECM above this
    bound_large=10**40,      # Skip QS above this
    trial_division_bound=10_000,
    pm1_bound=10**6,
    ecm_curves=20,
    gnfs_timeout=600,
    gnfs_binary="msieve",
    max_iterations=10_000_000,
    max_retries=20,
    batch_size=128,
    seed=None,
    stage_order=(
        "trial_division",
        "pollard_pminus1",
        "pollard_rho",
        "ecm",
        "quadratic_sieve",
        "gnfs",
    ),
)
pipeline = FactorisationPipeline(config)
```

Environment variables (`FACTORISE_*`):

- `FACTORISE_BOUND_SMALL`, `FACTORISE_BOUND_MEDIUM`, `FACTORISE_BOUND_LARGE`,
  `FACTORISE_BOUND_XLARGE` — size thresholds per stage.
- `FACTORISE_TRIAL_DIVISION_BOUND` — trial division prime ceiling.
- `FACTORISE_PM1_BOUND` — Pollard p−1 smoothness bound.
- `FACTORISE_ECM_CURVES` — number of ECM curves to try.
- `FACTORISE_GNFS_TIMEOUT` — GNFS subprocess timeout in seconds.
- `FACTORISE_GNFS_BINARY` — GNFS binary name/path.
- `FACTORISE_BATCH_SIZE`, `FACTORISE_MAX_ITERATIONS`, `FACTORISE_MAX_RETRIES` —
  Pollard-Brent parameters.
- `FACTORISE_SEED` — deterministic seed.
- `FACTORISE_USE_PIPELINE` — set to `1`/`true`/`yes` to enable pipeline mode.

## 6. API Reference

### Library

```python
from source import factorise, is_prime, FactorisationResult
from source import FactoriserConfig
from source import FactorisationPipeline, PipelineConfig
from source import StageResult, StageStatus, FactorStage

# Basic usage
result = factorise(123456789)
print(result.factors)   # [3, 3607, 3803]
print(result.powers)   # {3: 2, 3607: 1, 3803: 1}
print(result.expression())  # '3^2 * 3607 * 3803'

# Pipeline mode
config = FactoriserConfig(use_pipeline=True)
result = factorise(123456789, config)

# Direct pipeline usage
pipeline = FactorisationPipeline()
stage_result = pipeline.attempt(123456789, config=FactoriserConfig())
print(stage_result.status)   # StageStatus.SUCCESS
print(stage_result.factor)   # 3

# Primality testing
is_prime(97)  # True
```

### CLI

```bash
factorise 123456789
factorise 123456789 --verbose
factorise 123456789 --log-level INFO
factorise 123456789 --log-format json
```

## 7. Testing

Primary test commands:

```bash
pytest tests/ -v
pytest --cov=source --cov-fail-under=90 tests/
pytest -v benchmarks/stress.py::test_stress_correctness
pytest -q tests/test_core_primality.py
pytest -q tests/test_cli_errors.py
pytest -q tests/test_pipeline.py
```

Test strategy:
- Unit tests: correctness, edge cases, API behavior.
- Pipeline tests: multi-stage integration, stage ordering, fallback behavior.
- Integration tests: CLI paths and error handling.
- Property tests: invariants across broad integer ranges.
- Stress tests: deterministic correctness at scale.
- Test modules are organized by domain to reduce navigation friction.

## 8. Linting / Formatting / Type Checking

```bash
just lint
just format
just type-check
```

Or directly:

```bash
ruff check source/ tests/ benchmarks/
ruff format source/ tests/ benchmarks/
mypy source/ tests/ benchmarks/
```

Pre-commit:

```bash
pre-commit install
pre-commit run --all-files
```

CI enforces these checks and publishes JUnit artifacts for test jobs.

Documentation:
- Algorithm notes are maintained as curated narrative docs under `docs/`.

## 9. Architecture Notes

Design choices:
- Immutable config (`FactoriserConfig`, `PipelineConfig`) for reproducible and testable behavior.
- Explicit domain failure (`FactorisationError`) for exhausted compute budgets.
- `FactorStage` abstract interface for composable, replaceable stages.
- `StageResult` structured output for observability and debugging.
- Generator-based recursive splitting (`_factor_yield`, `_factor_yield_pipeline`) to keep memory bounded.
- Pipeline mode is opt-in via `use_pipeline=True` or `FACTORISE_USE_PIPELINE=1`
  to preserve full backward compatibility.

Scalability and safety:
- `max_iterations` and `max_retries` constrain worst-case runtime.
- Trial division and perfect-square fast paths reduce heavy-path pressure.
- GNFS adapter with strict input validation, timeout, and output parsing.
- No unsafe shell execution; external tool inputs are sanitized.

## 10. Logging / Troubleshooting

Logging model:
- Library logger is disabled by default for quiet embedding.
- CLI enables logging and validates allowed levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
- Human-readable logging remains the default.
- JSON mode emits one JSON object per line with operational fields.
- Stage-level logging includes: `stage`, `n`, `factor`, `status`, `reason`, `elapsed_ms`.

Stage result statuses:
- `SUCCESS`: stage found a non-trivial factor.
- `FAILURE`: stage ran but could not find a factor.
- `SKIPPED`: stage was not applicable (input too small/large, binary not found, etc.).

Troubleshooting:
- `TypeError` on input: ensure plain `int` values (no `bool`, `float`, `str`).
- `FactorisationError`: increase retry/iteration budget, enable pipeline mode,
  or set deterministic seed for reproduction.
- GNFS always skipped: ensure `msieve` or `cado-nfs` is on PATH.
- Wrong factors: enable DEBUG logging to see which stage found each factor.

## 11. Future Enhancements

- Add full in-repo GNFS implementation.
- Add parallel ECM curve execution.
- Add generated API reference docs if external integration demand increases.
- Add periodic benchmark trend checks in CI for regression detection.

## 12. Contribution Standards

- Work in-place; avoid parallel implementations.
- Keep imports, naming, and docstrings consistent with Google-style conventions.
- Add tests for behavior changes, especially error paths and edge cases.
- Run `just ci` (or `just ci-full`) before opening a PR.
- Keep comments high-value: explain intent, assumptions, and tradeoffs.
- Release flow on version tags uses trusted publishing (OIDC) and produces:
  - package artifacts (sdist/wheel)
  - `dist/SHA256SUMS` integrity file
  - `dist/sbom.cdx.json` CycloneDX SBOM artifact

See `CONTRIBUTING.md` and `SECURITY.md` for policy details.
