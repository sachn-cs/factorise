# Factorise Benchmarking Suite

This directory contains the automated performance and memory benchmarking suite for the `factorise` library.

The suite ensures that modifications to the core arithmetic routines (`Miller-Rabin`, `Pollard-Brent`) do not introduce performance regressions or memory accumulation.

---

## Overview

The benchmark suite measures:

1. **Execution Time (Throughput/Latency):** Wall-clock time required to factorise given inputs.
2. **Peak Memory Allocation:** Maximum memory used by the algorithms during execution.
3. **Scalability:** Performance trends as input sizes grow exponentially.

---

## Benchmark Scope

### Covered
- `is_prime(n)`: Deterministic Miller-Rabin primality testing.
- `factorise(n)`: Complete prime factorisation orchestration.
- `pollard_brent(n)`: Core Brent-Pollard cycle detection layer (isolated).
- **Batch Processing:** Throughput for processing multiple inputs consecutively.

### Excluded
- Command-Line Interface (CLI) startup time and rich formatting overhead.
- Exceptions/error paths (e.g., passing invalid types).

---

## Setup

Benchmarking requires additional development dependencies.

```bash
# Install the library with benchmarking extras
pip install -e ".[bench]"
```

**Dependencies:**
- `pytest`: Test runner.
- `pytest-benchmark`: High-resolution execution timing.

---

## Running Benchmarks

### Timing Benchmarks

Measure execution speed using `pytest-benchmark`:

```bash
# Run all timing benchmarks
pytest benchmarks/bench_timing.py --benchmark-only -v

# Run and sort results by mean execution time
pytest benchmarks/bench_timing.py --benchmark-only --benchmark-sort=mean

# Generate a histogram of execution times
pytest benchmarks/bench_timing.py --benchmark-only --benchmark-histogram
```

### Memory Benchmarks

Measure peak allocation using `tracemalloc`:

```bash
# Run all memory benchmarks and print allocation metrics
pytest benchmarks/bench_memory.py -v -s
```

### Multicore Stress Testing

To verify algorithmic stability and correctness at a massive scale, run the concurrent stress test tool. It divides the testing range across all available CPU cores and verifies that every output's prime factors mathematically reconstruct the original integer.

```bash
# Run the massive 1-to-N validation stress test
python3 benchmarks/stress_test.py
```

*Note: The stress test uses Python's `ProcessPoolExecutor` directly and displays a live `rich` progress bar, so it does not require `pytest` to execute.*

---

## Benchmark Design

### Input Tiers
All benchmarks are parameterized across controlled inputs defined in `inputs.py`.

* **Small:** Triggers fast-paths (small primes, trivial division).
* **Medium:** Exercises core loops (e.g., numbers up to `10^9`).
* **Large:** Stresses modular exponentiation and full cycle detection (e.g., 64-bit primes, large semiprimes).

### Parameterization
Where applicable, algorithms are tested against variables such as:
- Varying `FACTORISE_BATCH_SIZE`.
- Pure primes vs. highly composite numbers vs. semiprimes.
- Perfect squares (testing the `isqrt` fast-path).

### Warmup
`pytest-benchmark` automatically executes warmup rounds before capturing measurements, ensuring the JIT (if applicable) and CPU caches are primed.

---

## Metrics

### Execution Time
- **Mean / Min / Max:** Measured in microseconds (μs) or milliseconds (ms).
- **OPS (Operations Per Second):** The number of complete executions per second. Higher is better.
- **Interpretation:** Compare Mean time against a stable baseline. Any significant deviation (e.g., >5% slowdown) indicates a regression.

### Memory Usage
- **Peak Bytes/KB:** The maximum memory allocated during a function call, captured via Python's `tracemalloc`.
- **Interpretation:** `factorise` is designed to be highly memory-efficient. No single call should exceed ~2 MB. Tests will fail if threshold limits are breached, indicating a leak or inefficient allocation.

---

## Interpreting Results

### Reading the Output
`pytest-benchmark` produces a table format. Look at the `Mean` and `OPS` columns.

### Detecting Regressions
1. Run benchmarks on the `main` branch and save the results using `pytest-benchmark`'s JSON save feature.
2. Switch to your feature branch.
3. Run benchmarks and compare:
   ```bash
   pytest benchmarks/bench_timing.py --benchmark-only --benchmark-compare
   ```

---

## Reproducibility

Performance measurements vary significantly based on hardware state. To ensure consistent results:
- Run benchmarks on a quiet machine (close browsers, IDEs, background processes).
- Ensure your CPU is not thermal-throttling.
- If running on a laptop, ensure it is plugged into AC power.
- For authoritative baseline comparison, consider using a dedicated CI runner or locking CPU frequencies.

---

## Extending Benchmarks

### Where to add
- **Timing:** Add functions starting with `test_bench_` in `bench_timing.py`.
- **Memory:** Add functions starting with `test_memory_` in `bench_memory.py`.
- **Inputs:** Define reusable input sets in `inputs.py`.

### Conventions
- Always type-hint inputs.
- Keep the actual benchmarked function inside the `benchmark()` call.
- Prefix benchmark names clearly so they can be selectively filtered using `pytest -k`.

---

## Limitations

- **System Noise:** Absolute execution times depend entirely on the host CPU. Benchmarks are only useful for relative comparison on the same machine.
- **Python Version:** Python 3.11+ is noticeably faster than 3.10. Always benchmark the baseline and feature branches on the exact same Python version.
