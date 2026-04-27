"""Elliptic Curve Method (ECM) as a pipeline stage."""

from __future__ import annotations

import logging
import time

from factorise.core import ensure_integer_input
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus
from factorise.stages.ecm_shared import EllipticCurveOperations
from factorise.stages.ecm_shared import generate_primes_up_to

_LOG = logging.getLogger("factorise")

_DEFAULT_CURVES: int = 20
_DEFAULT_BOUND: int = 10_000
_PRIME_BASE_CUTOFF: int = 1000


class ECMStage(EllipticCurveOperations, FactorStage):
    """Elliptic Curve Method factorisation stage.

    ECM is most effective for finding factors in the 10–40 digit range. It works
    by running random elliptic curve arithmetic modulo *n* and detecting when
    a GCD reveals a non-trivial factor.

    Args:
        curves: Number of distinct curves to try before giving up. More curves
            increase the chance of finding a factor at higher computational cost.
        bound: Smoothness bound. Each curve's arithmetic is bounded by this
            limit. Larger bounds improve factor discovery at the cost of speed.

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
        self._curves = curves if curves is not None else _DEFAULT_CURVES
        self._bound = bound if bound is not None else _DEFAULT_BOUND

    @property
    def curves(self) -> int:
        """Return the number of curves configured for this stage."""
        return self._curves

    def attempt(self, n: int) -> StageResult:
        """Attempt to find a factor of *n* using ECM.

        Returns:
            StageResult with status SUCCESS and the factor if found, or
            FAILURE if no factor was discovered after all curves.
        """
        start = time.monotonic()
        ensure_integer_input(n)

        if n % 2 == 0:
            elapsed = (time.monotonic() - start) * 1000
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=2,
                elapsed_ms=elapsed,
                iterations_used=1,
            )

        prime_base = generate_primes_up_to(min(self._bound, _PRIME_BASE_CUTOFF))

        for curve_num in range(self._curves):
            factor = self.run_curve(n, curve_num, prime_base, self._bound)
            if factor is not None and factor > 1:
                elapsed = (time.monotonic() - start) * 1000
                _LOG.debug(
                    "stage=%s n=%d factor=%d curves=%d",
                    self.name, n, factor, curve_num + 1,
                )
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    factor=factor,
                    elapsed_ms=elapsed,
                    iterations_used=curve_num + 1,
                )

        elapsed = (time.monotonic() - start) * 1000
        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=elapsed,
            reason=f"no factor found after {self._curves} curves",
        )
