"""Quadratic Sieve (QS) as a pipeline stage."""

from __future__ import annotations

import math
import time
from typing import Any

from loguru import logger

from factorise.core import ensure_integer_input
from factorise.core import is_prime
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus
from factorise.pipeline import elapsed_ms
from factorise.stages.qs_shared import extract_factor
from factorise.stages.qs_shared import factor_over_base
from factorise.stages.qs_shared import find_dependency
from factorise.stages.qs_shared import is_small_prime

logger.disable("factorise")

MAX_QS_BIT_LENGTH: int = 80
DEFAULT_SMOOTHNESS_BOUND: int = 1000
MAX_FACTOR_BASE_SIZE: int = 60
RELATION_SEARCH_RADIUS: int = 200
RELATION_EXTRA_COUNT: int = 10
MAX_SQRT_MULTIPLIER: int = 3
MAX_SMALL_PRIME_DIVISOR: int = 2000


class QuadraticSieveStage(FactorStage):
    """Quadratic Sieve factorisation stage.

    Finds relations where a^2 mod n factors completely over a prime base,
    then uses Gaussian elimination over GF(2) to find a dependency and
    extract a factor via gcd.
    """

    name = "quadratic_sieve"

    def __init__(self, bound: int | None = None) -> None:
        """Initialise with a smoothness bound.

        Args:
            bound: The smoothness limit for the prime base.

        """
        self._bound = bound if bound is not None else DEFAULT_SMOOTHNESS_BOUND

    def attempt(self, n: int) -> StageResult:
        """Attempt to find a factor of *n* using the Quadratic Sieve."""
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

        factor = self._find_factor(n)
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

    def _find_factor(self, n: int) -> int | None:
        prime_base = self._build_prime_base(n)
        if len(prime_base) < 2:
            return None

        relations = self._find_smooth_relations(n, prime_base)
        if len(relations) < len(prime_base):
            return None

        dependency = find_dependency(relations, len(prime_base))
        if dependency is None:
            return None

        return extract_factor(n, relations, dependency, prime_base)

    def _build_prime_base(self, n: int) -> list[int]:
        base = [-1]
        limit = min(self._bound, MAX_SMALL_PRIME_DIVISOR)
        for candidate in range(3, limit, 2):
            if not is_small_prime(candidate):
                continue
            if pow(n, (candidate - 1) // 2, candidate) != 1:
                continue
            base.append(candidate)
            if len(base) >= MAX_FACTOR_BASE_SIZE:
                break
        return base

    def _find_smooth_relations(
        self,
        n: int,
        prime_base: list[int],
    ) -> list[dict[str, Any]]:
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
                relations.append(
                    {
                        "a": candidate,
                        "a2_mod_n": square_mod,
                        "exponents": exponents,
                    },)
                if len(relations) >= target_count:
                    return relations

        return relations
