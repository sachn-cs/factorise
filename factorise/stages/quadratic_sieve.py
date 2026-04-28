"""Quadratic Sieve (QS) as a pipeline stage."""

from __future__ import annotations

import logging
import math
import time

from factorise.core import ensure_integer_input
from factorise.core import is_prime
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus
from factorise.pipeline import elapsed_ms
from factorise.stages.qs_shared import QSRelation
from factorise.stages.qs_shared import extract_factor
from factorise.stages.qs_shared import factor_over_base
from factorise.stages.qs_shared import find_dependency
from factorise.stages.qs_shared import is_small_prime

LOG = logging.getLogger("factorise")

QS_MAX_BIT_LENGTH: int = 80
DEFAULT_SMOOTHNESS_BOUND: int = 1000
MAX_FACTOR_BASE_SIZE: int = 60
RELATION_SEARCH_RADIUS: int = 200
RELATION_EXTRA_COUNT: int = 10
MAX_SQRT_MULTIPLIER: int = 3
MAX_SMALL_PRIME_DIVISOR: int = 2000


class QuadraticSieveStage(FactorStage):
    """Quadratic Sieve factorisation stage.

    Finds relations where ``a^2 mod n`` factors completely over a prime base,
    then uses Gaussian elimination over GF(2) to find a dependency and
    extract a factor via gcd.
    """

    name = "quadratic_sieve"

    def __init__(self, bound: int | None = None) -> None:
        """Initialise with a smoothness bound.

        Args:
            bound: The smoothness limit for the prime base.

        """
        self.__bound = bound if bound is not None else DEFAULT_SMOOTHNESS_BOUND

    def attempt(self, n: int) -> StageResult:
        """Attempt to find a factor of *n* using the Quadratic Sieve.

        Args:
            n: The integer to factor.

        Returns:
            StageResult describing the outcome.

        """
        start = time.monotonic()
        ensure_integer_input(n)
        bits = n.bit_length()

        LOG.debug("stage=%s n=%d bits=%d action=attempt", self.name, n, bits)

        if n < 3:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d status=SKIPPED reason=%s elapsed_ms=%.2f",
                self.name,
                n,
                "n < 3",
                elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed,
                reason="n < 3",
            )

        if n % 2 == 0:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d factor=%d elapsed_ms=%.2f iterations=1",
                self.name,
                n,
                2,
                elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=2,
                elapsed_ms=elapsed,
                iterations_used=1,
            )

        if n.bit_length() > QS_MAX_BIT_LENGTH:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d status=SKIPPED reason=%s elapsed_ms=%.2f",
                self.name,
                n,
                f"n too large for QS ({n.bit_length()} bits > {QS_MAX_BIT_LENGTH})",
                elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed,
                reason=
                (f"n too large for QS ({n.bit_length()} bits > {QS_MAX_BIT_LENGTH})"
                ),
            )

        if is_prime(n):
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d status=SKIPPED reason=%s elapsed_ms=%.2f",
                self.name,
                n,
                "n is prime",
                elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed,
                reason="n is prime",
            )

        root_n = math.isqrt(n)
        if root_n * root_n == n:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d factor=%d elapsed_ms=%.2f iterations=1",
                self.name,
                n,
                root_n,
                elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=root_n,
                elapsed_ms=elapsed,
                reason="n is a perfect square",
            )

        factor = self.__find_factor(n)
        if factor is not None and 1 < factor < n:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d factor=%d elapsed_ms=%.2f",
                self.name,
                n,
                factor,
                elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=factor,
                elapsed_ms=elapsed,
            )

        elapsed = elapsed_ms(start)
        LOG.debug(
            "stage=%s n=%d status=FAILURE elapsed_ms=%.2f reason=%s",
            self.name,
            n,
            elapsed,
            "QS did not find a factor",
        )
        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=elapsed,
            reason="QS did not find a factor",
        )

    def __find_factor(self, n: int) -> int | None:
        base_start = time.monotonic()
        prime_base = self.__build_prime_base(n)
        LOG.debug(
            "stage=%s n=%d action=build_prime_base elapsed_ms=%.2f size=%d",
            self.name,
            n,
            elapsed_ms(base_start),
            len(prime_base),
        )
        if len(prime_base) < 2:
            return None

        rel_start = time.monotonic()
        relations = self.__find_smooth_relations(n, prime_base)
        LOG.debug(
            "stage=%s n=%d action=find_relations elapsed_ms=%.2f count=%d",
            self.name,
            n,
            elapsed_ms(rel_start),
            len(relations),
        )
        if len(relations) < len(prime_base):
            return None

        dep_start = time.monotonic()
        dependency = find_dependency(relations, len(prime_base))
        LOG.debug(
            "stage=%s n=%d action=find_dependency elapsed_ms=%.2f",
            self.name,
            n,
            elapsed_ms(dep_start),
        )
        if dependency is None:
            return None

        extract_start = time.monotonic()
        factor = extract_factor(n, relations, dependency, prime_base)
        LOG.debug(
            "stage=%s n=%d action=extract_factor elapsed_ms=%.2f",
            self.name,
            n,
            elapsed_ms(extract_start),
        )
        return factor

    def __build_prime_base(self, n: int) -> list[int]:
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
    ) -> list[QSRelation]:
        relations: list[QSRelation] = []
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
                relations.append(
                    {
                        "a": candidate,
                        "a2_mod_n": square_mod,
                        "exponents": exponents,
                    },)
                if len(relations) >= target_count:
                    return relations

        return relations
