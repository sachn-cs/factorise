"""Self-Initializing Quadratic Sieve (SIQS) as a pipeline stage."""

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

LOG = logging.getLogger("factorise")

SIQS_MAX_BIT_LENGTH: int = 110
MAX_SMALL_PRIME_DIVISOR: int = 2000
MIN_RELATIONS: int = 10
DEFAULT_FACTOR_BASE_LIMIT: int = 100
RELATION_SEARCH_RADIUS: int = 200
RELATION_SEARCH_MULTIPLIER: int = 4
MAX_SQRT_MULTIPLIER: int = 3


class SIQSStage(FactorStage):
    """Self-Initializing Quadratic Sieve factorisation stage.

    SIQS is the practical choice for 60–110 digit composites in pure Python.
    Beyond that, an external GNFS implementation is required.
    """

    name = "siqs"

    def __init__(self, max_bit_length: int | None = None) -> None:
        """Initialise with a maximum bit length.

        Args:
            max_bit_length: Numbers above this bit length are skipped.

        """
        self.__max_bit_length = (max_bit_length if max_bit_length is not None
                                 else SIQS_MAX_BIT_LENGTH)

    def attempt(self, n: int) -> StageResult:
        """Attempt to find a factor of *n* using SIQS.

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

        if n.bit_length() > self.__max_bit_length:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d status=SKIPPED reason=%s elapsed_ms=%.2f",
                self.name,
                n,
                f"n ({n.bit_length()} bits) exceeds SIQS maximum "
                f"({self.__max_bit_length} bits)",
                elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed,
                reason=(f"n ({n.bit_length()} bits) exceeds SIQS maximum "
                        f"({self.__max_bit_length} bits)"),
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
            "SIQS found no factor",
        )
        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=elapsed,
            reason="SIQS found no factor",
        )

    def __find_factor(self, n: int) -> int | None:
        bound_start = time.monotonic()
        bound = self.__compute_smoothness_bound(n)
        LOG.debug(
            "stage=%s n=%d action=compute_bound elapsed_ms=%.2f bound=%d",
            self.name,
            n,
            elapsed_ms(bound_start),
            bound,
        )

        base_start = time.monotonic()
        factor_base = self.__build_factor_base(n, bound)
        LOG.debug(
            "stage=%s n=%d action=build_factor_base elapsed_ms=%.2f size=%d",
            self.name,
            n,
            elapsed_ms(base_start),
            len(factor_base),
        )
        if len(factor_base) < MIN_RELATIONS:
            return None

        target = len(factor_base) + 5
        rel_start = time.monotonic()
        relations = self.__find_smooth_relations(n, factor_base, target)
        LOG.debug(
            "stage=%s n=%d action=find_relations elapsed_ms=%.2f count=%d",
            self.name,
            n,
            elapsed_ms(rel_start),
            len(relations),
        )
        if len(relations) < len(factor_base):
            return None

        dep_start = time.monotonic()
        dependency = find_dependency(relations, len(factor_base))
        LOG.debug(
            "stage=%s n=%d action=find_dependency elapsed_ms=%.2f",
            self.name,
            n,
            elapsed_ms(dep_start),
        )
        if dependency is None:
            return None

        extract_start = time.monotonic()
        factor = extract_factor(n, relations, dependency, factor_base)
        LOG.debug(
            "stage=%s n=%d action=extract_factor elapsed_ms=%.2f",
            self.name,
            n,
            elapsed_ms(extract_start),
        )
        return factor

    def __compute_smoothness_bound(self, n: int) -> int:
        log_n = math.log(n)
        log_log_n = math.log(log_n)
        bound = int(math.exp(math.sqrt(log_n * log_log_n) / 2))
        bound = max(bound, 1000)
        return min(bound, 100_000)

    def __build_factor_base(self, n: int, bound: int) -> list[int]:
        base: list[int] = [-1]
        limit = min(bound, MAX_SMALL_PRIME_DIVISOR)
        for candidate in range(3, limit, 2):
            if not is_prime(candidate):
                continue
            if pow(n, (candidate - 1) // 2, candidate) != 1:
                continue
            base.append(candidate)
            if len(base) >= DEFAULT_FACTOR_BASE_LIMIT:
                break
        return base

    def __find_smooth_relations(
        self,
        n: int,
        factor_base: list[int],
        target_count: int,
    ) -> list[QSRelation]:
        relations: list[QSRelation] = []
        sqrt_n = math.isqrt(n) + 1

        for multiplier in range(1, MAX_SQRT_MULTIPLIER + 1):
            center = multiplier * sqrt_n
            start = max(1, center - RELATION_SEARCH_RADIUS)
            end = center + RELATION_SEARCH_MULTIPLIER * RELATION_SEARCH_RADIUS
            for candidate in range(start, end):
                square_mod = (candidate * candidate) % n
                if square_mod == 0:
                    continue
                exponents = factor_over_base(square_mod, factor_base)
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
