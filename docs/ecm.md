# Elliptic Curve Method (ECM)

ECM is a modern general-purpose factorisation algorithm that is particularly effective for finding medium-sized factors (10–40 digits).

## Algorithm Overview

1. Choose a random elliptic curve and a point on it modulo `n`.
2. Compute `kP` where `k` is a product of small primes raised to appropriate powers.
3. If the computation fails due to a non-invertible element modulo `n`, the gcd of the non-invertible element and `n` gives a factor.

## Montgomery Ladder

The implementation uses Montgomery coordinates for fast point multiplication without computing `y` coordinates.

## Two-Pass Variant

`TwoPassECMStage` runs two passes:
- **Pass 1**: Standard ECM with a moderate bound and a fixed number of curves.
- **Pass 2**: Higher bound with fresh curves for harder factors.

## When to Use

- Most effective for finding factors in the 10–40 digit range.
- Better than Pollard's Rho for composites whose smallest factor is in this range.

## Implementation

```python
from factorise.stages.ecm import ECMStage

stage = ECMStage(curves=20)
result = stage.attempt(1234567890123456789, config=FactoriserConfig())
```
