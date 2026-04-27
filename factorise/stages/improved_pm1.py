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

_LOG = logging.getLogger("factorise")


class ImprovedPollardPMinusOneStage(FactorStage):
    """Pollard p-1 with progressive smoothness bounds and multiple bases.

    Finds a factor p when p-1 is smooth (all prime factors <= bound B).
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
        self._bounds = (bounds if bounds is not None else
                        (10**6, 10**7, 10**8, 10**9))
        self._bases = bases if bases is not None else (2, 3, 5, 7, 11)

    def attempt(self, n: int) -> StageResult:
        """Attempt to find a factor of *n* using improved Pollard p-1."""
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

        for bound in self._bounds:
            for base in self._bases:
                a = pow(base, bound, n)
                g = math.gcd(a - 1, n)
                if 1 < g < n:
                    _LOG.debug(
                        "stage=%s n=%d factor=%d bound=%d base=%d",
                        self.name, n, g, bound, base,
                    )
                    return StageResult(
                        stage_name=self.name,
                        status=StageStatus.SUCCESS,
                        factor=g,
                        elapsed_ms=elapsed_ms(start),
                        iterations_used=1,
                    )
                if g == n:
                    continue

        _LOG.debug(
            "stage=%s n=%d status=FAILURE reason=no_smooth_factor",
            self.name, n,
        )
        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=elapsed_ms(start),
            reason=
            f"no smooth factor found with bounds up to {self._bounds[-1]}",
        )
