# Factorise Documentation

This directory contains detailed documentation for the algorithms and usage patterns in the `factorise` library.

## Quick Reference

### CLI Usage

```bash
# Basic factorisation
factorise 123456789

# Verbose output with full expression
factorise 123456789 --verbose

# Custom log level
factorise 123456789 --log-level DEBUG

# JSON logging (for machine consumption)
factorise 123456789 --log-format json
```

### Library API

```python
from factorise import factorise, is_prime, FactoriserConfig

# Simple usage
result = factorise(123456789)
print(result.expression())  # "3^2 * 3607 * 3803"

# Check primality
print(is_prime(7))  # True

# Direct pipeline usage for large composites
from factorise import FactorisationPipeline
pipeline = FactorisationPipeline()
stage_result = pipeline.attempt(123456789)
```

## Algorithm Selection Guide

Choose the right algorithm based on input size and characteristics:

| Input Size | Recommended Algorithm | Notes |
|------------|----------------------|-------|
| < 20 digits | Pollard Rho (Brent) | Fast, general-purpose |
| 20-40 digits | ECM (Elliptic Curve Method) | Efficient for medium factors |
| 40-80 digits | Quadratic Sieve | General-purpose, robust |
| 60-110 digits | SIQS | Self-initializing, best for this range |
| > 110 digits | GNFS | Requires external `msieve` or `cado-nfs` binary |

## Available Documentation

### Algorithm Guides

- [Trial Division](trial_division.md) — Wheel-based small prime removal, O(π(√n))
- [Pollard p-1](pollard_pm1.md) — Smooth factor detection with progressive bounds
- [Pollard's Rho](pollards_rho.md) — Brent variant for general factorisation
- [Pollard's Rho (Brent)](pollards_rho_brent.md) — Optimised cycle detection
- [Miller-Rabin](miller_rabin.md) — Deterministic primality test for n < 2^64
- [Elliptic Curve Method (ECM)](ecm.md) — Modern method for 10-40 digit factors
- [Quadratic Sieve](quadratic_sieve.md) — QS for medium-to-large composites
- [Self-Initializing Quadratic Sieve (SIQS)](siqs.md) — Best for 60-110 digits
- [General Number Field Sieve (GNFS)](gnfs.md) — External adapter for very large inputs

### References

- [References](references.md) — Academic sources and further reading

## Architecture

The library uses a layered architecture:

```
cli.py              # Command-line interface
    |
core.py             # Miller-Rabin, is_prime, ensure_integer_input
    |
pipeline.py         # Multi-stage orchestrator
stages/
    trial_division.py
    pollard_rho.py
    ecm.py
    ecm_two_pass.py
    quadratic_sieve.py
    siqs.py
    gnfs.py
    ecm_shared.py     # Shared ECM utilities
    qs_shared.py      # Shared QS/SIQS utilities
    |
hybrid.py           # Stateful pipeline with threshold routing
config.py           # Configuration dataclasses
```

## Configuration

### FactoriserConfig

```python
from factorise import FactoriserConfig

config = FactoriserConfig(
    max_iterations=1_000_000,  # Pollard Rho iteration limit
    batch_size=1000,          # Rho batch size for efficiency
    seed=42,                  # Reproducibility seed
)
```

### HybridConfig

The `HybridFactorisationEngine` routes inputs by bit length:

```python
from factorise import HybridFactorisationEngine, HybridConfig

engine = HybridFactorisationEngine(HybridConfig())
result = engine.attempt(123456789)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FACTORISE_LOG_LEVEL` | `WARNING` | Log verbosity |
| `FACTORISE_LOG_FORMAT` | `human` | `human` or `json` |
| `FACTORISE_SEED` | random | Reproducibility seed |

## Testing

```bash
# Run all tests
just test

# Run with coverage
just coverage

# Run linting
just lint

# Run benchmarks
just bench
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (prime or composite) |
| 1 | Input error |
| 128 + signal | Terminated by signal (e.g. 130 for SIGINT, 143 for SIGTERM) |
