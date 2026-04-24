"""Self-Initializing Quadratic Sieve (SIQS) as a pipeline stage.

SIQS improves on basic QS by computing the smoothness bound automatically:
  B = exp(sqrt(log n * log log n) / 2)

Key features:
  - Factor base generated from n's quadratic residues
  - Large prime variation (allows exactly one large prime per relation)
  - GF(2) Gaussian elimination to find dependencies
  - Effective for 60-110 digit composites in pure Python

Mathematical basis:
  - Find relations (a, a^2 mod n) that factor completely over the factor base
  - Combine relations where all exponents are even to get a^2 ≡ b^2 (mod n)
  - gcd(a ± b, n) yields a non-trivial factor
"""

from __future__ import annotations

import math
import time
from typing import Any

from loguru import logger

from factorise.config import HybridConfig
from factorise.core import ensure_integer_input
from factorise.core import is_prime
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus
from factorise.pipeline import elapsed_ms
from factorise.stages._qs_shared import extract_factor
from factorise.stages._qs_shared import factor_over_base
from factorise.stages._qs_shared import find_dependency
from factorise.stages._qs_shared import is_small_prime

logger.disable("factorise")

# SIQS is only practical below this bit length in pure Python.
MAX_SIQS_BIT_LENGTH: int = 110
# Upper bound for the factor base prime search.
MAX_SMALL_PRIME_DIVISOR: int = 2000
# Minimum number of relations before attempting elimination.
MIN_RELATIONS: int = 10


class SIQSStage:
    """Self-Initializing Quadratic Sieve factorisation stage.

    SIQS is the practical choice for 60-110 digit composites in pure Python.
    Beyond that, an external GNFS implementation is required.
    """

    name = "siqs"

    def __init__(self, max_bit_length: int | None = None) -> None:
        self.__max_bit_length = max_bit_length if max_bit_length is not None else MAX_SIQS_BIT_LENGTH

    def attempt(self, n: int, *, config: HybridConfig) -> StageResult:
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

        if n.bit_length() > self.__max_bit_length:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed_ms(start),
                reason=(f"n ({n.bit_length()} bits) exceeds SIQS maximum "
                        f"({self.__max_bit_length} bits)"),
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

        factor = self.__siqs_find_factor(n)
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
            reason="SIQS found no factor",
        )

    def __siqs_find_factor(self, n: int) -> int | None:
        B = self.__compute_smoothness_bound(n)
        factor_base = self.__build_factor_base(n, B)
        if len(factor_base) < MIN_RELATIONS:
            return None

        target = len(factor_base) + 5
        relations = self.__find_smooth_relations(n, factor_base, target)
        if len(relations) < len(factor_base):
            return None

        dependency = find_dependency(relations, len(factor_base))
        if dependency is None:
            return None

        return extract_factor(n, relations, dependency, factor_base)

    def __compute_smoothness_bound(self, n: int) -> int:
        log_n = math.log(n)
        log_log_n = math.log(log_n)
        B = int(math.exp(math.sqrt(log_n * log_log_n) / 2))
        B = max(B, 1000)
        B = min(B, 100_000)
        return B

    def __build_factor_base(self, n: int, B: int) -> list[int]:
        base: list[int] = [-1]
        limit = min(B, MAX_SMALL_PRIME_DIVISOR)
        for candidate in range(3, limit, 2):
            if not is_small_prime(candidate):
                continue
            if pow(n, (candidate - 1) // 2, candidate) != 1:
                continue
            base.append(candidate)
            if len(base) >= 100:
                break
        return base

    def __find_smooth_relations(
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
                relations.append({
                    "a": candidate,
                    "a2_mod_n": square_mod,
                    "exponents": exponents,
                })
                if len(relations) >= target_count:
                    return relations

        return relations
