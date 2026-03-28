# Pollard’s Rho with Brent’s Improvement

Brent’s improvement (1980) is a significant optimization of Pollard’s Rho algorithm. It replaces Floyd’s cycle-finding method with a more efficient search strategy and drastically reduces the number of expensive Greatest Common Divisor (GCD) computations.

## Motivation
In the standard Pollard’s Rho algorithm, a GCD computation is performed at every single step. Since modular multiplications are much faster than GCD calls, the GCD becomes the primary bottleneck in software implementations.

## Differences from Floyd’s Cycle Detection
Floyd's method (tortoise and hare) requires 3 function evaluations and 1 GCD per step of the tortoise. Brent’s method:
1. Uses a fixed starting point for each "lap" (power of 2 length).
2. Accumulates a product of differences $(x - y_i)$ over several steps.
3. Performs a single GCD on the accumulated product after a "batch."

## Algorithm Steps
1. **Initialize**: $x, y, q, g, r, m$.
2. **Main Loop**:
   - Reset $x = y$.
   - For $i$ in $1$ to $r$: $y = f(y)$.
   - While $k < r$ and $g = 1$:
     - Save $y$ as $ys$.
     - Compute a batch of $m$ steps:
       - $y = f(y)$
       - $q = (q \cdot |x - y|) \pmod{n}$
     - Calculate $g = \gcd(q, n)$.
     - Increment $k$ by $m$.
   - Double the search distance $r = 2r$.
3. **Backtracking**: If $g = n$, the batch contained a collision that "swallowed" the cycle. Step back to $ys$ and re-run one-by-one with individual GCDs to recover the factor.

## Performance Improvements

### Reduced GCD Computations
By batching $m$ differences (typically $m=100$), the number of GCD calls is reduced by a factor of $m$. The rolling product $q$ will contain a factor of $n$ if any of its components share a factor with $n$.

### Better Function Utilization
Brent's method requires significantly fewer evaluations of the generator function $f(x)$ compared to Floyd's Hare, which evaluates the function twice per tortoise step.

## Comparison

| Feature | Floyd (Standard) | Brent (Improved) |
|---------|-----------------|------------------|
| Function Evalluations | 3 per step | 1 per step (amortized) |
| GCD Calls | 1 per step | 1 per $m$ steps |
| Memory | 2 variables | 4 variables |
| Performance | Baseline | ~20-30% faster |

## Trade-offs
Brent's method is more complex to implement due to the backtracking logic required when $g=n$. However, for numbers exceeding 40 bits, the performance gain from reduced GCD pressure is indispensable in production-grade factorizers.

## Pseudocode
```python
function pollard_brent(n, m=100):
    y, c, m = random(), random(), 100
    g, r, q = 1, 1, 1
    x, ys = 0, 0

    while g == 1:
        x = y
        for _ in range(r):
            y = f(y)
        k = 0
        while k < r and g == 1:
            ys = y
            for _ in range(min(m, r - k)):
                y = f(y)
                q = (q * abs(x - y)) % n
            g = gcd(q, n)
            k += m
        r *= 2

    if g == n: # Backtrack
        while True:
            ys = f(ys)
            g = gcd(abs(x - ys), n)
            if g > 1: break

    return g
```
