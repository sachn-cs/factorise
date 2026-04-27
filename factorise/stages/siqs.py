"""Self-Initializing Quadratic Sieve (SIQS) as a pipeline stage."""

from __future__ import annotations

import logging
import math
import time
from typing import Any

from factorise.core import ensure_integer_input
from factorise.core import is_prime
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus
from factorise.pipeline import elapsed_ms
from factorise.stages.qs_shared import extract_factor
from factorise.stages.qs_shared import factor_over_base
from factorise.stages.qs_shared import find_dependency

_LOG = logging.getLogger("factorise")

MAX_SIQS_BIT_LENGTH: int = 110
MAX_SMALL_PRIME_DIVISOR: int = 2000
MIN_RELATIONS: int = 10


class SIQSStage(FactorStage):
    """Self-Initializing Quadratic Sieve factorisation stage.

    SIQS is the practical choice for 60-110 digit composites in pure Python.
    Beyond that, an external GNFS implementation is required.
    """

    name = "siqs"

    def __init__(self, max_bit_length: int | None = None) -> None:
        """Initialise with a maximum bit length.

        Args:
            max_bit_length: Numbers above this bit length are skipped.

        """
        self._max_bit_length = (max_bit_length if max_bit_length is not None
                                else MAX_SIQS_BIT_LENGTH)

    def attempt(self, n: int) -> StageResult:
        """Attempt to find a factor of *n* using SIQS."""
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

        if n.bit_length() > self._max_bit_length:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed_ms(start),
                reason=(f"n ({n.bit_length()} bits) exceeds SIQS maximum "
                        f"({self._max_bit_length} bits)"),
            )

        if is_prime(n):
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed_ms(start),
                reason="n is prime",
            )

        if n % 2 == 0:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=2,
                elapsed_ms=elapsed_ms(start),
                iterations_used=1,
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
            _LOG.debug(
                "stage=%s n=%d factor=%d",
                self.name, n, factor,
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
            reason="SIQS found no factor",
        )

    def _find_factor(self, n: int) -> int | None:
        bound = self._compute_smoothness_bound(n)
        factor_base = self._build_factor_base(n, bound)
        if len(factor_base) < MIN_RELATIONS:
            return None

        target = len(factor_base) + 5
        relations = self._find_smooth_relations(n, factor_base, target)
        if len(relations) < len(factor_base):
            return None

        dependency = find_dependency(relations, len(factor_base))
        if dependency is None:
            return None

        return extract_factor(n, relations, dependency, factor_base)

    def _compute_smoothness_bound(self, n: int) -> int:
        log_n = math.log(n)
        log_log_n = math.log(log_n)
        bound = int(math.exp(math.sqrt(log_n * log_log_n) / 2))
        bound = max(bound, 1000)
        return min(bound, 100_000)

    def _build_factor_base(self, n: int, bound: int) -> list[int]:
        base: list[int] = [-1]
        limit = min(bound, MAX_SMALL_PRIME_DIVISOR)
        for candidate in range(3, limit, 2):
            if not is_prime(candidate):
                continue
            if pow(n, (candidate - 1) // 2, candidate) != 1:
                continue
            base.append(candidate)
            if len(base) >= 100:
                break
        return base

    def _find_smooth_relations(
        self,
        n: int,
        factor_base: list[int],
        target_count: int,
    ) -> list[dict[str, Any]]:
        relations: list[dict[str, Any]] = []
        sqrt_n = math.isqrt(n) + 1

        for multiplier in range(1, 4):
            center = multiplier * sqrt_n
            start = max(1, center - 200)
            end = center + 4 * 200
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
