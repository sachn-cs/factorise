# Pollard’s Rho with Brent’s Improvement

Brent’s improvement (1980) is a significant optimization of Pollard’s Rho algorithm. It replaces Floyd’s cycle-finding method with a more efficient search strategy and drastically reduces the computational pressure of Greatest Common Divisor (GCD) calls.

## The GCD Bottleneck
In the standard Pollard’s Rho algorithm, a GCD is computed at every step. In modern processors, modular multiplication and addition are significantly faster than GCD operations (which require multiple divisions). Brent's optimization exploits this by trade-off: performing more multiplications to perform fewer GCDs.

## Batching Logic
Brent’s method accumulates the product of differences over a "batch" of $m$ iterations (where $m$ is typically between 64 and 128). The accumulated product $Q$ is defined as:
$$Q = \prod_{i=1}^m |x - y_i| \pmod{n}$$
After every $m$ steps, we compute $g = \gcd(Q, n)$. If any $|x - y_i|$ shares a factor with $n$, the product $Q$ will also share that factor.

## Power-of-2 Search Distances
Unlike Floyd’s tortoise and hare, which move at different speeds, Brent’s method holds the tortoise ($x$) stationary while the hare ($y$) explores ahead in increasing powers of 2 ($r = 1, 2, 4, 8, \dots$).

## Backtracking Strategy
A common failure in batching is when "too many" factors are gathered in $Q$, causing $\gcd(Q, n) = n$. This happens if the batch size $m$ is too large and multiple factors are encountered.

To recover, the algorithm saves $y$ as $y_s$ before starting a batch. If the batch results in $g=n$, the algorithm steps through the batch one value at a time ($y_s \to y_{s+1} \dots$) computing individual GCDs until a non-trivial factor is recovered.

## Performance Analysis
By reducing GCD calls by a factor of $m$, Brent's method achieves a significant throughput increase. Furthermore, it only requires **one** function evaluation per step ($f(y)$), whereas Floyd's Hare requires **two**.

| Component | Floyd (Standard) | Brent (Improved) |
| :--- | :--- | :--- |
| **Generator Calls** | 3 per step | 1 per step (amortized) |
| **GCD Calls** | 1 per step | $1/m$ per step |
| **Logic Complexity** | Low | Moderate (due to backtrack) |
| **Throughput Gain** | Baseline | **20% - 40%** |

## Implementation Trace
The `factorise` tool implements Brent's Rho with a configurable `batch_size` (default 128) and a robust backtrack recovery phase.

```python
while g == 1:
    x = y
    for _ in range(r):
        y = (y * y + c) % n

    k = 0
    while k < r and g == 1:
        ys = y
        batch_limit = min(m, r - k)
        for _ in range(batch_limit):
            y = (y * y + c) % n
            q = (q * abs(x - y)) % n
        g = gcd(q, n)
        k += m
    r *= 2
```
