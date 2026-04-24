"""Elliptic Curve Method (ECM) as a pipeline stage.

ECM is a modern general-purpose factorisation algorithm particularly effective
at finding medium-sized prime factors (typically 10-40 digits). It works by
performing operations on a random elliptic curve modulo n; when a computation
yields a zero divisor (detected as gcd(denominator, n) > 1), a non-trivial
factor is found.

The implementation uses the Montgomery ladder for efficient point
multiplication and handles the projective coordinate setting correctly.

References:
- Brent, R. P. (1990). "Factorisation of integers using the elliptic curve method".
- Montgomery, P. L. (1987). "Speeding the Pollard and elliptic curve methods".
"""

from __future__ import annotations

import time

from loguru import logger

from factorise.core import FactoriserConfig
from factorise.core import ensure_integer_input
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus
from factorise.stages._ecm_shared import EllipticCurveOperations
from factorise.stages._ecm_shared import generate_primes_up_to

logger.disable("factorise")


class ECMStage(EllipticCurveOperations, FactorStage):
    """Elliptic Curve Method factorisation stage.

    ECM is most effective for finding factors in the 10-40 digit range. Each
    "curve" runs with a smoothness bound B; the probability of success per
    curve depends on the size of the smallest factor relative to B.

    This implementation uses stage 1 of the elliptic curve method: compute
    k*P for k = product of small primes up to B, then detect when an
    intermediate gcd reveals a factor.
    """

    name = "ecm"

    def __init__(
        self,
        curves: int | None = None,
        bound: int | None = None,
    ) -> None:
        self.__curves = curves if curves is not None else 20
        self.__bound = bound if bound is not None else 10_000

    @property
    def curves(self) -> int:
        """Return the number of curves configured for this stage."""
        return self.__curves

    def attempt(self, n: int, *, config: FactoriserConfig) -> StageResult:
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

        # Quick check for very small odd factors (should be handled by trial division
        # but we check anyway as a safety net).
        for p in (3, 5, 7, 11, 13, 17, 19, 23, 29):
            if n % p == 0:
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    factor=p,
                    elapsed_ms=(time.monotonic() - start) * 1000,
                    iterations_used=1,
                )

        primes = generate_primes_up_to(min(self.__bound, 1000))

        for curve_num in range(self.__curves):
            factor = self.run_curve(n, curve_num, primes, self.__bound)
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
            reason=f"no factor found after {self.__curves} curves",
        )
