# Miller-Rabin Primality Test

The Miller-Rabin primality test is a probabilistic algorithm that determines whether a
number is a strong probable prime. It is an extension of Fermat's Little Theorem and is
widely used in cryptography for generating large prime numbers.

## Mathematical Foundation

For a given odd integer $n > 2$, write $n - 1 = 2^s \cdot d$ where $d$ is odd:
$$n - 1 = 2^s \cdot d$$

### The Strong Probable Prime Condition

A number $n$ passes the test for a base $a \in [2, n-2]$ if one of the following holds:

1. $a^d \equiv 1 \pmod{n}$
2. $a^{2^r \cdot d} \equiv -1 \pmod{n}$ for some $0 \le r < s$

If $n$ is prime, it **must** satisfy one of these conditions for every base tested. If $n$
fails for any base, that base is a *witness* to the compositeness of $n$.

## Deterministic vs. Probabilistic

### Probabilistic Bound

For any composite $n$, at most $1/4$ of the bases $a \in [2, n-1]$ are "strong liars" —
bases that incorrectly pass the test. After testing $k$ random bases, the false-positive
probability is:
$$P(\text{false positive}) \le 4^{-k}$$

### Deterministic Bounds

Research by Jaeschke (1993) and Sorenson & Webster (2015) established witness sets that make
the test deterministic for all integers in a given range:

| Range of $n$ | Sufficient bases |
| :--- | :--- |
| $n < 2{,}047$ | $\{2\}$ |
| $n < 1{,}373{,}653$ | $\{2, 3\}$ |
| $n < 25{,}326{,}001$ | $\{2, 3, 5\}$ |
| $n < 3{,}215{,}031{,}751$ | $\{2, 3, 5, 7\}$ |
| $n < 10^{12}$ | $\{2, 3, 5, 7, 11, 13\}$ (Jaeschke) |
| $n < 2^{64}$ | $\{2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37\}$ |

`factorise` uses the **adaptive witness set**: 6 bases for $n < 10^{12}$, and the full 12-base
set for $10^{12} \le n < 2^{64}$. This makes the test deterministic across the entire 64-bit
range — no probabilistic false positives are possible for machine integers.

## Algorithm Complexity

Each base requires one modular exponentiation ($O(\log n)$ multiplications) plus up to $s-1$
squarings. With fast modular arithmetic the time complexity is $O(k \cdot \log^3 n)$ where
$k$ is the number of bases. For 64-bit inputs the constant factor is small (at most 12
bases).

## Implementation Notes

```python
from source.core import is_prime

# Deterministic for all n < 2^64
is_prime(2**61 - 1)   # True  (Mersenne prime M61)
is_prime(2**61 - 1 + 2)  # False (composite, caught by base 2)
```

The implementation performs two early-exit divisibility checks for 2 and 3 before invoking
Miller-Rabin. It also short-circuits when the input is in the precomputed witness table
(`WITNESSES_SET`), avoiding unnecessary modular exponentiation for small primes.

## Practical Considerations

Miller-Rabin is almost always preferred over the deterministic AKS primality test
($O(\log^6 n)$) due to its significantly lower complexity and high empirical reliability.
It is the standard test used by cryptographic libraries for RSA key generation.
