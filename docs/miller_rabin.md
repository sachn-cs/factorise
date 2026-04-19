# Miller-Rabin Primality Test

The Miller-Rabin primality test is a probabilistic algorithm that determines whether a number is a strong probable prime. It is an extension of Fermat's Little Theorem and is widely used in cryptography for generating large prime numbers.

## Mathematical Foundation

For a given odd integer $n > 2$, find the largest power of 2 that divides $n - 1$:
$$n - 1 = 2^s \cdot d$$
where $d$ is an odd number.

### The Strong Probable Prime Condition
A number $n$ passes the test for a base $a \in [2, n-2]$ if one of the following congruences holds:
1.  $a^d \equiv 1 \pmod{n}$
2.  $a^{2^r \cdot d} \equiv -1 \pmod{n}$ for some $0 \le r < s$.

If $n$ is prime, it MUST satisfy one of these conditions for all $a < n$. If $n$ fails these conditions for any $a$, it is definitely composite ($a$ is called a "witness" to the compositeness of $n$).

## Deterministic vs. Probabilistic

### Probabilistic Bound
For any composite $n$, at most $1/4$ of the bases $a \in [2, n-1]$ are "strong liars" (bases that fail to show the compositeness of $n$). By testing $k$ random bases, the probability of a false positive is:
$$P(\text{false positive}) \le 4^{-k}$$

### Deterministic Bounds for 64-bit Integers
For smaller integers, it is possible to make the test deterministic by choosing a specific set of bases. Research by Jaeschke and others has proven the following sets are sufficient:

| Range of $n$ | Required Bases |
| :--- | :--- |
| $n < 2,047$ | $\{2\}$ |
| $n < 1,373,653$ | $\{2, 3\}$ |
| $n < 25,326,001$ | $\{2, 3, 5\}$ |
| $n < 3,215,031,751$ | $\{2, 3, 5, 7\}$ |
| $n < 3,825,123,056,546,413,051$ | $\{2, 3, 5, 7, 11, 13, 17, 19, 23\}$ |

The `factorise` implementation uses the full 64-bit witness set (bases up to 23), making it **deterministic** for all standard machine integers.

## Algorithm Complexity
The time complexity of a single Miller-Rabin test is $O(k \cdot \log^3 n)$, where $k$ is the number of bases tested. Using Montgomery multiplication or other fast modular exponentiation techniques can slightly improve performance.

## Implementation Details
```python
def is_prime(n: int) -> bool:
    # Standard trial division for small primes (2, 3, 5, 7, ...)
    # Decomposition: n - 1 = 2^s * d
    # Loop through bases
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
