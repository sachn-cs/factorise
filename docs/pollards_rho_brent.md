# Pollard's Rho with Brent's Improvement

Brent's improvement (1980) is a significant optimization of Pollard's Rho algorithm. It
replaces Floyd's cycle-finding method with a more efficient batched search strategy that
drastically reduces the number of GCD computations at the cost of a modest increase in
modular multiplications.

## The GCD Bottleneck

In the standard Pollard Rho algorithm a GCD is computed at every step. On modern
processors, modular multiplication is an order of magnitude faster than a GCD (which
requires multiple division operations). Brent's optimization exploits this asymmetry: perform
more multiplications to perform far fewer GCDs.

## Batching Logic

Brent's method accumulates the product of differences over a batch of $m$ iterations
(where $m$ is the configured `batch_size`, default 128):

$$Q = \prod_{i=1}^m |x - y_i| \pmod{n}$$

After every $m$ steps, a single $g = \gcd(Q, n)$ is computed. If any $|x - y_i|$ shares a
non-trivial factor with $n$, that factor also divides $Q$, so the single deferred GCD will
find it. This amortizes one GCD across $m$ iterations.

## Power-of-Two Search Phases

Unlike Floyd's tortoise-and-hare which moves at fixed relative speeds, Brent's method holds
the tortoise ($x$) stationary and advances the hare ($y$) in exponentially growing phases:
$r = 1, 2, 4, 8, \dots$ At the start of each phase $x$ is reset to the current $y$.

## Backtracking on Cycle Collapse

A batch failure occurs when $\gcd(Q, n) = n$ — too many factors accumulated in $Q$, washing
out the signal. The algorithm recovers by stepping through the saved batch one value at a
time and recomputing individual GCDs until a non-trivial factor is recovered or the
backtrack budget is exhausted.

## Comparison with Floyd's Algorithm

| Component | Floyd (standard) | Brent (improved) |
| :--- | :--- | :--- |
| Function evaluations | 2 per step | 1 per step (amortized) |
| GCD computations | 1 per step | $1/m$ per step |
| Throughput gain | baseline | **20 % – 40 %** |
| Memory overhead | $O(1)$ | $O(m)$ for backtrack history |

## Implementation Trace

The `factorise` implementation uses `math.gcd` for the deferred GCD and a configurable
`batch_size`. The backtrack loop is bounded by the remaining iteration budget:

```python
while g == 1:
    x = y
    for _ in range(r):
        y = (y * y + c) % n

    k = 0
    while k < r and g == 1:
        ys = y
        for _ in range(min(batch_size, r - k)):
            y = (y * y + c) % n
            q = (q * abs(x - y)) % n
        g = gcd(q, n)
        k += batch_size
    r *= 2
```

The algorithm is wrapped in an outer retry loop that selects fresh random seeds $(y, c)$
whenever the current attempt fails to find a factor.
