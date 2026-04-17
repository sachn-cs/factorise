# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-03-28

### Added

- `factorise(n, config)` — main public API returning `FactorisationResult`
- `FactorisationResult` — typed frozen dataclass (strictly deduplicated factors, powers map, is_prime calculation)
- `FactoriserConfig` — frozen dataclass with `from_env()` for environment-based configuration
- `is_prime(n)` — deterministic Miller-Rabin test valid for all n < 2^64
- `validate_int(value, name)` — typed input guard (rejects bool, float, str)
- `pollard_brent(n, config)` — Brent's Pollard Rho with GCD batching and bounded retries
- `pollard_brent_attempt(n, y, c, config, max_iterations)` — single cycle-detection pass
- `factor_flatten(n, config)` — recursive prime splitter
- CLI via `factorise <number>` with `--verbose` and `--log-level` options
- SIGINT / SIGTERM graceful shutdown in CLI
- 240+ unit tests across correctness, type safety, determinism, and thread safety
- **100% logic coverage** across the core mathematical engine
- Exhaustive documentation suite in `docs/` (Miller-Rabin, Pollard-Brent depth)
- Timing benchmarks via `pytest-benchmark` (43 cases)
- Memory benchmarks via `tracemalloc` (34 cases)
- `benchmarks/stress.py` for scalable multicore validation
- Full README with premium badges and operational guide
- PEP 561 `py.typed` marker
- MIT License
