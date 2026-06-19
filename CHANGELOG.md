# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- API reference documentation using mkdocs with mkdocstrings.
- `docs/getting-started.md` — installation, quick start, and configuration guide.
- `docs/architecture.md` — internal design, components, data flow, and design principles.
- `docs/deployment.md` — publishing to PyPI, version management, CI/CD pipeline.
- `docs/faq.md` — frequently asked questions covering usage, performance, troubleshooting.
- `.github/FUNDING.yml` with GitHub Sponsors placeholder.
- Additional README badges: coverage, downloads, Python versions, security policy.
- `factorise/stages/README.md` documenting each stage's purpose, interface, and usage.
- Targeted coverage tests in `tests/test_coverage_extensions.py` raising overall
  coverage from ~93% to ~97%.
- `integer_kth_root(n, k)` helper replacing floating-point `n**(1.0/exp)` in
  `find_perfect_power` for exactness.
- `_elapsed_ms()` timing helpers and structured `key=value` logging across `cli.py`,
  `core.py`, `hybrid.py`, and `pipeline.py`.
- Extracted edge-case handlers (`try_zero`, `try_unit`, `try_two`, `try_perfect_power`,
  `try_even`) in `hybrid.py` for explicit data flow.

### Changed
- **File naming**: removed leading-underscore prefix from `_utils.py` to `utils.py`.
- **CLI display**: replaced emoji with plain-text markers (e.g. `[PRIME]`).
- **Config validation**: extracted `validate_int_range()` and `env_int()` helpers
  in `config.py` to eliminate repetitive validation blocks.
- **Pollard-Brent refactoring**: de-nested `execute_brent_pollard_cycle` into
  `compute_batch_limit()`, `run_brent_batch()`, and `backtrack_brent()` helpers.
- **Hybrid engine**: `factorise_stack()` now explicitly handles composite factors
  and cofactors pushed back onto the work stack.
- `FactorisationPipeline._build_stage_map()` uses direct imports instead of
  `importlib.import_module` for clarity.
- **Documentation**: expanded README with features, tech stack, roadmap, and security sections.
- **Documentation**: expanded CONTRIBUTING.md with branch naming, commit conventions, and detailed PR process.
- **Documentation**: expanded SECURITY.md with response expectations, disclosure policy, and security best practices.
- **Documentation**: added Documentation and Changelog URLs to `pyproject.toml`.
- `README.md` updated to remove stale references (`loguru`, JSON logging,
  `StageFactory`) and reflect current architecture.

### Fixed
- `pyproject.toml` entry point corrected from `factorise.cli:app` to
  `factorise.cli:main`.
- `DEFAULT_LOG_LEVEL` name corruption from global substring replacement restored.
- `has_carmichael_property` prime bug explicitly preserved with comment for
  backward compatibility.
- `compute_modular_inverse(0, n)` now correctly returns `0`.

## [0.5.2] — 2026-04-28

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

## [0.5.0] — 2026-04-28

### Added
- `yield_prime_factors_via_pipeline()` generator for recursive pipeline-based
  factorisation with Pollard-Brent fallback.
- `PollardPMinusOneStage` and `QuadraticSieveStage` as pipeline-compatible stages.
- `BrentPollardCycleResult` and `PollardBrentOutcome` for structured Pollard-Brent
  cycle observability.

## [0.4.0] — 2026-04-28

### Added
- `FactorisationPipeline` multi-stage orchestrator with `FactorStage` abstract
  interface and `StageResult` structured output.
- `OptimizedTrialDivisionStage`, `PollardRhoStage`, `ECMStage` as `FactorStage`
  implementations.
- `StageStatus` enum (`SKIPPED`, `PARTIAL`, `SUCCESS`, `FAILURE`).

### Changed
- Refactored monolithic `core.py` into `pipeline.py` and `stages/` package.

## [0.3.3] — 2026-04-17

### Added
- CycloneDX SBOM generation in the release pipeline.
- Checksum generation (`SHA256SUMS`) for all distribution artifacts.

### Fixed
- Stabilized CI workflows with improved caching and timeouts.
- Ensured reproducible builds via `SOURCE_DATE_EPOCH` injection.

## [0.3.0] — 2026-04-17

### Added
- Modular test suite architecture (split into domain-specific test files).
- Property-based testing via `hypothesis` for primality and factorisation invariants.
- Concurrency smoke tests for thread-safety verification.
- Validated JSON logging mode for CLI with trace context support.

### Changed
- Standardized benchmarking suite with normalized names and README guidance.
- Refined `FactoriserConfig` boundaries and environment variable mapping.

## [0.2.0] — 2026-04-16

### Added
- Transitioned to `Hatch` as the primary build backend.
- Integrated `just` task runner for simplified developer experience.
- Added `pre-commit` configuration for local linting enforcement.
- Initial project overview and architecture documentation in `README.md`.

## [0.1.0] — 2026-03-28

### Added
- Core Miller-Rabin and Pollard's Rho (Brent) implementation.
- Typed `FactorisationResult` and `FactoriserConfig` models.
- Functional CLI with verbose logging.
- Initial unit test suite and benchmarks.
- Project boilerplate (LICENSE, MANIFEST.in, .gitignore).
