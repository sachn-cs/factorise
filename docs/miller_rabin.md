# Miller–Rabin Primality Test

The Miller–Rabin Primality Test is a probabilistic primality test used to determine whether a given integer is a "strong probable prime." Founded on properties of strong pseudoprimes, it is one of the most efficient algorithms for testing the primality of large integers.

## Problem Definition
Given an odd integer $n > 2$, determine whether $n$ is prime or composite.

## Mathematical Foundation

### Fermat’s Little Theorem
If $n$ is prime and $a$ is not divisible by $n$, then $a^{n-1} \equiv 1 \pmod{n}$. If this property fails for some $a$, $n$ is certainly composite.

### Strong Probable Primes
For an odd prime $n$, let $n-1 = 2^s \cdot d$ where $d$ is odd. For any base $a$ such that $\gcd(a, n) = 1$, one of the following must hold:
1. $a^d \equiv 1 \pmod{n}$
2. $a^{2^r \cdot d} \equiv -1 \pmod{n}$ for some $0 \le r < s$.

If an integer $n$ satisfies one of these conditions for a base $a$, $n$ is a **strong probable prime** to the base $a$. If $n$ is composite but satisfies these conditions, $a$ is called a **strong liar** for $n$.

## Algorithm Steps

1. **Input**: Odd integer $n > 2$ and number of rounds $k$ (or a fixed set of bases).
2. **Setup**: Write $n - 1 = 2^s \cdot d$ by repeatedly dividing $n-1$ by 2.
3. **Round**: For each round/base $a$:
   a. Compute $x = a^d \pmod{n}$.
   b. If $x = 1$ or $x = n - 1$, the base $a$ passes. Continue to the next base.
   c. Repeat $s-1$ times:
      i. $x = x^2 \pmod{n}$.
      ii. If $x = n - 1$, the base $a$ passes. Continue to the next base.
   d. If the loop completes without passing, $n$ is **composite**.
4. **Conclusion**: If all $k$ bases pass, $n$ is **probably prime**.

## Deterministic vs Probabilistic

### Probabilistic Variant
By randomly choosing $k$ bases $a \in [2, n-2]$, the probability of a composite number $n$ passing $k$ rounds is at most $4^{-k}$. This makes the test extremely reliable for large $k$ (e.g., $k=40$).

### Deterministic Variant
For integers below specific bounds, the test becomes **fully deterministic** if tested against a specific set of prime bases.
- For $n < 2^{64}$, the bases $\{2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37\}$ are sufficient to guarantee primality.

## Complexity
The time complexity of a single round is $O(\log^3 n)$ using binary exponentiation (or $O(\log^2 n \cdot \log \log n \cdot \log \log \log n)$ with Fast Fourier Transform multiplication). The total complexity for $k$ rounds is $O(k \log^3 n)$.

## Pseudocode
```python
function is_prime(n, witnesses):
    if n < 2: return False
    if n == 2 or n == 3: return True
    if n % 2 == 0: return False

    # Write n - 1 as 2^s * d
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1

    for a in witnesses:
        if a >= n: break
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue

        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False # Composite

    return True # Strong probable prime
```

## Practical Considerations
Miller-Rabin is almost always preferred over the deterministic AKS primality test ($O(\log^6 n)$) due to its significantly lower complexity and high empirical reliability. It is the standard test used by cryptographic libraries for RSA key generation.
