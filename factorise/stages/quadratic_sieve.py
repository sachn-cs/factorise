"""Quadratic Sieve (QS) as a pipeline stage.

The Quadratic Sieve is a general-purpose factorisation algorithm particularly
effective for medium-sized composite numbers (up to ~100 digits). It works by
finding many integer values whose squares modulo n have only small prime factors,
then using linear algebra over GF(2) to combine these relations into a square,
which yields a factor via a GCD computation.

This implementation is simplified but correct. It is suitable for educational
purposes and for handling medium-sized inputs that are beyond ECM's reach but
below the threshold for GNFS.

For production use with very large numbers, use an external GNFS implementation.
"""

from __future__ import annotations

import math
import time
from typing import Any

from loguru import logger

from factorise.core import FactoriserConfig
from factorise.core import ensure_integer_input
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus
from factorise.pipeline import elapsed_ms
from factorise.stages._qs_shared import extract_factor
from factorise.stages._qs_shared import factor_over_base
from factorise.stages._qs_shared import find_dependency
from factorise.stages._qs_shared import is_small_prime

logger.disable("factorise")

# Maximum input size for QS in this implementation (in bits).
# Above this, QS becomes impractical in pure Python.
MAX_QS_BIT_LENGTH: int = 80

# Default smoothness bound for the factor base.
DEFAULT_SMOOTHNESS_BOUND: int = 1000

# Maximum number of primes in the factor base.
MAX_FACTOR_BASE_SIZE: int = 60

# How far around sqrt(n) to search for smooth relations.
RELATION_SEARCH_RADIUS: int = 200

# How many extra relations to collect beyond the factor base size.
RELATION_EXTRA_COUNT: int = 10

# Maximum absolute multiplier for sqrt(n) when searching relations.
MAX_SQRT_MULTIPLIER: int = 3

# Maximum primality test divisor for small primes.
MAX_SMALL_PRIME_DIVISOR: int = 2000


class QuadraticSieveStage(FactorStage):
    """Quadratic Sieve factorisation stage.

    The Quadratic Sieve works by:
    1. Selecting a smoothness bound B.
    2. Finding "relations": integers a where a² mod n factors completely over the
       prime base {-1, p₁, p₂, ..., pₖ} where all pᵢ ≤ B.
    3. Using Gaussian elimination over GF(2) to find a dependency between rows
       of the relation matrix.
    4. Computing gcd(x ± y, n) to extract a factor.

    This implementation is intentionally simplified and not optimised for
    large inputs. It uses a small prime base and limited relation search.
    """

    name = "quadratic_sieve"

    def __init__(self, bound: int | None = None) -> None:
        """Initialise the Quadratic Sieve stage.

        Args:
            bound: Upper limit for primes in the factor base. Defaults to
                DEFAULT_SMOOTHNESS_BOUND.
        """
        self.__bound = bound if bound is not None else DEFAULT_SMOOTHNESS_BOUND

    def attempt(self, n: int, *, config: FactoriserConfig) -> StageResult:
        """Attempt to find a non-trivial factor of n using the Quadratic Sieve.

        Args:
            n: The integer to factor.
            config: Algorithm parameters.

        Returns:
            StageResult describing the outcome.
        """
        from factorise.core import is_prime

        start = time.monotonic()
        ensure_integer_input(n)

        if n < 3:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed_ms(start),
                reason="n < 3",
            )

        if n.bit_length() > MAX_QS_BIT_LENGTH:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed_ms(start),
                reason=
                (f"n too large for QS ({n.bit_length()} bits > {MAX_QS_BIT_LENGTH})"
                ),
            )

        if is_prime(n):
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed_ms(start),
                reason="n is prime",
            )

        root_n = math.isqrt(n)
        if root_n * root_n == n:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=root_n,
                elapsed_ms=elapsed_ms(start),
                reason="n is a perfect square",
            )

        factor = self.__qs_find_factor(n)
        if factor is not None and 1 < factor < n:
            logger.debug(
                "stage={stage} n={n} factor={factor}",
                stage=self.name,
                n=n,
                factor=factor,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=factor,
                elapsed_ms=elapsed_ms(start),
            )

        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=elapsed_ms(start),
            reason="QS did not find a factor",
        )

    def __qs_find_factor(self, n: int) -> int | None:
        """Run the Quadratic Sieve to find a factor of n.

        Args:
            n: A positive odd composite integer that is not a perfect square.

        Returns:
            A non-trivial factor, or None if no factor is found.
        """
        prime_base = self.__build_prime_base(n)
        if len(prime_base) < 2:
            return None

        relations = self.__find_smooth_relations(n, prime_base)
        if len(relations) < len(prime_base):
            return None

        dependency = find_dependency(relations, len(prime_base))
        if dependency is None:
            return None

        factor = extract_factor(n, relations, dependency, prime_base)
        return factor

    def __build_prime_base(self, n: int) -> list[int]:
        """Build the factor base of primes where n is a quadratic residue.

        The factor base always includes -1 to handle negative values.

        Args:
            n: The integer being factored.

        Returns:
            A list of primes (and -1) suitable for the factor base.
        """
        base = [-1]
        limit = min(self.__bound, MAX_SMALL_PRIME_DIVISOR)
        for candidate in range(3, limit, 2):
            if not is_small_prime(candidate):
                continue
            if pow(n, (candidate - 1) // 2, candidate) != 1:
                continue
            base.append(candidate)
            if len(base) >= MAX_FACTOR_BASE_SIZE:
                break
        return base

    def __find_smooth_relations(
        self,
        n: int,
        prime_base: list[int],
    ) -> list[dict[str, Any]]:
        """Find smooth relations a² ≡ product of prime_base^e (mod n).

        Each relation is a dictionary with keys:
            a: The integer used in the relation.
            a2_mod_n: The value a² mod n.
            exponents: List of exponents for each prime in the base.

        Args:
            n: The integer being factored.
            prime_base: The factor base.

        Returns:
            A list of smooth relations.
        """
        relations = []
        target_count = len(prime_base) + RELATION_EXTRA_COUNT
        sqrt_n = math.isqrt(n) + 1

        for multiplier in range(1, MAX_SQRT_MULTIPLIER + 1):
            center = multiplier * sqrt_n
            start = max(1, center - RELATION_SEARCH_RADIUS)
            end = center + 4 * RELATION_SEARCH_RADIUS
            for candidate in range(start, end):
                square_mod = (candidate * candidate) % n
                if square_mod == 0:
                    continue
                exponents = factor_over_base(square_mod, prime_base)
                if exponents is None:
                    continue
                relations.append({
                    "a": candidate,
                    "a2_mod_n": square_mod,
                    "exponents": exponents,
                })
                if len(relations) >= target_count:
                    return relations

        return relations
