# Pollard p−1

Pollard's p−1 method finds factors `p` where `p−1` is smooth (all prime factors are small).

## Algorithm

1. Choose a smoothness bound `B`.
2. Compute `a = a^B! mod n` (or `a^L mod n` where `L` is the lcm of integers up to `B`).
3. Compute `d = gcd(a − 1, n)`.
4. If `1 < d < n`, then `d` is a non-trivial factor.

## Progressive Bounds

The `ImprovedPollardPMinusOneStage` uses progressively larger bounds (10^6, 10^7, 10^8, 10^9) and multiple bases (2, 3, 5, 7, 11) to increase the chance of finding a smooth factor.

## When to Use

- Effective when the input has a factor `p` where `p−1` is smooth.
- Good intermediate stage between trial division and Pollard's Rho.

## Implementation

```python
from factorise.stages.improved_pm1 import ImprovedPollardPMinusOneStage

stage = ImprovedPollardPMinusOneStage(bounds=(10**6, 10**7), bases=(2, 3, 5))
result = stage.attempt(91, config=FactoriserConfig())
```
