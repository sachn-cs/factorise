# Pollard’s Rho Factorization

Pollard’s Rho is an integer factorization algorithm particularly effective for finding small prime factors of large composite numbers. It relies on the birthday paradox and cycle detection in a pseudo-random sequence.

## Problem Definition
Given a composite integer $n$, find a non-trivial factor $d$ such that $1 < d < n$.

## Mathematical Foundation

### Intuition: The Birthday Paradox
If we generate a sequence of integers $x_i$ randomly in the range $[0, n-1]$, a collision ($x_i = x_j$) is expected in $O(\sqrt{n})$ steps. However, for factorization, we are interested in a collision **modulo $p$**, where $p$ is a factor of $n$. This occurs when:
$$x_i \equiv x_j \pmod{p} \implies p \text{ divides } |x_i - x_j|$$
The expected number of iterations to find such a collision is significantly lower:
$$E[T] \approx \sqrt{\frac{\pi p}{2}} \approx 1.25 \sqrt{p}$$

### Sequence Generation and the "Rho" Structure
The algorithm uses a polynomial function, typically $f(x) = (x^2 + c) \pmod{n}$, to generate a sequence. Because $n$ is finite, the sequence must eventually repeat. The name "Rho" comes from the visual shape of the sequence:
1.  **The Tail**: A starting sequence of non-repeating values.
2.  **The Cycle**: Once a value repeats, the sequence enters a periodic loop.

The mapping $f(x) = x^2 + c$ is used because it approximates a random mapping, which is essential for the Birthday Paradox bounds to hold.

## Floyd’s Cycle-Finding Method
To detect a collision modulo $p$ without knowing $p$, we compute $\gcd(|x_i - x_j|, n)$. If $1 < \gcd < n$, the difference shares a common factor with $n$. Floyd's "tortoise and hare" approach uses two pointers:
-   **Tortoise**: $x_{i+1} = f(x_i)$
-   **Hare**: $y_{i+1} = f(f(y_i))$

At each step, we calculate $g = \gcd(|x - y|, n)$.

## Algorithm Steps
1.  **Initialize**: Choose $x_0$, $y_0$, and $c$. The `factorise` tool selects random values for these parameters.
2.  **Iterate**:
    -   $x = f(x)$
    -   $y = f(f(y))$
    -   $d = \gcd(|x - y|, n)$
3.  **Terminate**:
    -   If $1 < d < n$, return $d$.
    -   If $d = n$, the cycle collapsed (too many collisions). Retry with different $x_0$ or $c$.

## Complexity
The expected runtime is $O(n^{1/4})$, as $p \le \sqrt{n}$ for any composite $n$. This is a massive improvement over trial division's $O(n^{1/2})$.

## Implementation Details
```python
while g == 1:
    x = (x*x + c) % n
    y = (y*y + c) % n
    y = (y*y + c) % n
    g = gcd(abs(x - y), n)
```

## Sensitivity to Parameters
Polynomials like $f(x) = x^2$ or $f(x) = x^2 - 2$ should be avoided, as they can produce short cycles or highly structured sequences that defeat the probabilistic assumptions of the algorithm.
