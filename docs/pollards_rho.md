# Pollard's Rho Factorization

Pollard's Rho is an integer factorisation algorithm particularly effective for finding small
to medium prime factors of large composite numbers. It exploits the birthday paradox and
cycle detection in a pseudo-random sequence.

## Problem Definition

Given a composite integer $n$, find a non-trivial factor $d$ such that $1 < d < n$.

## Mathematical Foundation

### Intuition: The Birthday Paradox

If a sequence of integers $x_i$ is generated uniformly at random in $[0, n-1]$, a collision
$x_i = x_j$ is expected in $O(\sqrt{n})$ steps. For factorisation, we seek a collision
**modulo $p$**, where $p$ is a factor of $n$:

$$x_i \equiv x_j \pmod{p} \implies p \text{ divides } |x_i - x_j|$$

Because $p \le \sqrt{n}$, such a collision is expected in only:

$$E[T] \approx 1.25\sqrt{p}$$

This is significantly faster than trial division's $O(\sqrt{n})$.

### Sequence Generation

The algorithm uses a polynomial function, typically $f(x) = (x^2 + c) \pmod{n}$, to generate
a pseudo-random sequence. Because $n$ is finite the sequence must eventually repeat. The
"Rho" name reflects the visual shape of the sequence path: a tail leading into a cycle.

The mapping $f(x) = x^2 + c$ is used because it approximates a random mapping, which is
essential for the birthday paradox bounds to hold. Polynomials such as $f(x) = x^2$ should be
avoided — they produce short or highly structured cycles.

## Floyd's Cycle-Finding Method

To detect a collision modulo $p$ without knowing $p$, we compute $g = \gcd(|x_i - y_j|, n)$
where the hare moves twice as fast as the tortoise:

- **Tortoise**: $x_{i+1} = f(x_i)$
- **Hare**: $y_{i+1} = f(f(y_i))$

At each step, if $1 < g < n$, the difference $|x_i - y_j|$ shares a non-trivial factor with $n$
— that factor is returned.

## Algorithm Steps

1. **Initialise**: Choose $x_0$, $y_0$, and $c$ randomly.
2. **Iterate**:
   - $x = f(x)$
   - $y = f(f(y))$
   - $d = \gcd(|x - y|, n)$
3. **Terminate**:
   - If $1 < d < n$, return $d$ (non-trivial factor found).
   - If $d = n$, the cycle collapsed; retry with different parameters.

## Complexity

The expected runtime is $O(n^{1/4})$ for finding the smallest prime factor. This is a massive
improvement over trial division's $O(\sqrt{n})$.

## Implementation

```python
def pollard_rho(n: int) -> int:
    x, y, c = randint(1, n-1), randint(1, n-1), randint(1, n-1)
    d = 1
    while d == 1:
        x = (x*x + c) % n
        y = (y*y + c) % n
        y = (y*y + c) % n
        d = gcd(abs(x - y), n)
    return d if d != n else pollard_rho(n)
```

`factorise` uses Brent's improvement over this basic algorithm: instead of one GCD per step,
multiple modular multiplications are performed and a single GCD is computed after a batch,
amortising the expensive GCD across many cheap multiplications.
