# Architecture

This document describes the internal architecture of `factorise` and the design decisions behind it.

## Overview

`factorise` is designed as a composable, multi-stage factorisation library with zero runtime dependencies. The architecture separates concerns into distinct modules:

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI (cli.py)                         │
├─────────────────────────────────────────────────────────────┤
│                   Hybrid Engine (hybrid.py)                 │
├─────────────────────────────────────────────────────────────┤
│              Factorisation Pipeline (pipeline.py)           │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│  Trial   │ Pollard  │ Pollard  │   ECM    │  Quadratic     │
│ Division │   p-1    │  Rho     │          │  Sieve / GNFS  │
├──────────┴──────────┴──────────┴──────────┴────────────────┤
│                   Core Algorithms (core.py)                 │
├─────────────────────────────────────────────────────────────┤
│               Configuration (config.py)                    │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### `core.py` — Foundation Layer

The foundation layer provides:

- **Input validation**: `ensure_integer_input()` ensures plain `int` values
- **Primality testing**: Miller-Rabin deterministic for `n < 2^64`
- **Perfect power detection**: Identifies `n = b^k` forms
- **Factorisation result**: `FactorisationResult` dataclass with factors, powers, and expression generation
- **Domain exceptions**: `FactorisationError` for exhausted compute budgets

### `config.py` — Configuration Management

Immutable frozen dataclasses enforce fail-fast validation:

- **`FactoriserConfig`**: Core algorithm parameters (batch size, retries, seed)
- **`PipelineConfig`**: Extends `FactoriserConfig` with stage-specific bounds
- **`HybridConfig`**: Digit-count thresholds for adaptive routing

All configs support construction from environment variables via `from_env()`.

### `pipeline.py` — Multi-Stage Orchestrator

The pipeline coordinates factorisation stages:

1. **Stage interface**: `FactorStage` abstract base class
2. **Stage execution**: `attempt()` returns `StageResult`
3. **Recursive splitting**: Generator-based to keep memory bounded
4. **Stage ordering**: Configurable via `stage_order` tuple

### `stages/` — Algorithm Implementations

Each stage implements `FactorStage`:

| Stage | Algorithm | Best For |
|-------|-----------|----------|
| `trial_division.py` | Trial Division | Small primes (≤ 10^4) |
| `improved_pm1.py` | Pollard p-1 | Smooth factors |
| `pollard_rho.py` | Pollard's Rho (Brent) | General small-medium |
| `ecm.py` / `ecm_two_pass.py` | ECM | Medium factors (10-40 digits) |
| `quadratic_sieve.py` | Quadratic Sieve | Medium-large (≤ 80 bits) |
| `siqs.py` | SIQS | Large (60-110 digits) |
| `gnfs_optimized.py` | GNFS adapter | Very large (60-128 bits) |

### `hybrid.py` — Adaptive Engine

Routes each cofactor to the optimal algorithm based on input size:

- Digit-count thresholds determine which stages to attempt
- Adaptive retry strategies per input bucket
- Structured observability via `HybridFactorisationState`

## Design Principles

### Immutability

All configuration objects are frozen dataclasses. This ensures:

- Thread-safe access
- Predictable behavior across calls
- Easy testing and reproducibility

### Fail-Fast Validation

Configuration validation happens at construction time:

```python
config = PipelineConfig(batch_size=-1)  # Raises immediately
```

### Composability

Stages are composable via the `FactorStage` interface:

```python
class FactorStage(Protocol):
    def attempt(self, n: int, config: FactoriserConfig) -> StageResult: ...
```

### Structured Observability

All operations return structured results:

```python
@dataclass(frozen=True)
class StageResult:
    status: StageStatus
    factor: int | None
    elapsed_ms: float
    reason: str | None
    iterations_used: int | None
```

### Memory Efficiency

Generator-based recursive splitting keeps memory bounded:

```python
def yield_prime_factors(n: int) -> Iterator[int]:
    # Yields factors one at a time
    # No accumulation of intermediate results
```

## Data Flow

```
Input (int)
    │
    ▼
validate_int() ──► TypeError if invalid
    │
    ▼
is_prime() ──► Return immediately if prime
    │
    ▼
Pipeline.attempt(n)
    │
    ├──► TrialDivision.attempt(n)
    │       │
    │       ▼
    │    StageResult(factor=3, status=SUCCESS)
    │
    ├──► Recurse on factor (3) and cofactor (41152263)
    │       │
    │       ▼
    │    ... (continue until all factors are prime)
    │
    ▼
FactorisationResult(factors=[3, 3, 3607, 3803], powers={3: 2, ...})
```

## Testing Strategy

- **Unit tests**: Individual algorithm correctness
- **Integration tests**: Pipeline behavior and stage interaction
- **Property tests**: Invariants via Hypothesis (e.g., `product(result.factors) == n`)
- **Stress tests**: Deterministic correctness at scale
- **Concurrency tests**: Thread and process safety verification

## Performance Considerations

- **Batch GCD**: Pollard-Brent batches GCD computations for throughput
- **Progressive bounds**: Pollard p-1 increases smoothness bounds incrementally
- **Curve diversity**: ECM runs multiple random curves
- **Timeout isolation**: GNFS adapter enforces strict timeouts

## Security Considerations

- **Input validation**: All public entry points validate integer inputs
- **No shell injection**: External tool inputs sanitized; no `os.system()`
- **Timeout controls**: GNFS subprocess timeout prevents hanging
- **Deterministic builds**: Reproducible via `SOURCE_DATE_EPOCH`
