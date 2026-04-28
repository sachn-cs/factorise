"""Elliptic Curve Method (ECM) as a pipeline stage."""

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

DEFAULT_CURVES: int = 20
DEFAULT_BOUND: int = 10_000
PRIME_BASE_CUTOFF: int = 1000


class ECMStage(EllipticCurveOperations, FactorStage):
    """Elliptic Curve Method factorisation stage.

    ECM is most effective for finding factors in the 10–40 digit range.  It
    works by running random elliptic curve arithmetic modulo *n* and detecting
    when a GCD reveals a non-trivial factor.

    Args:
        curves: Number of distinct curves to try before giving up.  More curves
            increase the chance of finding a factor at higher computational cost.
        bound: Smoothness bound.  Each curve's arithmetic is bounded by this
            limit.  Larger bounds improve factor discovery at the cost of speed.

    Example:
        >>> stage = ECMStage(curves=50, bound=20_000)
        >>> result = stage.attempt(455839)
        >>> if result.factor:
        ...     print(f"Found factor: {result.factor}")

    """

    name = "ecm"

    def __init__(
        self,
        curves: int | None = None,
        bound: int | None = None,
    ) -> None:
        """Initialise the ECM stage with curve count and smoothness bound."""
        self.__curves = curves if curves is not None else DEFAULT_CURVES
        self.__bound = bound if bound is not None else DEFAULT_BOUND

    @property
    def curves(self) -> int:
        """Return the number of curves configured for this stage."""
        return self.__curves

    def attempt(self, n: int) -> StageResult:
        """Attempt to find a factor of *n* using ECM.

        Args:
            n: The integer to factor.

        Returns:
            StageResult with status SUCCESS and the factor if found, or
            FAILURE if no factor was discovered after all curves.

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

        prime_start = time.monotonic()
        prime_base = generate_primes_up_to(min(self.__bound,
                                               PRIME_BASE_CUTOFF),)
        LOG.debug(
            "stage=%s n=%d action=build_prime_base elapsed_ms=%.2f primes=%d",
            self.name,
            n,
            elapsed_ms(prime_start),
            len(prime_base),
        )

        for curve_num in range(self.__curves):
            curve_start = time.monotonic()
            factor = self.run_curve(n, curve_num, prime_base)
            if factor is not None and factor > 1:
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
                "stage=%s n=%d action=run_curve curve=%d elapsed_ms=%.2f",
                self.name,
                n,
                curve_num + 1,
                elapsed_ms(curve_start),
            )

        elapsed = elapsed_ms(start)
        LOG.debug(
            "stage=%s n=%d status=FAILURE elapsed_ms=%.2f reason=%s",
            self.name,
            n,
            elapsed,
            f"no factor found after {self.__curves} curves",
        )
        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=elapsed,
            reason=f"no factor found after {self.__curves} curves",
        )
