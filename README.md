# factorise

[![CI](https://github.com/sachn-cs/factorise/actions/workflows/ci.yml/badge.svg)](https://github.com/sachn-cs/factorise/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

Deterministic prime factorisation for Python using Miller-Rabin primality testing and Pollard's Rho (Brent variant), with typed APIs, bounded compute controls, and a CLI.

## 1. Project Overview

`factorise` provides:
- A library API for prime decomposition of signed integers.
- Deterministic primality checks for all `n < 2^64`.
- Bounded retry/iteration controls to avoid unbounded runtime.
- A CLI for operational use and debugging.

High-level flow:

```text
validate_int
  -> is_prime
  -> pollard_brent
     -> pollard_brent_attempt
  -> _factor_yield
  -> factorise -> FactorisationResult
```

Key capabilities:
- `factorise(n, config=None)` returns a structured `FactorisationResult`.
- `is_prime(n)` is available as a standalone function.
- Optional reproducibility via `seed` / `FACTORISE_SEED`.
- CLI with validated log levels.

## 2. Repository Structure

```text
src/factorise/
  __init__.py     Public exports and version.
  core.py         Algorithms, config, validation, domain exceptions.
  cli.py          CLI command, display, logging, signal handling.
  py.typed        PEP 561 marker.

tests/
  conftest.py               Shared test constants.
  test_core_config.py       Config, model, and validation behavior.
  test_core_primality.py    Primality behavior and edge cases.
  test_core_factorisation.py Factorisation semantics and determinism.
  test_core_pollard.py      Pollard-Brent and flattening behavior.
  test_core_edge_cases.py   Internal algorithm edge paths.
  test_core_concurrency.py  Concurrency smoke coverage.
  test_cli.py               CLI user behavior.
  test_cli_errors.py        CLI error and logging-mode behavior.
  test_result_model.py      Result model edge behavior.
  test_properties.py Property-based invariants.

benchmarks/
  timing.py       Timing benchmarks.
  memory.py       Allocation/memory benchmarks.
  stress.py       Process-based stress checks and CI gate.
  inputs.py       Shared benchmark datasets.

.github/workflows/ci.yml
  Lint, typecheck, tests, stress gate, security audit, build/release checks.
```

## 3. Setup Instructions

Prerequisites:
- Python 3.10, 3.11, 3.12, or 3.13.
- `pip` 23+.

Create environment and install:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Optional tooling:
- `just` for command shortcuts (`just --list`).
- `pre-commit` for local hook enforcement.

## 4. Environment Variables

Runtime configuration (used by `FactoriserConfig.from_env()`):

- `FACTORISE_BATCH_SIZE` (default: `128`)
- `FACTORISE_MAX_ITERATIONS` (default: `10000000`)
- `FACTORISE_MAX_RETRIES` (default: `20`)
- `FACTORISE_SEED` (optional deterministic seed)
- `FACTORISE_LOG_LEVEL` (CLI only; default: `WARNING`)
- `FACTORISE_LOG_FORMAT` (`human` or `json`, default: `human`)
- `FACTORISE_REQUEST_ID` (optional, JSON log context)
- `FACTORISE_CORRELATION_ID` (optional, JSON log context)
- `FACTORISE_TRACE_ID` (optional, JSON log context)
- `FACTORISE_SPAN_ID` (optional, JSON log context)
- `FACTORISE_SESSION_ID` (optional, JSON log context)

Bootstrap:

```bash
cp .env.example .env
```

## 5. Running Locally

Library usage:

```python
from factorise import factorise

result = factorise(123_456_789)
print(result.factors)
print(result.powers)
print(result.expression())
```

CLI usage:

```bash
factorise 123456789
factorise 123456789 --verbose
factorise 123456789 --log-level INFO
factorise 123456789 --log-format json
```

common local commands:

```bash
just test
just lint
just type-check
just ci
just ci-full
```

## 6. Testing

Primary test commands:

```bash
pytest tests/ -v
pytest --cov=factorise --cov-fail-under=90 tests/
pytest -v benchmarks/stress.py::test_stress_correctness
pytest -q tests/test_core_primality.py
pytest -q tests/test_cli_errors.py
```

Test strategy:
- Unit tests: correctness, edge cases, API behavior.
- Integration tests: CLI paths and error handling.
- Property tests: invariants across broad integer ranges.
- Stress tests: deterministic correctness at scale.
- Test modules are organized by domain to reduce navigation friction.

## 7. Linting / Formatting / Type Checking

```bash
just lint
just format
just type-check
```

Or directly:

```bash
ruff check src/ tests/ benchmarks/
ruff format src/ tests/ benchmarks/
mypy src/ tests/ benchmarks/
```

Pre-commit:

```bash
pre-commit install
pre-commit run --all-files
```

CI enforces these checks and publishes JUnit artifacts for test jobs.

Documentation:
- Algorithm notes are maintained as curated narrative docs under `docs/`.

## 8. Architecture Notes

Design choices:
- Immutable config (`FactoriserConfig`) for reproducible and testable behavior.
- Explicit domain failure (`FactorisationError`) for exhausted compute budgets.
- Attempt-level status model (`AttemptResult`, `AttemptStatus`) for precise retry logic.
- Generator-based recursive splitting (`_factor_yield`) to keep memory bounded.

Scalability and safety:
- `max_iterations` and `max_retries` constrain worst-case runtime.
- Trial division and perfect-square fast paths reduce heavy-path pressure.

## 9. Logging / Troubleshooting

Logging model:
- Library logger is disabled by default for quiet embedding.
- CLI enables logging and validates allowed levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
- Human-readable logging remains the default.
- JSON mode emits one JSON object per line with operational fields:
  - `timestamp`, `level`, `logger`, `message`, `module`, `function`
  - `line_number`, `process_id`, `thread_id`
  - Optional trace context fields (`request_id`, `correlation_id`, `trace_id`, `span_id`, `session_id`)
  - Structured `exception` payload with type, message, and stacktrace when present.

Troubleshooting:
- `TypeError` on input: ensure plain `int` values (no `bool`, `float`, `str`).
- `FactorisationError`: increase retry/iteration budget or set deterministic seed for reproduction.
- CLI configuration error: fix invalid `--log-level` / `FACTORISE_LOG_LEVEL`.

## 10. Contribution Standards

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

## 11. Future Enhancements

- Add machine-readable log output mode for downstream observability systems.
- Add periodic benchmark trend checks in CI for regression detection.
- Add generated API reference docs if external integration demand increases.
