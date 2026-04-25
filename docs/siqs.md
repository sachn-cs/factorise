# Self-Initializing Quadratic Sieve (SIQS)

SIQS is an improved version of the Quadratic Sieve that automatically computes the smoothness bound and is effective for 60-110 digit composites in pure Python.

## Key Features

- **Auto-computed smoothness bound**: `B = exp(sqrt(log n * log log n) / 2)`.
- **Large prime variation**: Allows exactly one large prime per relation.
- **GF(2) Gaussian elimination**: Finds dependencies among relations.

## Algorithm Overview

1. Compute the smoothness bound `B` from `n`.
2. Generate a factor base of primes for which `n` is a quadratic residue.
3. Search for smooth relations `(a, a^2 mod n)`.
4. Use Gaussian elimination to find a subset of relations with even exponents.
5. Extract a factor via `gcd(a ± b, n)`.

## When to Use

- Practical choice for 60-110 digit composites in pure Python.
- Beyond that, an external GNFS implementation is required.

## Implementation

```python
from factorise.stages.siqs import SIQSStage

stage = SIQSStage(max_bit_length=110)
result = stage.attempt(123456789012345678901234567890123456789)
print(result.factor)
```
