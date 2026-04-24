"""Two-pass ECM (Elliptic Curve Method) as a pipeline stage."""

from __future__ import annotations

import time

from loguru import logger

from factorise.core import FactoriserConfig
from factorise.core import ensure_integer_input
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus
from factorise.pipeline import elapsed_ms
from factorise.stages._ecm_shared import EllipticCurveOperations
from factorise.stages._ecm_shared import generate_primes_up_to

logger.disable("factorise")


class TwoPassECMStage(EllipticCurveOperations):
    """Two-pass ECM: stage 1 (standard) + stage 2 (higher bound).

    Stage 1 uses a smoothness bound B1 and curves1 curves to find
    factors where p-1 has only small prime factors.
    Stage 2 increases the bound to B2 > B1 with fresh curves, extending
    the reach to medium-sized factors (typically 10–40 digits).

    This is the most effective method for the 41–70 digit range in pure
    Python and significantly outperforms Rho for composites whose
    smallest factor is in that range.
    """

    name = "ecm"

    def __init__(
        self,
        first_pass_curves: int = 20,
        first_pass_bound: int = 10_000,
        second_pass_curves: int = 30,
        second_pass_bound: int = 50_000,
    ) -> None:
        self.__first_pass_curves = first_pass_curves
        self.__first_pass_bound = first_pass_bound
        self.__second_pass_curves = second_pass_curves
        self.__second_pass_bound = second_pass_bound

    def attempt(self, n: int, *, config: FactoriserConfig) -> StageResult:
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

        for p in (3, 5, 7, 11, 13, 17, 19, 23, 29):
            if n % p == 0:
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    factor=p,
                    elapsed_ms=elapsed_ms(start),
                    iterations_used=1,
                )

        first_pass_primes = generate_primes_up_to(self.__first_pass_bound)
        for curve_num in range(self.__first_pass_curves):
            factor = self.run_curve(n, curve_num, first_pass_primes,
                                    self.__first_pass_bound)
            if factor is not None and 1 < factor < n:
                logger.debug(
                    "stage={stage} n={n} factor={factor} curve={curve}",
                    stage=self.name,
                    n=n,
                    factor=factor,
                    curve=curve_num + 1,
                )
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    factor=factor,
                    elapsed_ms=elapsed_ms(start),
                    iterations_used=curve_num + 1,
                )

        second_pass_primes = generate_primes_up_to(self.__second_pass_bound)
        for curve_num in range(self.__second_pass_curves):
            factor = self.run_curve(n, self.__first_pass_curves + curve_num,
                                    second_pass_primes,
                                    self.__second_pass_bound)
            if factor is not None and 1 < factor < n:
                logger.debug(
                    "stage={stage} n={n} factor={factor} curve={curve} stage=2",
                    stage=self.name,
                    n=n,
                    factor=factor,
                    curve=self.__first_pass_curves + curve_num + 1,
                )
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    factor=factor,
                    elapsed_ms=elapsed_ms(start),
                    iterations_used=self.__first_pass_curves + curve_num + 1,
                )

        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=elapsed_ms(start),
            reason=
            (f"no factor found after {self.__first_pass_curves + self.__second_pass_curves} curves"
            ),
        )
