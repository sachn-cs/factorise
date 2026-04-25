"""Elliptic Curve Method (ECM) as a pipeline stage."""

from __future__ import annotations

import time

from loguru import logger

from factorise.core import ensure_integer_input
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus
from factorise.stages.ecm_shared import EllipticCurveOperations
from factorise.stages.ecm_shared import generate_primes_up_to

logger.disable("factorise")


class ECMStage(EllipticCurveOperations, FactorStage):
    """Elliptic Curve Method factorisation stage.

    ECM is most effective for finding factors in the 10-40 digit range.
    """

    name = "ecm"

    def __init__(
        self,
        curves: int | None = None,
        bound: int | None = None,
    ) -> None:
        """Initialise with curve count and smoothness bound.

        Args:
            curves: Number of ECM curves to attempt.
            bound: Smoothness bound for each curve.

        """
        self._curves = curves if curves is not None else 20
        self._bound = bound if bound is not None else 10_000

    @property
    def curves(self) -> int:
        """Return the number of curves configured for this stage."""
        return self._curves

    def attempt(self, n: int) -> StageResult:
        """Attempt to find a factor of *n* using ECM."""
        start = time.monotonic()
        ensure_integer_input(n)

        if n % 2 == 0:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=2,
                elapsed_ms=(time.monotonic() - start) * 1000,
                iterations_used=1,
            )

        primes = generate_primes_up_to(min(self._bound, 1000))

        for curve_num in range(self._curves):
            factor = self.run_curve(n, curve_num, primes, self._bound)
            if factor is not None and factor > 1:
                logger.debug(
                    "stage={stage} n={n} factor={factor} curves={curves}",
                    stage=self.name,
                    n=n,
                    factor=factor,
                    curves=curve_num + 1,
                )
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    factor=factor,
                    elapsed_ms=(time.monotonic() - start) * 1000,
                    iterations_used=curve_num + 1,
                )

        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=(time.monotonic() - start) * 1000,
            reason=f"no factor found after {self._curves} curves",
        )
