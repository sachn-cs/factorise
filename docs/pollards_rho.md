# Pollard’s Rho Factorization

Pollard’s Rho is an integer factorization algorithm particularly effective for finding small prime factors of large composite numbers. It relies on the birthday paradox and cycle detection in a pseudo-random sequence.

## Problem Definition
Given a composite integer $n$, find a non-trivial factor $d$ such that $1 < d < n$.

## Mathematical Foundation

### Intuition: Cycle Detection
If we generate a sequence of integers $x_i$ randomly in the range $[0, n-1]$, the birthday paradox suggests that two values will collide ($x_i = x_j$) in approximately $O(\sqrt{n})$ steps. However, to find a factor of $n$, we only need a collision modulo $p$, where $p$ is a factor of $n$. This occurs much sooner, in approximately $O(\sqrt{p})$ steps.

### Sequence Generation
The algorithm uses a polynomial function, typically $f(x) = (x^2 + c) \pmod{n}$, where $c$ is a constant (often $c=1$). This sequence is determined by its previous value, meaning it will eventually enter a cycle.

## Floyd’s Cycle-Finding Method
To detect a collision modulo $p$ ($x_i \equiv x_j \pmod{p}$) without knowing $p$, we compute $\gcd(|x_i - x_j|, n)$. If $1 < \gcd < n$, we have found a factor. Floyd's "tortoise and hare" approach uses two pointers:
- $x$ (tortoise): $x_{i+1} = f(x_i)$
- $y$ (hare): $y_{i+1} = f(f(y_i))$

## Algorithm Steps
1. **Initialize**: Choose $x_0 = 2$, $y_0 = 2$, and $c = 1$.
2. **Iterate**:
   - $x = f(x)$
   - $y = f(f(y))$
   - $d = \gcd(|x - y|, n)$
3. **Terminate**:
   - If $1 < d < n$, return $d$.
   - If $d = n$, the attempt failed (cycle collapsed). Retry with different $x_0$ or $c$.

## Complexity
The expected runtime is $O(\sqrt{p}) \le O(n^{1/4})$, where $p$ is the smallest prime factor of $n$. This makes it significantly faster than trial division ($O(\sqrt{n})$) for numbers with small to medium factors.

## Pseudocode
```python
function pollard_rho(n):
    if n % 2 == 0: return 2
    x = random(2, n-1)
    y = x
    c = random(1, n-1)
    g = 1

    while g == 1:
        x = (x*x + c) % n
        y = (y*y + c) % n
        y = (y*y + c) % n
        g = gcd(abs(x - y), n)

    if g == n:
        return failure # Retry with new c or starting x
    return g
```

## Sensitivity to Polynomial Choice
The algorithm rarely fails for $f(x) = x^2 + c$. However, $c=0$ or $c=-2$ should be avoided as they generate sequences that do not behave like random mappings, leading to much longer cycles or immediate failure.
