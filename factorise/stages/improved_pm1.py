"""Improved Pollard p-1 with progressive bounds and multiple bases."""

from __future__ import annotations

import logging
import math
import time

from factorise.core import ensure_integer_input
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus
from factorise.pipeline import elapsed_ms

LOG = logging.getLogger("factorise")

DEFAULT_BOUNDS: tuple[int, ...] = (10**6, 10**7, 10**8, 10**9)
DEFAULT_BASES: tuple[int, ...] = (2, 3, 5, 7, 11)


class ImprovedPollardPMinusOneStage(FactorStage):
    """Pollard p-1 with progressive smoothness bounds and multiple bases.

    Finds a factor *p* when ``p-1`` is smooth (all prime factors <= bound B).
    Uses nested iteration over bases and increasing bounds.
    """

    name = "pollard_pminus1"

    def __init__(
        self,
        bounds: tuple[int, ...] | None = None,
        bases: tuple[int, ...] | None = None,
    ) -> None:
        """Initialise with smoothness bounds and trial bases.

        Args:
            bounds: Progressive smoothness limits.
            bases: Bases for the p-1 exponentiation.

        """
        self.__bounds = bounds if bounds is not None else DEFAULT_BOUNDS
        self.__bases = bases if bases is not None else DEFAULT_BASES

    def attempt(self, n: int) -> StageResult:
        """Attempt to find a factor of *n* using improved Pollard p-1.

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

        iterations = 0
        for bound in self.__bounds:
            for base in self.__bases:
                iterations += 1
                iteration_start = time.monotonic()
                a = pow(base, bound, n)
                g = math.gcd(a - 1, n)
                if 1 < g < n:
                    elapsed = elapsed_ms(start)
                    LOG.debug(
                        "stage=%s n=%d factor=%d bound=%d base=%d "
                        "elapsed_ms=%.2f iterations=%d",
                        self.name,
                        n,
                        g,
                        bound,
                        base,
                        elapsed,
                        iterations,
                    )
                    return StageResult(
                        stage_name=self.name,
                        status=StageStatus.SUCCESS,
                        factor=g,
                        elapsed_ms=elapsed,
                        iterations_used=iterations,
                    )
                if g == n:
                    continue
                LOG.debug(
                    "stage=%s n=%d action=iteration bound=%d base=%d "
                    "elapsed_ms=%.2f",
                    self.name,
                    n,
                    bound,
                    base,
                    elapsed_ms(iteration_start),
                )

        elapsed = elapsed_ms(start)
        LOG.debug(
            "stage=%s n=%d status=FAILURE elapsed_ms=%.2f reason=%s",
            self.name,
            n,
            elapsed,
            f"no smooth factor found with bounds up to {self.__bounds[-1]}",
        )
        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=elapsed,
            reason=
            f"no smooth factor found with bounds up to {self.__bounds[-1]}",
        )
