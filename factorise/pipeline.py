"""Multi-stage integer factorisation pipeline.

The pipeline attempts factorisation using progressively more powerful algorithms:

1. Trial Division — trivial division by small primes.
2. Pollard p-1 — finds factors where p-1 is smooth.
3. Pollard's Rho (Brent) — general-purpose.
4. ECM — modern, general-purpose.
5. Quadratic Sieve — fast for medium-to-large inputs.
6. GNFS — external tool adapter for very large inputs.

Each stage exposes a common interface (FactorStage) and emits a structured result
(StageResult). Stages are composable: the pipeline feeds non-trivial composite
parts back into earlier stages until everything is prime.
"""

from __future__ import annotations

__all__ = [
    "FactorStage",
    "FactorisationPipeline",
    "PollardPMinusOneStage",
    "StageFactory",
    "StageResult",
    "StageStatus",
    "yield_prime_factors_via_pipeline",
]

import dataclasses
import enum
import importlib
import math
import time
from abc import ABC
from abc import abstractmethod
from collections.abc import Generator

from loguru import logger

from factorise.config import FactoriserConfig
from factorise.config import PipelineConfig
from factorise.core import EXTENDED_SMALL_PRIMES
from factorise.core import FactorisationError
from factorise.core import ensure_integer_input
from factorise.core import find_nontrivial_factor_pollard_brent
from factorise.core import is_prime

# ---------------------------------------------------------------------------
# Stage result types
# ---------------------------------------------------------------------------


class StageStatus(enum.Enum):
    """Outcome of a factorisation stage attempt."""

    SKIPPED = "skipped"
    PARTIAL = "partial"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclasses.dataclass(frozen=True)
class StageResult:
    """Result of a single factorisation stage.

    Attributes:
        stage_name: Canonical name of the stage.
        status: One of SKIPPED | PARTIAL | SUCCESS | FAILURE.
        factor: A non-trivial factor found, or None if the stage failed/skipped.
        elapsed_ms: Wall-clock milliseconds spent in the stage.
        reason: Human-readable reason for SKIPPED or FAILURE, or None.
        iterations_used: Algorithm-specific iteration counter (0 if skipped).

    """

    stage_name: str
    status: StageStatus
    factor: int | None
    elapsed_ms: float
    reason: str | None = None
    iterations_used: int = 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StageResult):
            return NotImplemented
        return (self.stage_name == other.stage_name and
                self.status == other.status and self.factor == other.factor and
                self.reason == other.reason)

    def __hash__(self) -> int:
        return hash((self.stage_name, self.status, self.factor, self.reason))


# ---------------------------------------------------------------------------
# Stage interface
# ---------------------------------------------------------------------------


class FactorStage(ABC):
    """Abstract interface for a single factorisation stage.

    All stages share the same call signature so they can be composed in a
    pipeline and replaced independently. Stages are stateless — they receive
    configuration via their constructors but hold no mutable state.
    """

    name: str

    @abstractmethod
    def attempt(self, n: int) -> StageResult:
        """Attempt to find a non-trivial factor of *n*.

        Args:
            n: An odd composite integer >= 3. The caller guarantees n is not prime.

        Returns:
            StageResult describing the outcome.

        """
        ...


def elapsed_ms(start: float) -> float:
    """Return elapsed milliseconds since *start* (from time.monotonic())."""
    return (time.monotonic() - start) * 1000


# ---------------------------------------------------------------------------
# Pollard p-1 stage
# ---------------------------------------------------------------------------


class PollardPMinusOneStage(FactorStage):
    """Pollard's p-1 method.

    Finds a factor p when p-1 is smooth (has only small prime factors).
    It is particularly effective as an intermediate stage between trial division
    and Pollard's Rho because it can find larger smooth factors that trial
    division misses.
    """

    name = "pollard_pminus1"

    def __init__(self, bound: int | None = None) -> None:
        """Initialise with a smoothness bound.

        Args:
            bound: The smoothness limit for the p-1 method.

        """
        self._bound = bound if bound is not None else 10**6

    def attempt(self, n: int) -> StageResult:
        """Attempt to find a factor of *n* using Pollard p-1."""
        start = time.monotonic()
        ensure_integer_input(n)

        if n < 3:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed_ms(start),
                reason="n < 3",
            )

        for base in (2, 3, 5, 7, 11):
            a = pow(base, self._bound, n)
            g = math.gcd(a - 1, n)
            if 1 < g < n:
                logger.debug(
                    "stage={stage} n={n} factor={factor} base={base}",
                    stage=self.name,
                    n=n,
                    factor=g,
                    base=base,
                )
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    factor=g,
                    elapsed_ms=elapsed_ms(start),
                    iterations_used=1,
                )

        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=elapsed_ms(start),
            reason=f"no factor found with bound={self._bound}",
        )


# ---------------------------------------------------------------------------
# Stage factory
# ---------------------------------------------------------------------------


class StageFactory:
    """Explicit factory that constructs stage instances from a PipelineConfig.

    Replaces the previous global StageRegistry metaclass. Each pipeline owns
    its own factory, making stage availability explicit and testable.
    """

    def __init__(self, config: PipelineConfig) -> None:
        """Initialise the factory from a pipeline config.

        Args:
            config: The pipeline configuration defining enabled stages.

        """
        self._config = config
        self._stages: dict[str, FactorStage] = {}
        self._build_stages()

    def _build_stages(self) -> None:
        """Instantiate stage handlers based on the configured stage order."""
        for name in self._config.enabled_stages():
            if name == "trial_division":
                mod = importlib.import_module("factorise.stages.trial_division")
                cls = mod.OptimizedTrialDivisionStage
                self._stages[name] = cls(
                    bound=self._config.trial_division_bound,
                    prime_table=EXTENDED_SMALL_PRIMES,
                )
            elif name == "pollard_pminus1":
                self._stages[name] = PollardPMinusOneStage(
                    bound=self._config.pm1_bound,)
            elif name == "pollard_rho":
                mod = importlib.import_module("factorise.stages.pollard_rho")
                cls = mod.PollardRhoStage
                self._stages[name] = cls(
                    max_retries=self._config.max_retries,
                    max_iterations=self._config.max_iterations,
                    batch_size=self._config.batch_size,
                    seed=self._config.seed,
                )
            elif name == "ecm":
                mod = importlib.import_module("factorise.stages.ecm")
                cls = mod.ECMStage
                self._stages[name] = cls(
                    curves=self._config.ecm_curves,
                    bound=self._config.bound_medium,
                )
            elif name == "quadratic_sieve":
                mod = importlib.import_module(
                    "factorise.stages.quadratic_sieve")
                cls = mod.QuadraticSieveStage
                self._stages[name] = cls()
            elif name == "gnfs":
                mod = importlib.import_module("factorise.stages.gnfs")
                cls = mod.GNFSStage
                self._stages[name] = cls(
                    binary=self._config.gnfs_binary,
                    timeout_seconds=self._config.gnfs_timeout,
                )

    def get(self, name: str) -> FactorStage | None:
        """Look up a stage instance by canonical name."""
        return self._stages.get(name)

    def names(self) -> list[str]:
        """Return all registered stage names."""
        return list(self._stages.keys())

    def stage_map(self) -> dict[str, FactorStage]:
        """Return a shallow copy of the internal stage mapping."""
        return dict(self._stages)


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------


class FactorisationPipeline:
    """Multi-stage factorisation pipeline.

    The pipeline is constructed with a PipelineConfig that specifies which
    stages to run and in what order. It implements the FactorStage interface
    so that it can itself be used as a stage in outer pipelines.

    The pipeline handles the overall orchestration: for each composite part it
    has not yet factored, it runs the enabled stages in order until a stage
    returns a non-trivial factor.
    """

    def __init__(self, config: PipelineConfig | None = None) -> None:
        """Initialise the pipeline with an optional configuration.

        Args:
            config: Pipeline configuration. Uses defaults if omitted.

        """
        self._config = config if config is not None else PipelineConfig()
        self._factory = StageFactory(self._config)

    @property
    def config(self) -> PipelineConfig:
        """Return the pipeline configuration."""
        return self._config

    @property
    def stages(self) -> dict[str, FactorStage]:
        """Return a shallow copy of the internal stage mapping."""
        return self._factory.stage_map()

    def attempt(self, n: int) -> StageResult:
        """Attempt to fully factor *n* using the configured stage pipeline.

        Runs stages in order until the input is fully factored into primes. If
        all stages fail, returns a FAILURE result.

        Args:
            n: An odd composite integer >= 3.

        Returns:
            StageResult where status is SUCCESS (fully factored) or FAILURE.
            On SUCCESS, the factor field contains a non-trivial factor;
            callers must use it to split the number and recurse.

        """
        start = time.monotonic()

        if n < 2:
            return StageResult(
                stage_name="pipeline",
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed_ms(start),
                reason="n < 2",
            )

        if is_prime(n):
            return StageResult(
                stage_name="pipeline",
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed_ms(start),
                reason="n is prime",
            )

        failures: list[str] = []
        for stage_name in self._config.enabled_stages():
            stage = self._factory.get(stage_name)
            if stage is None:
                continue

            result = stage.attempt(n)
            logger.debug(
                "stage={stage} n={n} status={status} factor={factor} "
                "elapsed_ms={elapsed_ms:.2f}",
                stage=stage_name,
                n=n,
                status=result.status.value,
                factor=result.factor,
                elapsed_ms=result.elapsed_ms,
            )

            if (result.status is StageStatus.SUCCESS and
                    result.factor is not None):
                return StageResult(
                    stage_name="pipeline",
                    status=StageStatus.SUCCESS,
                    factor=result.factor,
                    elapsed_ms=elapsed_ms(start),
                    iterations_used=result.iterations_used,
                )

            if result.status is not StageStatus.SKIPPED:
                failures.append(
                    f"{stage_name}({result.status.value}): "
                    f"{result.reason or 'unknown'}",)

        return StageResult(
            stage_name="pipeline",
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=elapsed_ms(start),
            reason="; ".join(failures) if failures else "all stages failed",
        )


# ---------------------------------------------------------------------------
# Pipeline-based recursive factorisation
# ---------------------------------------------------------------------------


def yield_prime_factors_via_pipeline(
    n: int,
    config: FactoriserConfig,
) -> Generator[int, None, None]:
    """Yield prime factors of n using the multi-stage pipeline.

    Args:
        n: The integer to factorise.
        config: Factorisation configuration (retries, iterations, seed).

    Yields:
        Prime factors of n, possibly repeated.

    """
    pipeline_config = PipelineConfig(
        max_iterations=config.max_iterations,
        max_retries=config.max_retries,
        batch_size=config.batch_size,
        seed=config.seed,
    )
    pipeline = FactorisationPipeline(pipeline_config)

    stack: list[int] = [n]
    while stack:
        current = stack.pop()
        if current < 2:
            continue
        if is_prime(current):
            yield current
            continue

        result = pipeline.attempt(current)
        if result.status is StageStatus.SUCCESS and result.factor is not None:
            d = result.factor
            logger.debug("pipeline split n={n} d={d}", n=current, d=d)
            stack.append(d)
            stack.append(current // d)
        elif result.status is StageStatus.FAILURE:
            logger.warning(
                "pipeline failed for n={n}, falling back to pollard_brent",
                n=current,
            )
            try:
                d = find_nontrivial_factor_pollard_brent(current, config)
                stack.append(d)
                stack.append(current // d)
            except FactorisationError as exc:
                raise FactorisationError(
                    f"All stages failed for n={current}; "
                    "input may be prime or require GNFS",) from exc
        else:
            raise FactorisationError(
                f"Pipeline returned unexpected status {result.status} "
                f"for composite n={current}",)
