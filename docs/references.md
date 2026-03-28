# References

The algorithms implemented in `factorise` are based on foundational research in computational number theory.

## Miller (1976)
**Title:** Riemann's Hypothesis and Tests for Primality
**Author:** Gary L. Miller
**Year:** 1976
**Description:** Introduced first deterministic primality test based on the Generalized Riemann Hypothesis. This established the "witness" framework used in the Miller-Rabin test.
**Link:** [ACM Digital Library](https://dl.acm.org/doi/10.1145/800116.803773)

## Rabin (1980)
**Title:** Probabilistic Algorithm for Testing Primality
**Author:** Michael O. Rabin
**Year:** 1980
**Description:** Refined Miller's work into a probabilistic test that does not depend on the Riemann Hypothesis. Proved the error bound of $1/4$ per round.
**Link:** [Journal of Number Theory](https://www.sciencedirect.com/science/article/pii/0022314X80900840)

## Pollard (1975)
**Title:** A Monte Carlo Method for Factorization
**Author:** John M. Pollard
**Year:** 1975
**Description:** Introduced the Pollard’s Rho algorithm for integer factorization using Floyd’s cycle-finding strategy.
**Link:** [BIT Numerical Mathematics](https://link.springer.com/article/10.1007/BF01931034)

## Brent (1980)
**Title:** An Improved Monte Carlo Factorization Algorithm
**Author:** Richard P. Brent
**Year:** 1980
**Description:** Published the improved cycle-finding method that reduces GCD calls and ensures faster convergence in practice.
**Link:** [BIT Numerical Mathematics](https://link.springer.com/article/10.1007/BF01933190)

## Further Reading
- **Jaeschke (1993):** On strong pseudoprimes to several bases. Defined the deterministic bounds for Miller-Rabin.
- **Sorenson & Webster (2015):** Deterministic Miller-Rabin Primality Test for Numbers less than $2^{64}$.
