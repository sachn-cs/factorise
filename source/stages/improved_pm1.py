"""Improved Pollard p−1 with progressive bounds and multiple bases."""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING

from loguru import logger

from source.core import ensure_integer_input
from source.pipeline import StageResult
from source.pipeline import StageStatus

if TYPE_CHECKING:
    from source.config import HybridConfig

logger.disable("factorise")


class ImprovedPollardPMinusOneStage:
    """Pollard p−1 with progressive smoothness bounds and multiple bases.

    Finds a factor p when p−1 is smooth (all prime factors <= bound B).
    Uses nested iteration over bases (2,3,5,7,11) and increasing bounds
    (10^6 -> 10^9). A factor is returned as soon as any combination yields
    a non-trivial gcd.

    This method is particularly effective as an intermediate stage between
    trial division and Pollard Rho for the 13–20 digit range.
    """

    name = "pollard_pminus1"

    def __init__(
        self,
        bounds: tuple[int, ...] | None = None,
        bases: tuple[int, ...] | None = None,
    ) -> None:
        self._bounds = bounds if bounds is not None else (10**6, 10**7, 10**8, 10**9)
        self._bases = bases if bases is not None else (2, 3, 5, 7, 11)

    def attempt(self, n: int, *, config: HybridConfig) -> StageResult:
        start = time.monotonic()
        ensure_integer_input(n)

        if n < 3:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=self._elapsed_ms(start),
                reason="n < 3",
            )

        for bound in self._bounds:
            for base in self._bases:
                a = pow(base, bound, n)
                g = math.gcd(a - 1, n)
                if 1 < g < n:
                    logger.debug(
                        "stage={stage} n={n} factor={factor} bound={bound} base={base}",
                        stage=self.name,
                        n=n,
                        factor=g,
                        bound=bound,
                        base=base,
                    )
                    return StageResult(
                        stage_name=self.name,
                        status=StageStatus.SUCCESS,
                        factor=g,
                        elapsed_ms=self._elapsed_ms(start),
                        iterations_used=1,
                    )
                if g == n:
                    continue

        logger.debug(
            "stage={stage} n={n} status=FAILURE reason=no_smooth_factor",
            stage=self.name,
            n=n,
        )
        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=self._elapsed_ms(start),
            reason=f"no smooth factor found with bounds up to {self._bounds[-1]}",
        )

    def _elapsed_ms(self, start: float) -> float:
        return (time.monotonic() - start) * 1000
