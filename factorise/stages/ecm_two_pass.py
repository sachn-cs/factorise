"""Two-pass ECM (Elliptic Curve Method) as a pipeline stage."""

from __future__ import annotations

import logging
import time

from factorise.core import ensure_integer_input
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus
from factorise.pipeline import elapsed_ms
from factorise.stages.ecm_shared import EllipticCurveOperations
from factorise.stages.ecm_shared import generate_primes_up_to

_LOG = logging.getLogger("factorise")


class TwoPassECMStage(EllipticCurveOperations, FactorStage):
    """Two-pass ECM: stage 1 (standard) + stage 2 (higher bound).

    Stage 1 uses a smoothness bound B1 and curves1 curves to find factors
    where p-1 has only small prime factors. Stage 2 increases the bound to
    B2 > B1 with fresh curves, extending the reach to medium-sized factors.
    """

    name = "ecm_two_pass"

    def __init__(
        self,
        first_pass_curves: int = 20,
        first_pass_bound: int = 10_000,
        second_pass_curves: int = 30,
        second_pass_bound: int = 50_000,
    ) -> None:
        """Initialise with two-pass curve and bound parameters.

        Args:
            first_pass_curves: Number of curves in stage 1.
            first_pass_bound: Smoothness bound for stage 1.
            second_pass_curves: Number of curves in stage 2.
            second_pass_bound: Smoothness bound for stage 2.

        """
        self._first_pass_curves = first_pass_curves
        self._first_pass_bound = first_pass_bound
        self._second_pass_curves = second_pass_curves
        self._second_pass_bound = second_pass_bound

    def attempt(self, n: int) -> StageResult:
        """Attempt to find a factor of *n* using two-pass ECM."""
        start = time.monotonic()
        ensure_integer_input(n)

        if n % 2 == 0:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=2,
                elapsed_ms=elapsed_ms(start),
                iterations_used=1,
            )

        first_pass_primes = generate_primes_up_to(self._first_pass_bound)
        for curve_num in range(self._first_pass_curves):
            factor = self.run_curve(
                n,
                curve_num,
                first_pass_primes,
                self._first_pass_bound,
            )
            if factor is not None and 1 < factor < n:
                _LOG.debug(
                    "stage=%s n=%d factor=%d curve=%d",
                    self.name, n, factor, curve_num + 1,
                )
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    factor=factor,
                    elapsed_ms=elapsed_ms(start),
                    iterations_used=curve_num + 1,
                )

        second_pass_primes = generate_primes_up_to(self._second_pass_bound)
        for curve_num in range(self._second_pass_curves):
            factor = self.run_curve(
                n,
                self._first_pass_curves + curve_num,
                second_pass_primes,
                self._second_pass_bound,
            )
            if factor is not None and 1 < factor < n:
                _LOG.debug(
                    "stage=%s n=%d factor=%d curve=%d stage=2",
                    self.name, n, factor,
                    self._first_pass_curves + curve_num + 1,
                )
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    factor=factor,
                    elapsed_ms=elapsed_ms(start),
                    iterations_used=self._first_pass_curves + curve_num + 1,
                )

        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=elapsed_ms(start),
            reason=
            (f"no factor found after {self._first_pass_curves + self._second_pass_curves} curves"
            ),
        )
