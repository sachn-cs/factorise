"""Pollard's Rho (Brent variant) as a pipeline stage."""

from __future__ import annotations

import time

from loguru import logger

from factorise.core import FactorisationError
from factorise.core import FactoriserConfig
from factorise.core import ensure_integer_input
from factorise.core import find_nontrivial_factor_pollard_brent
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus

logger.disable("factorise")


class PollardRhoStage(FactorStage):
    """Pollard's Rho (Brent variant) factorisation stage.

    This stage wraps the existing pollard_brent implementation from factorise.core
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
        self.__max_retries = max_retries
        self.__max_iterations = max_iterations
        self.__batch_size = batch_size
        self.__seed = seed

    def attempt(self, n: int, *, config: FactoriserConfig) -> StageResult:
        start = time.monotonic()
        ensure_integer_input(n)

        cfg = FactoriserConfig(
            batch_size=self.__batch_size,
            max_iterations=self.__max_iterations,
            max_retries=self.__max_retries,
            seed=self.__seed,
        )

        try:
            factor = find_nontrivial_factor_pollard_brent(n, cfg)
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
                iterations_used=self.__max_retries,
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
