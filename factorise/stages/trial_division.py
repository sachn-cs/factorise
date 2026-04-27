"""Trial division with 30-wheel optimization and extended prime table."""

from __future__ import annotations

import logging
import time

from factorise.core import EXTENDED_SMALL_PRIMES
from factorise.core import ensure_integer_input
from factorise.pipeline import elapsed_ms
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus

_LOG = logging.getLogger("factorise")


class OptimizedTrialDivisionStage(FactorStage):
    """Trial division with 30-wheel factorization and extended prime table.

    The 30-wheel eliminates ~73% of trial candidates by skipping multiples
    of 2, 3, and 5. Combined with an extended prime table (1000 primes),
    this finds small factors very quickly before heavier algorithms run.
    """

    name = "trial_division"

    def __init__(
        self,
        bound: int | None = None,
        prime_table: tuple[int, ...] | None = None,
    ) -> None:
        """Initialise with a trial division bound and prime table.

        Args:
            bound: Upper limit for trial division.
            prime_table: Tuple of small primes to test.

        """
        self._bound = bound if bound is not None else 10_000
        self._prime_table = (prime_table if prime_table is not None else
                             EXTENDED_SMALL_PRIMES)

    def attempt(self, n: int) -> StageResult:
        """Attempt to find a small factor of *n* via trial division."""
        start = time.monotonic()
        ensure_integer_input(n)

        if n < 2:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed_ms(start),
                reason="n < 2",
            )

        if n % 2 == 0:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=2,
                elapsed_ms=elapsed_ms(start),
                iterations_used=1,
            )
        if n % 3 == 0:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=3,
                elapsed_ms=elapsed_ms(start),
                iterations_used=1,
            )
        if n % 5 == 0:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=5,
                elapsed_ms=elapsed_ms(start),
                iterations_used=1,
            )

        for prime in self._prime_table:
            if prime > self._bound:
                break
            if n % prime == 0:
                _LOG.debug(
                    "stage=%s n=%d factor=%d",
                    self.name, n, prime,
                )
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    factor=prime,
                    elapsed_ms=elapsed_ms(start),
                    iterations_used=1,
                )

        _LOG.debug(
            "stage=%s n=%d status=FAILURE reason=no_small_factor",
            self.name, n,
        )
        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=elapsed_ms(start),
            reason="no small factor found in trial division",
        )
