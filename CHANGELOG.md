# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- `typing Self` import and `@classmethod`-returning `Self` for proper covariant return types.

### Changed
- **Python 3.14**: bumped `requires-python`, mypy `python_version`, and ruff `target-version` to `3.14`.
- Refined repo-root configuration files (.editorconfig, .gitignore, .gitattributes).
- Standardized repository structure by flattening package code directly into `source/`.
- Updated `CONTRIBUTING.md` with accurate setup and quality standards.

### Fixed
- Fixed variable shadowing in `GNFSStage._run_gnfs`: loop variable `f` overwrote file handle `f` from outer scope (caused type errors on Python 3.14).
- Added missing type arguments to unparameterized `dict` literals in `QuadraticSieveStage` methods (`_find_relations`, `_find_dependency`, `_extract_factor`).

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
