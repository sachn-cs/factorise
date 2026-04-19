# Factorise Benchmarking Suite

This directory contains the automated performance and memory benchmarking suite for the `factorise` library.

The suite ensures that modifications to the core arithmetic routines (`Miller-Rabin`, `Pollard-Brent`) do not introduce performance regressions or memory accumulation.

---

## 1. Overview

The benchmark suite measures:

1. **Execution Time (Throughput/Latency):** Wall-clock time required to factorise given inputs.
2. **Peak Memory Allocation:** Maximum memory used by the algorithms during execution.
3. **Scalability:** Performance trends as input sizes grow exponentially.
4. **Stress Correctness:** Verification of algorithmic stability at scale across multiple cores.

---

## 2. Setup

Benchmarking requires development dependencies.

```bash
# Install the library with dev/benchmark extras
pip install -e ".[dev]"
```

**Key Dependencies:**
- `pytest-benchmark`: High-resolution execution timing.
- `tracemalloc`: Standard library memory tracking (used in `memory.py`).
- `rich`: Console UI for concurrent stress testing.

---

## 3. Running Benchmarks (Quick Start)

The recommended way to run benchmarks is via the `just` task runner:

```bash
# Run execution timing benchmarks
just benchmark

# Run memory allocation benchmarks
just benchmark-memory

# Run massive concurrent stress tests
just stress-test
```

---

## 4. Advanced Usage (Manual)

For deeper diagnostics, use `pytest` directly:

### Timing Diagnostics
Measure execution speed with specific sorting or histograms:

```bash
# Sort results by mean execution time
pytest benchmarks/timing.py --benchmark-only --benchmark-sort=mean

# Generate a histogram of execution times
pytest benchmarks/timing.py --benchmark-only --benchmark-histogram
```

### Memory Diagnostics
Measure peak allocation with verbose output:

```bash
# Run all memory benchmarks and print allocation metrics
pytest benchmarks/memory.py -v -s
```

### Regression Testing
To detect regressions against a baseline:

1. Save baseline from master: `pytest benchmarks/timing.py --benchmark-only --benchmark-save=baseline`
2. Run on feature branch: `pytest benchmarks/timing.py --benchmark-only --benchmark-compare`

---

## 5. Benchmark Design

### Input Tiers
Inputs are controlled in `inputs.py` to ensure consistency:
* **Small:** Triggers fast-paths (small primes, trivial division).
* **Medium:** Exercises core loops (numbers up to $10^9$).
* **Large:** Stresses modular exponentiation and cycle detection ($2^{64}$ semiprimes).

### Metrics
- **Mean/Min/Max:** Captured in microseconds (μs) or milliseconds (ms).
- **OPS (Operations Per Second):** Throughput measurement; higher is better.
- **Peak Bytes:** Maximum memory allocated during the benchmarked call.

---

## 6. Contribution Standards

- **Warmup**: `pytest-benchmark` performs automatic warmup rounds; do not add manual sleeps.
- **Isolation**: Run benchmarks on a quiet machine with thermal throttling disabled for stable results.
- **Conventions**: Keep the actual benchmarked logic inside the `benchmark()` call provided by the fixture.

---

## 7. Limitations

- **Hardware Variance**: Absolute times depend on the host CPU. Use relative comparisons on the same machine.
- **Runtime Variance**: Python 3.11+ provides significant speedups over 3.10. Ensure consistent Python versions during comparison.

---

*For detailed contribution guidelines, see [CONTRIBUTING.md](../CONTRIBUTING.md).*
