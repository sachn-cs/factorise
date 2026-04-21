"""Pollard's Rho (Brent variant) as a pipeline stage."""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

from loguru import logger

from source.pipeline import FactorStage, StageResult, StageStatus

if TYPE_CHECKING:
    from source.core import FactoriserConfig

logger.disable("factorise")


class PollardRhoStage(FactorStage):
    """Pollard's Rho (Brent variant) factorisation stage.

    This stage wraps the existing pollard_brent implementation from source.core
    and exposes it via the FactorStage interface. It is the primary general-purpose
    factorisation method in the pipeline, effective for small-to-medium composites.

    The stage is skipped when the input is below the "small" threshold since
    trial division is faster for those inputs.
    """

    name = "pollard_rho"

    def __init__(
        self,
        max_retries: int = 20,
        max_iterations: int = 10_000_000,
        batch_size: int = 128,
        seed: int | None = None,
    ) -> None:
        self._max_retries = max_retries
        self._max_iterations = max_iterations
        self._batch_size = batch_size
        self._seed = seed

    def attempt(self, n: int, *, config: FactoriserConfig) -> StageResult:
        from source.core import (
            FactorisationError,
            FactoriserConfig,
            pollard_brent,
            validate_int,
        )

        start = time.monotonic()
        validate_int(n)

        cfg = FactoriserConfig(
            batch_size=self._batch_size,
            max_iterations=self._max_iterations,
            max_retries=self._max_retries,
            seed=self._seed,
        )

        try:
            factor = pollard_brent(n, cfg)
            logger.debug(
                "stage={stage} n={n} factor={factor}",
                stage=self.name,
                n=n,
                factor=factor,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=factor,
                elapsed_ms=(time.monotonic() - start) * 1000,
                iterations_used=self._max_retries,
            )
        except FactorisationError as exc:
            logger.debug(
                "stage={stage} n={n} status=FAILURE reason={reason}",
                stage=self.name,
                n=n,
                reason=str(exc),
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILURE,
                factor=None,
                elapsed_ms=(time.monotonic() - start) * 1000,
                reason=str(exc),
            )
