# References

The algorithms implemented in `factorise` are based on foundational research in computational number theory and modern refinements for machine-integer factorization.

## Primary Sources

### Miller (1976)
**Title:** Riemann's Hypothesis and Tests for Primality
**Author:** Gary L. Miller
**Year:** 1976
**Description:** Established the "witness" mathematical framework for primality testing.
**Link:** [ACM Digital Library](https://dl.acm.org/doi/10.1145/800116.803773)

### Rabin (1980)
**Title:** Probabilistic Algorithm for Testing Primality
**Author:** Michael O. Rabin
**Year:** 1980
**Description:** Refined Miller's test into the probabilistic standard used today, proving the $1/4$ error bound.
**Link:** [Journal of Number Theory](https://www.sciencedirect.com/science/article/pii/0022314X80900840)

### Pollard (1975)
**Title:** A Monte Carlo Method for Factorization
**Author:** John M. Pollard
**Year:** 1975
**Description:** Introduced the Pollard’s Rho algorithm for factorization using random mappings.
**Link:** [BIT Numerical Mathematics](https://link.springer.com/article/10.1007/BF01931034)

### Brent (1980)
**Title:** An Improved Monte Carlo Factorization Algorithm
**Author:** Richard P. Brent
**Year:** 1980
**Description:** Published the improved cycle-finding method that reduces GCD pressure via batching.
**Link:** [BIT Numerical Mathematics](https://link.springer.com/article/10.1007/BF01933190)

## Deterministic Benchmarking & Extensions

### Jaeschke (1993)
**Title:** On strong pseudoprimes to several bases
**Author:** Gerhard Jaeschke
**Description:** Derived the deterministic bases for Miller-Rabin for numbers up to $10^{18}$ and beyond.
**Link:** [Mathematics of Computation](https://www.ams.org/journals/mcom/1993-61-204/S0025-5718-1993-1192971-X/)

### Sorenson & Webster (2015)
**Title:** Strong Pseudoprimes to 12 Bases
**Description:** Modern refinement of Jaeschke’s work, proving deterministic witness sets for 64-bit integers.
**Link:** [ArXiv PDF](https://arxiv.org/abs/1503.01800)

### Bach (1990)
**Title:** Explicit Bounds for Primality Testing and Related Problems
**Description:** Provided deep theoretical bounds on the performance and reliability of probabilistic algorithms in number theory.

## Further Reading
- **Crandall & Pomerance:** *Prime Numbers: A Computational Perspective* (Springer). The gold standard textbook for implementing these algorithms.
- **Knuth:** *The Art of Computer Programming, Volume 2: Seminumerical Algorithms*. Section 4.5.4 contains foundational analysis of Rho-methods.
