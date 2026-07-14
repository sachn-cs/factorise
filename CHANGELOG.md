# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
ISO-8601 dates are used throughout. Every released version heading carries the
short commit SHA of the corresponding `version:X.Y.Z` (or `Version:X.Y.Z`)
commit and its commit timestamp.

## [Unreleased]

### Changed
- Project metadata: author normalized to `Sachin <sachncs@gmail.com>` in
  `pyproject.toml`.
- `LICENSE` copyright line updated to
  `Copyright (c) 2026 Sachin <sachncs@gmail.com>`.
- `.github/FUNDING.yml` removed for production release.
- Repository URLs normalized from `sachn-cs/factorise` to canonical
  `sachncs/factorise` across `README.md`, `CONTRIBUTING.md`, `docs/`,
  `pyproject.toml`, `mkdocs.yml`, and issue templates.

## [0.7.3] - 2026-06-20 — `e869453`

### Added
- API reference documentation using mkdocs with mkdocstrings.
- `docs/getting-started.md` — installation, quick start, and configuration guide.
- `docs/architecture.md` — internal design, components, data flow, and design
  principles.
- `docs/deployment.md` — publishing to PyPI, version management, CI/CD pipeline.
- `docs/faq.md` — frequently asked questions covering usage, performance, and
  troubleshooting.
- `.github/FUNDING.yml` with GitHub Sponsors placeholder (removed in
  `[Unreleased]`).
- Additional README badges: coverage, downloads, Python versions, security policy.
- Expanded `CONTRIBUTING.md` with branch naming, commit conventions, and a
  detailed PR process.
- Expanded `SECURITY.md` with response expectations, disclosure policy, and
  security best practices.
- Added `Documentation` and `Changelog` URLs to `pyproject.toml`.

## [0.7.2] - 2026-04-28 — `5c4602d`

### Changed
- Refined coverage-extension tests (`tests/test_coverage_extensions.py`) and a
  minor `pyproject.toml` adjustment.

## [0.7.1] - 2026-04-28 — `ad7c9bc`

### Changed
- Refactor of stage code paths: `cli.py`, `config.py`, `core.py`, `hybrid.py`,
  `pipeline.py`, and all stage modules (`ecm*`, `gnfs_optimized`,
  `improved_pm1`, `pollard_rho`, `qs_shared`, `quadratic_sieve`).
- Benchmark stress suite updates.

## [0.7.0] - 2026-04-28 — `2dd5338`

### Added
- `integer_kth_root(n, k)` helper replacing floating-point `n**(1.0/exp)` in
  `find_perfect_power` for exactness.
- `_elapsed_ms()` timing helpers and structured `key=value` logging across
  `cli.py`, `core.py`, `hybrid.py`, and `pipeline.py`.
- Extracted edge-case handlers (`try_zero`, `try_unit`, `try_two`,
  `try_perfect_power`, `try_even`) in `hybrid.py` for explicit data flow.
- `factorise/stages/README.md` documenting each stage's purpose, interface, and
  usage.
- Targeted coverage tests in `tests/test_coverage_extensions.py` raising overall
  coverage from ~93% to ~97%.

### Changed
- **File naming**: removed leading-underscore prefix from `_utils.py` to
  `utils.py`.
- **CLI display**: replaced emoji with plain-text markers (e.g. `[PRIME]`).
- **Config validation**: extracted `validate_int_range()` and `env_int()`
  helpers in `config.py` to eliminate repetitive validation blocks.
- **Pollard-Brent refactoring**: de-nested `execute_brent_pollard_cycle` into
  `compute_batch_limit()`, `run_brent_batch()`, and `backtrack_brent()` helpers.
- **Hybrid engine**: `factorise_stack()` now explicitly handles composite
  factors and cofactors pushed back onto the work stack.
- `FactorisationPipeline._build_stage_map()` uses direct imports instead of
  `importlib.import_module` for clarity.
- `README.md` updated to remove stale references (`loguru`, JSON logging,
  `StageFactory`) and reflect current architecture.

### Fixed
- `pyproject.toml` entry point corrected from `factorise.cli:app` to
  `factorise.cli:main`.
- `DEFAULT_LOG_LEVEL` name corruption from global substring replacement restored.
- `has_carmichael_property` prime bug explicitly preserved with comment for
  backward compatibility.
- `compute_modular_inverse(0, n)` now correctly returns `0`.

## [0.6.1] - 2026-04-27 — `655bdee`

### Changed
- Refactor of stage code paths: `cli.py`, `hybrid.py`, `pipeline.py`,
  `gnfs_optimized.py`, `qs_shared.py`, `quadratic_sieve.py`, `siqs.py`,
  `trial_division.py`; associated test rewrites across the test suite.

## [0.6.0] - 2026-04-27 — `fa2ee12`

### Added
- `HybridFactorisationEngine` with adaptive algorithm selection by input size.
- `HybridConfig` with digit-count thresholds and per-bucket stage routing.
- Self-Initializing Quadratic Sieve (`SIQSStage`) for 60–110 digit composites.
- Pure-Python GNFS (`OptimizedGNFSStage`) for 60–128 bit inputs with lattice
  sieving and rational/algebraic factor bases.
- Two-pass ECM (`TwoPassECMStage`) with progressive smoothness bounds.
- Extended test suite: `test_hybrid.py`, `test_coverage_gaps.py`,
  `test_stages.py`, `test_ecm_shared.py`.

### Changed
- Migrated from `setuptools` to `hatchling` build backend.
- Added Python 3.13 and 3.14 to CI matrix and classifiers.

### Removed
- `PipelineConfig`, `FactorisationPipeline`, `StageFactory`, and
  `yield_prime_factors_via_pipeline` re-exports consolidated into a slimmer
  public surface (`core`, `hybrid`, `pipeline` modules).

## [0.5.1] - 2026-04-25 — `fc2ce0b`

### Fixed
- One-line hotfix in `pipeline.py`.

## [0.5.0] - 2026-04-25 — `5073719`

### Added
- `yield_prime_factors_via_pipeline()` generator for recursive pipeline-based
  factorisation with Pollard-Brent fallback.
- `PollardPMinusOneStage` and `QuadraticSieveStage` as pipeline-compatible
  stages.
- `BrentPollardCycleResult` and `PollardBrentOutcome` for structured
  Pollard-Brent cycle observability.

### Changed
- Refactored stages package: removed `_ecm_shared.py` (no leading underscore),
  promoted `ecm_shared.py` and added `improved_pm1.py`, `pollard_rho.py`,
  `trial_division.py`, `siqs.py`, `gnfs.py`, `quadratic_sieve.py`.
- Major rewrite of `core.py`, `config.py`, `hybrid.py`, `pipeline.py`.
- Documentation: added `docs/README.md`, expanded algorithm-specific docs.
- Renamed `src/factorise/*` to `factorise/*` (package rename).

## [0.4.1] - 2026-04-24 — `bc16012`

### Changed
- Major refactor across benchmarks, stages, and test files. Filenames updated
  from `src/factorise/*` to `factorise/*` in most modules in this release
  cycle (fully landed in 0.5.0).

## [0.4.0] - 2026-04-24 — `b784544`

### Added
- `docs/ecm.md`, `docs/gnfs.md`, `docs/pollard_pm1.md`,
  `docs/quadratic_sieve.md`, `docs/siqs.md`, `docs/trial_division.md`.
- `MANIFEST.in` updated for source distribution.
- Algorithmic documentation expansion.

### Changed
- `source/` package renamed to `factorise/`.
- `.pre-commit-config.yaml` initial setup.

## [0.3.4] - 2026-04-23 — `9abef80`

### Added
- New algorithm documentation files: `docs/miller_rabin.md`,
  `docs/pollards_rho.md`, `docs/pollards_rho_brent.md`, `docs/references.md`.
- New shared internals: `source/stages/_ecm_shared.py`,
  `source/stages/_qs_shared.py`.
- New algorithm stages: `source/stages/ecm_two_pass.py`,
  `source/stages/improved_pm1.py`.

### Changed
- `docs/ecm.md`, `docs/gnfs.md`, `docs/pollard_pm1.md`,
  `docs/quadratic_sieve.md`, `docs/siqs.md`, `docs/trial_division.md`,
  `docs/index.md` content rewrites.
- `pyproject.toml` updates.

## [0.3.3] - 2026-04-17 — `52acb8b`

### Added
- CycloneDX SBOM generation in the release pipeline.
- Checksum generation (`SHA256SUMS`) for all distribution artifacts.

### Fixed
- Stabilized CI workflows with improved caching and timeouts.
- Ensured reproducible builds via `SOURCE_DATE_EPOCH` injection.

## [0.3.2] - 2026-04-17 — `4bf6017`

### Changed
- Rewritten CI workflow: `.github/workflows/ci.yml` expanded with cache, matrix,
  and artifact retention steps.

## [0.3.1] - 2026-04-17 — `42609fa`

### Added
- `src/factorise/__init__.py` (interim packaging split during the
  `source/` → `factorise/` rename).

### Changed
- Updated benchmark suite: `benchmarks/memory.py`, `benchmarks/stress.py`,
  `benchmarks/timing.py`.
- Source relocation: `src/factorise/` directory structure introduced.

## [0.3.0] - 2026-04-17 — `f568862`

### Added
- Modular test suite architecture (split into domain-specific test files).
- Property-based testing via `hypothesis` for primality and factorisation
  invariants.
- Concurrency smoke tests for thread-safety verification.
- Validated JSON logging mode for CLI with trace context support.

### Changed
- Standardized benchmarking suite with normalized names and README guidance.
- Refined `FactoriserConfig` boundaries and environment variable mapping.

## [0.2.0] - 2026-04-16 — `86dd409`

### Added
- Transitioned to `Hatch` as the primary build backend.
- Integrated `just` task runner for simplified developer experience.
- Added `pre-commit` configuration for local linting enforcement.
- Initial project overview and architecture documentation in `README.md`.

## [0.1.0] - 2026-03-28 — `465deb1`

### Added
- Core Miller-Rabin and Pollard's Rho (Brent) implementation.
- Typed `FactorisationResult` and `FactoriserConfig` models.
- Functional CLI with verbose logging.
- Initial unit test suite and benchmarks.
- Project boilerplate (LICENSE, MANIFEST.in, .gitignore).
