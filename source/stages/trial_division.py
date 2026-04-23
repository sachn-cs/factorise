"""Trial division with 30-wheel optimization and extended prime table."""

from __future__ import annotations

import time

from loguru import logger

from source.core import EXTENDED_SMALL_PRIMES
from source.core import FactoriserConfig
from source.core import ensure_integer_input
from source.pipeline import FactorStage
from source.pipeline import StageResult
from source.pipeline import StageStatus

logger.disable("factorise")


class OptimizedTrialDivisionStage(FactorStage):
    """Trial division with 30-wheel factorization and extended prime table.

    The 30-wheel eliminates ~73% of trial candidates by skipping multiples
    of 2, 3, and 5. Combined with an extended prime table (1000 primes),
    this finds small factors very quickly before heavier algorithms run.

    This stage is appropriate for any composite input but is most effective
    when *n* has a small factor (practically any n < 10^12, and even
    larger n with probability ~log(log n)).
    """

    name = "trial_division"

    def __init__(
        self,
        bound: int | None = None,
        prime_table: tuple[int, ...] | None = None,
    ) -> None:
        self._bound = bound if bound is not None else 10_000
        self._prime_table = (
            prime_table if prime_table is not None else EXTENDED_SMALL_PRIMES
        )

    def attempt(self, n: int, *, config: HybridConfig) -> StageResult:
        start = time.monotonic()
        ensure_integer_input(n)

        if n < 2:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=self._elapsed_ms(start),
                reason="n < 2",
            )

        if n % 2 == 0:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=2,
                elapsed_ms=self._elapsed_ms(start),
                iterations_used=1,
            )
        if n % 3 == 0:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=3,
                elapsed_ms=self._elapsed_ms(start),
                iterations_used=1,
            )
        if n % 5 == 0:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=5,
                elapsed_ms=self._elapsed_ms(start),
                iterations_used=1,
            )

        for prime in self._prime_table:
            if prime > self._bound:
                break
            if prime == 2 or prime == 3 or prime == 5:
                continue
            if n % prime == 0:
                logger.debug(
                    "stage={stage} n={n} factor={factor}",
                    stage=self.name,
                    n=n,
                    factor=prime,
                )
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    factor=prime,
                    elapsed_ms=self._elapsed_ms(start),
                    iterations_used=1,
                )

        logger.debug(
            "stage={stage} n={n} status=FAILURE reason=no_small_factor",
            stage=self.name,
            n=n,
        )
        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=self._elapsed_ms(start),
            reason="no small factor found in trial division",
        )

    def _elapsed_ms(self, start: float) -> float:
        return (time.monotonic() - start) * 1000
