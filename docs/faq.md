# Frequently Asked Questions

## General

### What is `factorise`?

`factorise` is a Python library for deterministic prime factorisation. It uses Miller-Rabin primality testing and a multi-stage factorisation pipeline to decompose integers into their prime factors.

### Is `factorise` deterministic?

Yes. For `n < 2^64`, primality testing is deterministic using Miller-Rabin with specific witnesses. Factorisation results are consistent across runs (with optional deterministic seeding).

### Does `factorise` have any dependencies?

No. `factorise` has **zero runtime dependencies**. All algorithms are implemented from scratch using only the Python standard library.

### What Python versions are supported?

Python 3.10, 3.11, 3.12, 3.13, and 3.14.

## Usage

### How do I factorise a number?

```python
from factorise import factorise

result = factorise(123456789)
print(result.factors)  # [3, 3607, 3803]
```

### How do I check if a number is prime?

```python
from factorise import is_prime

is_prime(97)  # True
```

### How do I use the CLI?

```bash
factorise 123456789
factorise 123456789 --verbose
```

### Can I factorise negative numbers?

The library API supports negative integers:

```python
from factorise import factorise

result = factorise(-123456789)
```

The CLI does not accept negative integers directly because the leading `-` is interpreted as an option flag. Use the library API for negative inputs.

### How do I configure the algorithm parameters?

```python
from factorise import factorise, FactoriserConfig

config = FactoriserConfig(
    batch_size=256,
    max_iterations=5_000_000,
    seed=42,
)
result = factorise(123456789, config=config)
```

Or use environment variables:

```bash
export FACTORISE_BATCH_SIZE=256
export FACTORISE_MAX_ITERATIONS=5000000
```

## Performance

### How fast is `factorise`?

Performance depends on input size and factorisation difficulty:

- **Small numbers** (< 10^6): Milliseconds
- **Medium numbers** (< 10^12): Seconds
- **Large numbers** (> 10^20): Minutes to hours (depends on algorithms used)

### What algorithms are used?

The pipeline tries algorithms in order:

1. **Trial Division** — Fast for small primes
2. **Pollard p-1** — Effective for smooth factors
3. **Pollard's Rho (Brent)** — General-purpose
4. **ECM** — Medium factors (10-40 digits)
5. **Quadratic Sieve** — Medium-large (up to ~80 bits)
6. **SIQS** — Large (60-110 digits)
7. **GNFS** — Very large (60-128 bits)

### Can I use specific algorithms only?

Yes. Use the pipeline directly with a custom stage order:

```python
from factorise import FactorisationPipeline, PipelineConfig

config = PipelineConfig(
    stage_order=("pollard_rho", "ecm"),
)
pipeline = FactorisationPipeline(config)
result = pipeline.attempt(123456789)
```

## Troubleshooting

### `TypeError: expected int, got <type>`

Ensure you pass plain `int` values:

```python
# Correct
factorise(123456789)

# Wrong
factorise("123456789")
factorise(123456789.0)
factorise(True)
```

### `FactorisationError: factorisation failed`

The algorithm exhausted its compute budget. Options:

1. Increase `max_iterations`:
   ```python
   config = FactoriserConfig(max_iterations=100_000_000)
   ```

2. Increase `max_retries`:
   ```python
   config = FactoriserConfig(max_retries=50)
   ```

3. Set a deterministic seed for reproducibility:
   ```python
   config = FactoriserConfig(seed=42)
   ```

### GNFS is always skipped

Ensure `msieve` or `cado-nfs` is installed and on your PATH:

```bash
which msieve
# or
which cado-nfs-client.py
```

### Wrong factors returned

Enable DEBUG logging to see which stage found each factor:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Development

### How do I run tests?

```bash
just test              # Run test suite
just test-ci          # Run with coverage enforcement
```

### How do I contribute?

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

### How do I report a bug?

[Open an issue](https://github.com/sachncs/factorise/issues/new?template=bug_report.md) with:

- Steps to reproduce
- Expected vs actual behavior
- Python version and OS

### How do I report a security vulnerability?

See [SECURITY.md](../SECURITY.md) for the vulnerability reporting process.

## Integration

### Can I use `factorise` in production?

Yes. `factorise` is designed for production use:

- Zero runtime dependencies
- Full type hints
- Deterministic behavior
- Comprehensive test suite (90%+ coverage)
- CI/CD with security auditing

### Can I use `factorise` in a web application?

Yes. Use the library API:

```python
from factorise import factorise

@app.route("/factorise/<int:n>")
def factorise_number(n):
    result = factorise(n)
    return {"factors": result.factors, "expression": result.expression()}
```

### Is `factorise` thread-safe?

Yes. Configuration objects are frozen dataclasses, and the library uses no global mutable state.
