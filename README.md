# factorise

[![Build Status](https://github.com/sachin/factorise/actions/workflows/ci.yml/badge.svg)](https://github.com/sachin/factorise/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Coverage Status](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](https://github.com/sachin/factorise)
[![Code Style: Google](https://img.shields.io/badge/code%20style-google-3666d6.svg)](https://google.github.io/styleguide/pyguide.html)

A pure-Python library for deterministic prime factorisation of arbitrary integers,
built on two well-established algorithms: **Miller-Rabin** primality testing and
**Pollard's Rho (Brent's improvement)** for factor finding.

Supports Python 3.10+. Installable, importable, and accessible via CLI.

---

## Overview

`factorise` solves the problem of decomposing any integer into its prime factors,
quickly and correctly, for numbers that are large enough to make trial division
impractical.

It can be used:

- As a Python library in any project requiring prime decomposition
- As a command-line tool for interactive or scripted use
- As a reference implementation of the Pollard-Brent algorithm in pure Python

---

## Architecture

The library is organised as a single cohesive module with a layered design:

```
Input validation
      │
      ▼
Miller-Rabin primality test  ◄──── used throughout factorisation
      │
      ▼
Pollard-Brent (one attempt)
      │
      ▼
Pollard-Brent (with retries)  ◄── uses fresh random seeds on failure
      │
      ▼
factor_flatten (recursive splitter)
      │
      ▼
factorise()  ──────────────────────► FactorisationResult
```

Configuration (`FactoriserConfig`) is passed explicitly through the call chain —
there is no global state.

---

## System Components

### `FactorisationResult`

A frozen dataclass that is the single, typed return value of `factorise()`.

| Attribute  | Type            | Description                                        |
|------------|-----------------|----------------------------------------------------|
| `original` | `int`           | The original input value                           |
| `sign`     | `int`           | `1` for non-negative, `-1` for negative            |
| `factors`  | `list[int]`     | Sorted unique prime factors, e.g. `[2, 3]` |
| `powers`   | `dict[int, int]`| Maps each prime to its exponent, e.g. `{2: 2, 3: 1}` |
| `is_prime` | `bool`          | `True` if the original number is prime             |

**Method:**

```python
result.expression()  # → '2^2 * 3'  or  '-1 * 2^2 * 3'
```

---

### `FactoriserConfig`

A frozen dataclass controlling all algorithm parameters.
Constructed directly or loaded from environment variables via `from_env()`.

| Parameter        | Env Variable                  | Type  | Default      | Description                                           |
|------------------|-------------------------------|-------|--------------|-------------------------------------------------------|
| `batch_size`     | `FACTORISE_BATCH_SIZE`        | `int` | `128`        | GCD operations batched per iteration (throughput)     |
| `max_iterations` | `FACTORISE_MAX_ITERATIONS`    | `int` | `10_000_000` | Hard cap on inner steps per Pollard-Brent attempt     |
| `max_retries`    | `FACTORISE_MAX_RETRIES`       | `int` | `20`         | Fresh random seeds to try before raising `RuntimeError` |

All fields are validated immediately at construction — invalid values raise `ValueError`.

---

## Algorithms

### Miller-Rabin Primality Test

Miller-Rabin is a probabilistic primality test that, when given a carefully
chosen fixed set of witnesses, becomes **fully deterministic** for all integers
below a proven bound.

**How it works:**

Given an odd integer `n > 1`, write `n − 1 = 2^s * d` where `d` is odd.
For each witness `a`:

1. Compute `x = a^d mod n`
2. If `x == 1` or `x == n − 1`, this witness passes — continue to the next
3. Square `x` up to `s − 1` times:
   - If `x == n − 1` at any point, this witness passes
   - If the loop ends without finding `n − 1`, `n` is **composite**
4. If all witnesses pass, `n` is **prime**

**Witness set used:**

```
{2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37}
```

This set is provably sufficient to make the test **deterministic for all
n < 2^64** (Jaeschke, 1993; Sorenson & Webster, 2015).

**Complexity:** `O(k log² n)` where `k` is the number of witnesses.

---

### Pollard's Rho — Brent's Improvement

Pollard's Rho is a randomised integer factorisation algorithm based on cycle
detection in a pseudo-random sequence. Brent's improvement makes it more
efficient by using a different cycle-detection strategy and batching GCD
operations to reduce the number of modular arithmetic calls.

**Complexity:** `O(n^{1/4})` per successful attempt on average.

---

## Detailed Algorithm Documentation

For a deep-dive into the mathematical derivations and implementation nuances:

- [Miller–Rabin Primality Testing](docs/miller_rabin.md)
- [Pollard’s Rho Factorization](docs/pollards_rho.md)
- [Brent’s Improved Factorization](docs/pollards_rho_brent.md)
- [Bibliography & References](docs/references.md)

---

## Installation

```bash
# Install from source
pip install .

# Install with development tools
pip install ".[dev]"
```

**Runtime dependencies:**

| Package  | Version  | Purpose                          |
|----------|----------|----------------------------------|
| `typer`  | `≥ 0.9`  | CLI framework                    |
| `rich`   | `≥ 13.0` | Terminal output formatting       |
| `loguru` | `≥ 0.7`  | Structured logging               |

**Requires:** Python 3.10+

---

## Usage

### CLI

```bash
# Factorise a number
factorise 123456789

# Show the full prime product expression
factorise 123456789 --verbose

# Enable debug logging
factorise 123456789 --log-level DEBUG

# Show help
factorise --help
```

**Example output:**

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

---

### Library

```python
from factorise import factorise, FactoriserConfig, FactorisationResult

# Use defaults (reads from environment variables)
result = factorise(123456789)

# Or pass an explicit config
config = FactoriserConfig(batch_size=256, max_retries=30)
result = factorise(123456789, config)

print(result.factors)     # [3, 3607, 3803]
print(result.powers)      # {3: 2, 3607: 1, 3803: 1}
print(result.is_prime)    # False
print(result.expression()) # '3^2 * 3607 * 3803'
```

**Primality check:**

```python
from factorise.core import is_prime

is_prime(2**31 - 1)   # True  (Mersenne prime M31)
is_prime(100)          # False
```

**Handling errors:**

```python
from factorise import factorise

try:
    result = factorise(n)
except TypeError as e:
    # n was not a plain int (bool, float, str, etc.)
    ...
except RuntimeError as e:
    # Factorisation exhausted all retries — increase max_retries or max_iterations
    ...
```

---

## Configuration

All algorithm parameters can be set via environment variables.
They are validated at `FactoriserConfig` construction time.

```bash
# Tune GCD batch size (higher = fewer GCD calls, more multiplication)
export FACTORISE_BATCH_SIZE=256

# Raise the per-attempt iteration cap for very large numbers
export FACTORISE_MAX_ITERATIONS=50000000

# Allow more random seed retries before giving up
export FACTORISE_MAX_RETRIES=50

# Set CLI log verbosity (DEBUG, INFO, WARNING, ERROR)
export FACTORISE_LOG_LEVEL=INFO
```

Or construct the config in code:

```python
from factorise import FactoriserConfig

config = FactoriserConfig(
    batch_size=256,
    max_iterations=50_000_000,
    max_retries=50,
)
```

---

## Project Structure

```
factorise/
├── docs/                       # Detailed algorithm documentation
│   ├── miller_rabin.md
│   ├── pollards_rho.md
│   └── pollards_rho_brent.md
├── benchmarks/                 # Latency and memory benchmarks
├── pyproject.toml              # Project metadata and dependencies
├── README.md                   # This file
├── src/
│   └── factorise/
│       ├── __init__.py         # Public API exports
│       ├── core.py             # Algorithms, config, and result types
│       └── cli.py              # Typer-based CLI
└── tests/
    ├── test_core.py            # Core algorithm tests (225+ cases)
    ├── test_cli.py             # CLI integration tests
    └── test_coverage_gap.py    # Exhaustive edge-case validation
```

### Key files

| File            | Responsibility                                               |
|-----------------|--------------------------------------------------------------|
| `core.py`       | All mathematical logic, config, and typed result dataclass   |
| `cli.py`        | CLI entry point; display helpers; signal handling            |
| `__init__.py`   | Exports `factorise`, `is_prime`, `FactorisationResult`, `FactoriserConfig` |

---

## Operational Notes

### Logging

Logging is powered by `loguru` and is **disabled by default** to avoid noise
in library contexts. Callers opt into logging explicitly.

**CLI:** pass `--log-level` or set `FACTORISE_LOG_LEVEL`.

**Library:**

```python
from loguru import logger

logger.enable("factorise")
logger.add("factorise.log", level="DEBUG")
```

**Events logged:**

| Level     | Event                                                        |
|-----------|--------------------------------------------------------------|
| `INFO`    | `factorise` start and completion with factor list            |
| `DEBUG`   | Each Pollard-Brent attempt, seed values, and each split      |
| `WARNING` | Iteration cap or backtrack cap reached (attempt abandoned)   |
| `ERROR`   | Invalid input or factorisation failure (CLI only)            |

### Error Handling

| Exception      | Cause                                                              |
|----------------|--------------------------------------------------------------------|
| `TypeError`    | Input is not a plain `int` (e.g. `bool`, `float`, `str`)         |
| `ValueError`   | `FactoriserConfig` receives an out-of-range parameter              |
| `RuntimeError` | Factorisation failed after exhausting `max_retries` attempts       |

Errors are never silently swallowed. All exceptions preserve their full stack trace.

### Graceful Shutdown (CLI)

The CLI registers handlers for `SIGINT` and `SIGTERM`. On either signal,
it logs the event and exits cleanly with code `0`.

---

## Development

### Setup

```bash
# Install in editable mode with dev tools
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run the full suite
python3 -m pytest -p no:asyncio tests/ -v

# Run with coverage
pytest --cov=factorise --cov-report=term-missing tests/
```

### Coding Standards

- **Style:** PEP 8, enforced by `pylint` and `black`
- **Types:** All public functions carry complete type annotations
- **Docstrings:** Google style, required on all public functions and classes
- **No booleans or floats as integers:** `validate_int()` enforces plain `int` only
- **No global state:** configuration is always passed explicitly

### Adding a New Algorithm

1. Implement the algorithm as a plain function in `core.py`
2. Accept `FactoriserConfig` as a parameter if it needs tuneable limits
3. Return a factor or raise `RuntimeError` — never return silently on failure
4. Add tests in `tests/test_core.py` covering correct output, edge cases, and failure modes
5. Export from `__init__.py` if it is part of the public API

---

## Limitations

- **Pure Python:** no C extensions. For maximum throughput on very large numbers (> 10^20), consider `gmpy2` or `sympy`.
- **Recursion depth:** `factor_flatten` is recursive. Numbers with many small factors may approach Python's default recursion limit (`sys.setrecursionlimit`).
- **Negative CLI input:** `typer` interprets a leading `-` as an option flag. Negative integers cannot currently be passed directly as CLI arguments.
- **Randomised algorithm:** Pollard-Brent is probabilistic per attempt. Correctness is guaranteed through retries and bounded iteration, but pathological inputs may require increasing `max_retries`.
- **Not a cryptographic tool:** this library is intended for mathematical and educational use. It does not implement constant-time operations or side-channel protections.

---

## License

MIT
