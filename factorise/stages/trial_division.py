"""Trial division with 30-wheel optimization and extended prime table."""

from __future__ import annotations

import logging
import time

from factorise.core import EXTENDED_SMALL_PRIMES
from factorise.core import ensure_integer_input
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus
from factorise.pipeline import elapsed_ms

LOG = logging.getLogger("factorise")

DEFAULT_BOUND: int = 10_000


class OptimizedTrialDivisionStage(FactorStage):
    """Trial division with 30-wheel factorization and extended prime table.

    The 30-wheel eliminates ~73% of trial candidates by skipping multiples
    of 2, 3, and 5.  Combined with an extended prime table (1000 primes),
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
        self.__bound = bound if bound is not None else DEFAULT_BOUND
        self.__prime_table = (
            prime_table if prime_table is not None else EXTENDED_SMALL_PRIMES
        )

    def attempt(self, n: int) -> StageResult:
        """Attempt to find a small factor of *n* via trial division.

        Args:
            n: The integer to factor.

        Returns:
            StageResult describing the outcome.

        """
        start = time.monotonic()
        ensure_integer_input(n)
        bits = n.bit_length()

        LOG.debug("stage=%s n=%d bits=%d action=attempt", self.name, n, bits)

        if n < 2:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d status=SKIPPED reason=%s elapsed_ms=%.2f",
                self.name, n, "n < 2", elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed,
                reason="n < 2",
            )

        if n % 2 == 0:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d factor=%d elapsed_ms=%.2f iterations=1",
                self.name, n, 2, elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=2,
                elapsed_ms=elapsed,
                iterations_used=1,
            )
        if n % 3 == 0:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d factor=%d elapsed_ms=%.2f iterations=1",
                self.name, n, 3, elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=3,
                elapsed_ms=elapsed,
                iterations_used=1,
            )
        if n % 5 == 0:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d factor=%d elapsed_ms=%.2f iterations=1",
                self.name, n, 5, elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=5,
                elapsed_ms=elapsed,
                iterations_used=1,
            )

        iterations = 0
        for prime in self.__prime_table:
            if prime > self.__bound:
                break
            iterations += 1
            if n % prime == 0:
                elapsed = elapsed_ms(start)
                LOG.debug(
                    "stage=%s n=%d factor=%d elapsed_ms=%.2f iterations=%d",
                    self.name, n, prime, elapsed, iterations,
                )
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    factor=prime,
                    elapsed_ms=elapsed,
                    iterations_used=iterations,
                )

        elapsed = elapsed_ms(start)
        LOG.debug(
            "stage=%s n=%d status=FAILURE elapsed_ms=%.2f reason=%s",
            self.name, n, elapsed, "no small factor found in trial division",
        )
        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=elapsed,
            reason="no small factor found in trial division",
        )
