# Getting Started

This guide walks you through installing, configuring, and using `factorise` for prime factorisation in Python.

## Installation

### From PyPI

```bash
pip install factorise
```

### From Source

```bash
git clone https://github.com/sachncs/factorise.git
cd factorise
pip install -e ".[dev]"
```

### Verify Installation

```bash
python -c "from factorise import factorise; print(factorise(123456789).expression())"
# Output: 3^2 * 3607 * 3803
```

## Quick Start

### Library API

The simplest way to factorise a number:

```python
from factorise import factorise

result = factorise(123456789)

print(result.factors)       # [3, 3607, 3803]
print(result.powers)        # {3: 2, 3607: 1, 3803: 1}
print(result.expression())  # '3^2 * 3607 * 3803'
```

### Primality Testing

```python
from factorise import is_prime

is_prime(97)   # True
is_prime(100)  # False
```

### CLI Usage

```bash
# Basic usage
factorise 123456789

# Verbose output
factorise 123456789 --verbose

# Set log level
factorise 123456789 --log-level INFO
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and modify as needed:

```bash
cp .env.example .env
```

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `FACTORISE_LOG_LEVEL` | `WARNING` | Logging verbosity |
| `FACTORISE_BATCH_SIZE` | `128` | GCD batch size |
| `FACTORISE_MAX_ITERATIONS` | `10000000` | Max steps per attempt |
| `FACTORISE_SEED` | — | Deterministic seed |

### Programmatic Configuration

```python
from factorise import FactoriserConfig, factorise

config = FactoriserConfig(
    batch_size=256,
    max_iterations=5_000_000,
    seed=42,
)

result = factorise(123456789, config=config)
```

## Next Steps

- Read the [Architecture](architecture.md) documentation
- Explore [Algorithm Documentation](index.md) for mathematical details
- Review the [API Reference](../README.md#api-reference)
- Check the [FAQ](faq.md) for common questions
