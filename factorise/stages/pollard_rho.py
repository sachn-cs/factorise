"""Pollard's Rho (Brent variant) as a pipeline stage."""

from __future__ import annotations

import logging
import time

from factorise.config import FactoriserConfig
from factorise.core import FactorisationError
from factorise.core import ensure_integer_input
from factorise.core import find_nontrivial_factor_pollard_brent
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus
from factorise.pipeline import elapsed_ms

LOG = logging.getLogger("factorise")

DEFAULT_MAX_RETRIES: int = 20
DEFAULT_MAX_ITERATIONS: int = 10_000_000
DEFAULT_BATCH_SIZE: int = 128


class PollardRhoStage(FactorStage):
    """Pollard's Rho (Brent variant) factorisation stage.

    This stage wraps the existing Pollard-Brent implementation from
    :mod:`factorise.core` and exposes it via the :class:`FactorStage`
    interface.  It is the primary general-purpose factorisation method in
    the pipeline.
    """

    name = "pollard_rho"

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        batch_size: int = DEFAULT_BATCH_SIZE,
        seed: int | None = None,
    ) -> None:
        """Initialise with retry and iteration limits.

        Args:
            max_retries: How many fresh seeds to try.
            max_iterations: Iteration cap per attempt.
            batch_size: GCD batch size.
            seed: Optional deterministic seed.

        """
        self.__max_retries = max_retries
        self.__max_iterations = max_iterations
        self.__batch_size = batch_size
        self.__seed = seed

    def attempt(self, n: int) -> StageResult:
        """Attempt to find a factor of *n* using Pollard's Rho.

        Args:
            n: The integer to factor.

        Returns:
            StageResult describing the outcome.

        """
        start = time.monotonic()
        ensure_integer_input(n)
        bits = n.bit_length()

        LOG.debug("stage=%s n=%d bits=%d action=attempt", self.name, n, bits)

        cfg = FactoriserConfig(
            batch_size=self.__batch_size,
            max_iterations=self.__max_iterations,
            max_retries=self.__max_retries,
            seed=self.__seed,
        )

        try:
            factor = find_nontrivial_factor_pollard_brent(n, cfg)
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d factor=%d elapsed_ms=%.2f iterations=1",
                self.name,
                n,
                factor,
                elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=factor,
                elapsed_ms=elapsed,
                iterations_used=1,
            )
        except FactorisationError as exc:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d status=FAILURE elapsed_ms=%.2f reason=%s",
                self.name,
                n,
                elapsed,
                str(exc),
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILURE,
                factor=None,
                elapsed_ms=elapsed,
                reason=str(exc),
            )
