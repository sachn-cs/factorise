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

LOG = logging.getLogger("factorise")


class TwoPassECMStage(EllipticCurveOperations, FactorStage):
    """Two-pass ECM: stage 1 (standard) + stage 2 (higher bound).

    Stage 1 uses a smoothness bound B1 and *curves1* curves to find factors
    where ``p-1`` has only small prime factors.  Stage 2 increases the bound
    to B2 > B1 with fresh curves, extending the reach to medium-sized factors.
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
        self.__first_pass_curves = first_pass_curves
        self.__first_pass_bound = first_pass_bound
        self.__second_pass_curves = second_pass_curves
        self.__second_pass_bound = second_pass_bound

    def attempt(self, n: int) -> StageResult:
        """Attempt to find a factor of *n* using two-pass ECM.

        Args:
            n: The integer to factor.

        Returns:
            StageResult describing the outcome.

        """
        start = time.monotonic()
        ensure_integer_input(n)
        bits = n.bit_length()

        LOG.debug("stage=%s n=%d bits=%d action=attempt", self.name, n, bits)

        if n % 2 == 0:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d factor=%d elapsed_ms=%.2f iterations=1",
                self.name,
                n,
                2,
                elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=2,
                elapsed_ms=elapsed,
                iterations_used=1,
            )

        # Stage 1
        pass1_start = time.monotonic()
        first_pass_primes = generate_primes_up_to(self.__first_pass_bound)
        LOG.debug(
            "stage=%s n=%d action=stage1_primes elapsed_ms=%.2f",
            self.name,
            n,
            elapsed_ms(pass1_start),
        )

        for curve_num in range(self.__first_pass_curves):
            factor = self.run_curve(n, curve_num, first_pass_primes)
            if factor is not None and 1 < factor < n:
                elapsed = elapsed_ms(start)
                LOG.debug(
                    "stage=%s n=%d factor=%d elapsed_ms=%.2f iterations=%d",
                    self.name,
                    n,
                    factor,
                    elapsed,
                    curve_num + 1,
                )
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    factor=factor,
                    elapsed_ms=elapsed,
                    iterations_used=curve_num + 1,
                )

        LOG.debug(
            "stage=%s n=%d action=stage1_done elapsed_ms=%.2f curves=%d",
            self.name,
            n,
            elapsed_ms(pass1_start),
            self.__first_pass_curves,
        )

        # Stage 2
        pass2_start = time.monotonic()
        second_pass_primes = generate_primes_up_to(self.__second_pass_bound)
        LOG.debug(
            "stage=%s n=%d action=stage2_primes elapsed_ms=%.2f",
            self.name,
            n,
            elapsed_ms(pass2_start),
        )

        for curve_num in range(self.__second_pass_curves):
            factor = self.run_curve(
                n,
                self.__first_pass_curves + curve_num,
                second_pass_primes,
            )
            if factor is not None and 1 < factor < n:
                total_curves = self.__first_pass_curves + curve_num + 1
                elapsed = elapsed_ms(start)
                LOG.debug(
                    "stage=%s n=%d factor=%d elapsed_ms=%.2f iterations=%d",
                    self.name,
                    n,
                    factor,
                    elapsed,
                    total_curves,
                )
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    factor=factor,
                    elapsed_ms=elapsed,
                    iterations_used=total_curves,
                )

        elapsed = elapsed_ms(start)
        total_curves = self.__first_pass_curves + self.__second_pass_curves
        LOG.debug(
            "stage=%s n=%d status=FAILURE elapsed_ms=%.2f reason=%s",
            self.name,
            n,
            elapsed,
            f"no factor found after {total_curves} curves",
        )
        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=elapsed,
            reason=f"no factor found after {total_curves} curves",
        )
