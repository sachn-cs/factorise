# Trial Division

Trial division is the simplest factorisation method: test whether the input is divisible by each prime in a precomputed list.

## 30-Wheel Optimisation

The `OptimizedTrialDivisionStage` uses a 30-wheel to skip multiples of 2, 3, and 5, eliminating ~73% of candidates. Combined with an extended prime table (1000 primes up to ~7919), this finds small factors very quickly.

## When to Use

- Best for inputs with small prime factors (practically any n < 10^12).
- Used as the first gate in the multi-stage pipeline.
- Very fast: O(π(b)) where b is the bound.

## Implementation

```python
from factorise.stages.trial_division import OptimizedTrialDivisionStage

stage = OptimizedTrialDivisionStage(bound=10_000)
result = stage.attempt(123456, config=FactoriserConfig())
print(result.factor)  # 2
```
