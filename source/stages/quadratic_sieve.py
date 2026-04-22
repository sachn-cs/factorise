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
from typing import TYPE_CHECKING

from loguru import logger

from source.pipeline import FactorStage
from source.pipeline import StageResult
from source.pipeline import StageStatus

if TYPE_CHECKING:
    from source.core import FactoriserConfig

logger.disable("factorise")

# Maximum input size for QS in this implementation (in bits).
# Above this, QS becomes impractical in pure Python.
_MAX_QS_BITS = 80

# Default smoothness bound for the factor base.
_DEFAULT_SMOOTHNESS_BOUND = 1000

# Maximum number of primes in the factor base.
_MAX_FACTOR_BASE_SIZE = 60

# How far around sqrt(n) to search for smooth relations.
_RELATION_SEARCH_RADIUS = 200

# How many extra relations to collect beyond the factor base size.
_RELATION_EXTRA_COUNT = 10

# Maximum absolute multiplier for sqrt(n) when searching relations.
_MAX_SQRT_MULTIPLIER = 3

# Maximum primality test divisor for small primes.
_MAX_SMALL_PRIME_DIVISOR = 2000


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
                _DEFAULT_SMOOTHNESS_BOUND.
        """
        self._bound = bound if bound is not None else _DEFAULT_SMOOTHNESS_BOUND

    def attempt(self, n: int, *, config: FactoriserConfig) -> StageResult:
        """Attempt to find a non-trivial factor of n using the Quadratic Sieve.

        Args:
            n: The integer to factor.
            config: Algorithm parameters.

        Returns:
            StageResult describing the outcome.
        """
        from source.core import is_prime
        from source.core import validate_int

        start = time.monotonic()
        validate_int(n)

        if n < 3:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=self._elapsed(start),
                reason="n < 3",
            )

        if n.bit_length() > _MAX_QS_BITS:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=self._elapsed(start),
                reason=(
                    f"n too large for QS ({n.bit_length()} bits > {_MAX_QS_BITS})"
                ),
            )

        if is_prime(n):
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=self._elapsed(start),
                reason="n is prime",
            )

        root_n = math.isqrt(n)
        if root_n * root_n == n:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=root_n,
                elapsed_ms=self._elapsed(start),
                reason="n is a perfect square",
            )

        factor = self._qs_factor(n)
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
                elapsed_ms=self._elapsed(start),
            )

        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=self._elapsed(start),
            reason="QS did not find a factor",
        )

    def _qs_factor(self, n: int) -> int | None:
        """Run the Quadratic Sieve to find a factor of n.

        Args:
            n: A positive odd composite integer that is not a perfect square.

        Returns:
            A non-trivial factor, or None if no factor is found.
        """
        prime_base = self._build_prime_base(n)
        if len(prime_base) < 2:
            return None

        relations = self._find_relations(n, prime_base)
        if len(relations) < len(prime_base):
            return None

        dependency = self._find_dependency(relations, len(prime_base))
        if dependency is None:
            return None

        factor = self._extract_factor(n, relations, dependency, prime_base)
        return factor

    def _build_prime_base(self, n: int) -> list[int]:
        """Build the factor base of primes where n is a quadratic residue.

        The factor base always includes -1 to handle negative values.

        Args:
            n: The integer being factored.

        Returns:
            A list of primes (and -1) suitable for the factor base.
        """
        base = [-1]
        limit = min(self._bound, _MAX_SMALL_PRIME_DIVISOR)
        for candidate in range(3, limit, 2):
            if not self._is_small_prime(candidate):
                continue
            if pow(n, (candidate - 1) // 2, candidate) != 1:
                continue
            base.append(candidate)
            if len(base) >= _MAX_FACTOR_BASE_SIZE:
                break
        return base

    def _is_small_prime(self, candidate: int) -> bool:
        """Test whether a small integer is prime.

        Args:
            candidate: The integer to test.

        Returns:
            True if candidate is prime, False otherwise.
        """
        if candidate < 2:
            return False
        if candidate % 2 == 0:
            return candidate == 2
        limit = int(candidate**0.5) + 1
        for divisor in range(3, limit, 2):
            if candidate % divisor == 0:
                return False
        return True

    def _find_relations(
        self,
        n: int,
        prime_base: list[int],
    ) -> list[dict]:
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
        target_count = len(prime_base) + _RELATION_EXTRA_COUNT
        sqrt_n = math.isqrt(n) + 1

        for multiplier in range(1, _MAX_SQRT_MULTIPLIER + 1):
            center = multiplier * sqrt_n
            start = max(1, center - _RELATION_SEARCH_RADIUS)
            end = center + 4 * _RELATION_SEARCH_RADIUS
            for candidate in range(start, end):
                square_mod = (candidate * candidate) % n
                if square_mod == 0:
                    continue
                exponents = self._factor_over_base(square_mod, prime_base)
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

    def _factor_over_base(
        self,
        value: int,
        prime_base: list[int],
    ) -> list[int] | None:
        """Factor a value over the given prime base.

        Args:
            value: The integer to factor.
            prime_base: The list of allowed primes (and -1).

        Returns:
            A list of exponents (one per prime in the base), or None if the
            value has a prime factor outside the base.
        """
        exponents = [0] * len(prime_base)
        remaining = value

        if remaining < 0:
            exponents[0] = 1
            remaining = -remaining

        for index, prime in enumerate(prime_base):
            if prime == -1:
                continue
            if prime * prime > remaining:
                break
            if remaining % prime != 0:
                continue
            count = 0
            while remaining % prime == 0:
                remaining //= prime
                count += 1
            exponents[index] = count

        if remaining == 1:
            return exponents

        if remaining in prime_base:
            index = prime_base.index(remaining)
            exponents[index] += 1
            return exponents

        return None

    def _find_dependency(
        self,
        relations: list[dict],
        num_primes: int,
    ) -> list[int] | None:
        """Find a linear dependency among relations using Gaussian elimination.

        Filters out trivial relations (all even exponents) before elimination,
        since they produce x ≡ y (mod n) and never yield a non-trivial factor.

        Args:
            relations: The list of smooth relations.
            num_primes: The number of primes in the factor base.

        Returns:
            A binary vector indicating which relations form a dependency,
            or None if no dependency is found.
        """
        non_trivial = [
            rel
            for rel in relations
            if any(exp % 2 == 1 for exp in rel["exponents"])
        ]
        if len(non_trivial) < num_primes:
            return None

        rows: list[list[int]] = []
        for index, rel in enumerate(non_trivial):
            mask = 0
            for j, exp in enumerate(rel["exponents"]):
                if exp % 2 == 1:
                    mask |= 1 << j
            history = 1 << index
            rows.append([mask, history])

        row_index = 0
        for col in range(num_primes):
            pivot = -1
            for r in range(row_index, len(rows)):
                if (rows[r][0] >> col) & 1:
                    pivot = r
                    break
            if pivot == -1:
                continue

            rows[row_index], rows[pivot] = rows[pivot], rows[row_index]

            for r in range(len(rows)):
                if r != row_index and ((rows[r][0] >> col) & 1):
                    rows[r][0] ^= rows[row_index][0]
                    rows[r][1] ^= rows[row_index][1]

            row_index += 1
            if row_index >= len(rows):
                break

        for row in rows:
            mask, history = row
            if mask == 0 and history != 0:
                vector = [0] * len(non_trivial)
                for bit in range(len(non_trivial)):
                    if (history >> bit) & 1:
                        vector[bit] = 1
                return vector

        return None

    def _extract_factor(
        self,
        n: int,
        relations: list[dict],
        dependency: list[int],
        prime_base: list[int],
    ) -> int | None:
        """Extract a non-trivial factor from a dependency.

        Computes x = product of a_i and y = product of p_j^(e_j/2),
        then returns gcd(x ± y, n) if it yields a non-trivial factor.

        Args:
            n: The integer being factored.
            relations: The list of smooth relations.
            dependency: Binary vector indicating which relations to combine.
            prime_base: The factor base.

        Returns:
            A non-trivial factor, or None if no useful factor is found.
        """
        product_x = 1
        product_y = 1
        for index, rel in enumerate(relations):
            if not dependency[index]:
                continue
            product_x = (product_x * rel["a"]) % n
            for prime_index, exp in enumerate(rel["exponents"]):
                if exp <= 0:
                    continue
                prime = prime_base[prime_index]
                if prime == -1:
                    continue
                product_y = (product_y * pow(prime, exp // 2, n)) % n

        candidate = math.gcd(product_x - product_y, n)
        if 1 < candidate < n:
            return candidate

        candidate = math.gcd(product_x + product_y, n)
        if 1 < candidate < n:
            return candidate

        return None

    def _elapsed(self, start: float) -> float:
        """Compute elapsed time in milliseconds.

        Args:
            start: The start time from time.monotonic().

        Returns:
            Elapsed time in milliseconds.
        """
        return (time.monotonic() - start) * 1000
