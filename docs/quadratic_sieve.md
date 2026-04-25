# Quadratic Sieve (QS)

The Quadratic Sieve is a fast factorisation method for medium-to-large composites (up to ~80 bits).

## Algorithm Overview

1. **Factor Base**: Choose a set of small primes.
2. **Relation Search**: Find values `a` such that `a^2 mod n` factors completely over the factor base.
3. **Linear Algebra**: Use Gaussian elimination over GF(2) to find a subset of relations whose exponents are all even.
4. **Factor Extraction**: Compute `gcd(a ± b, n)` to extract a non-trivial factor.

## Limitations

The simplified implementation in `QuadraticSieveStage` is limited to 80-bit inputs for educational purposes.

## When to Use

- Fast for medium-to-large inputs up to ~80 bits.
- Educational implementation suitable for learning the algorithm.

## Implementation

```python
from factorise.stages.quadratic_sieve import QuadraticSieveStage

stage = QuadraticSieveStage()
result = stage.attempt(1234567890123456789)
print(result.factor)
```
