# factorise stages

This directory contains the individual factorisation algorithms that make up the
multi-stage pipeline.  Each stage implements the :class:`~factorise.pipeline.FactorStage`
abstract interface and returns a structured :class:`~factorise.pipeline.StageResult`.

## Stage interface

Every stage must provide:

```python
class MyStage(FactorStage):
    name: str = "my_stage"

    def attempt(self, n: int) -> StageResult:
        ...
```

Stages are expected to return one of the following statuses:

| Status   | Meaning                                                    |
|----------|------------------------------------------------------------|
| SUCCESS  | Found a non-trivial factor (field `factor` is populated). |
| FAILURE  | Ran to completion but could not find a factor.            |
| SKIPPED  | Not applicable for this input (too small, too large, etc).|

## Stage catalogue

### Trial Division
**File:** `trial_division.py`

Tests divisibility against a fixed table of small primes (up to 7919 by default).
Very fast for inputs with small prime factors.

```python
from factorise.stages.trial_division import OptimizedTrialDivisionStage

stage = OptimizedTrialDivisionStage(bound=10_000)
result = stage.attempt(12345)
```

### Pollard p-1
**File:** `improved_pm1.py`

Finds factors `p` where `p-1` is smooth (has only small prime factors).  Uses
progressive smoothness bounds and multiple bases.

```python
from factorise.stages.improved_pm1 import ImprovedPollardPMinusOneStage

stage = ImprovedPollardPMinusOneStage(bounds=(10**6, 10**7), bases=(2, 3, 5))
result = stage.attempt(12345)
```

### Pollard's Rho (Brent)
**File:** `pollard_rho.py`

General-purpose factorisation using Brent's improvement to Pollard's Rho.
Batches GCD computations for throughput.

```python
from factorise.stages.pollard_rho import PollardRhoStage

stage = PollardRhoStage(max_retries=20, max_iterations=10_000_000)
result = stage.attempt(12345)
```

### ECM (Elliptic Curve Method)
**Files:** `ecm.py`, `ecm_shared.py`, `ecm_two_pass.py`

Modern general-purpose factorisation using elliptic curve arithmetic.  Most
effective for finding factors in the 10–40 digit range.

```python
from factorise.stages.ecm import ECMStage

stage = ECMStage(curves=20, bound=10_000)
result = stage.attempt(12345)
```

Two-pass ECM (`ecm_two_pass.py`) runs a second stage with higher bound and
fresh curves for harder factors.

### Quadratic Sieve
**Files:** `quadratic_sieve.py`, `qs_shared.py`

Fast for medium-to-large inputs up to ~80 bits.  Finds relations where
`a^2 mod n` factors completely over a prime base, then uses Gaussian elimination
over GF(2) to extract a factor.

```python
from factorise.stages.quadratic_sieve import QuadraticSieveStage

stage = QuadraticSieveStage(bound=1000)
result = stage.attempt(12345)
```

### SIQS (Self-Initializing Quadratic Sieve)
**File:** `siqs.py`

Practical choice for 60–110 digit composites in pure Python.  Auto-computes the
smoothness bound and factor base.

```python
from factorise.stages.siqs import SIQSStage

stage = SIQSStage(max_bit_length=110)
result = stage.attempt(12345)
```

### GNFS (General Number Field Sieve)
**File:** `gnfs_optimized.py`

Pure-Python GNFS adapter for 60–128 bit inputs.  Implements single-polynomial
GNFS with lattice sieving and proper rational + algebraic factor bases.  For
very large inputs an external GNFS tool (msieve, CADO-NFS) is required.

```python
from factorise.stages.gnfs_optimized import OptimizedGNFSStage

stage = OptimizedGNFSStage()
result = stage.attempt(12345)
```

## Shared utilities

- `ecm_shared.py` — Montgomery-curve point operations and prime generation for
  ECM stages.
- `qs_shared.py` — Prime testing, smoothness checking, linear algebra over GF(2),
  and factor extraction for QS-based stages.

## Adding a new stage

1. Create a new file in this directory.
2. Implement `FactorStage` with a unique `name`.
3. Return `StageResult` with the appropriate `StageStatus`.
4. Import and register the stage in `factorise/pipeline.py` or wire it into the
   `HybridFactorisationEngine` in `factorise/hybrid.py`.
5. Add tests in `tests/test_stages.py` or a new `tests/test_<stage>.py` file.
