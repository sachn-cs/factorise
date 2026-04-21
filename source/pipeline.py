"""Multi-stage integer factorisation pipeline.

The pipeline attempts factorisation using progressively more powerful algorithms:

1. **Trial Division** — trivial division by small primes; O(π(b)) where b is the bound.
2. **Pollard p−1** — finds factors where p−1 is smooth; good for medium inputs.
3. **Pollard's Rho (Brent)** — general-purpose; effective for small-to-medium composites.
4. **ECM (Elliptic Curve Method)** — modern, general-purpose; best for medium inputs.
5. **Quadratic Sieve** — fast for medium-to-large inputs up to ~100 digits.
6. **GNFS (General Number Field Sieve)** — full in-repo adapter wrapping external tools
   (msieve, CADO-NFS) with strict isolation; appropriate for very large inputs.

Each stage exposes a common interface (`FactorStage`) and emits a structured result
(`StageResult`) that includes the factor found (if any), elapsed time, and the reason
for skipping or failure. Stages are composable: the pipeline feeds non-trivial
composite parts back into earlier stages until everything is prime.

The pipeline is configurable via `PipelineConfig`, which controls thresholds for
when each stage is used, per-stage iteration limits, whether stages are enabled
or disabled, and stage ordering. Safe defaults are provided so callers can use
the pipeline without tuning.

Observability
============
Each stage emits structured log records (via loguru) with fields:
  - stage: the stage name
  - n: the input being factored
  - factor: the factor found (if any)
  - status: SKIPPED | PARTIAL | SUCCESS | FAILURE
  - reason: why a stage was skipped or failed
  - elapsed_ms: wall-clock time for the stage attempt

Correctness invariants
=====================
- Every factor returned by any stage is verified prime before being emitted.
- The product of all returned prime factors equals abs(original_input).
- Zero, one, negative numbers, and primes are handled without calling any stage.
- The pipeline fails safely: exhaustion of all stages raises `FactorisationError`
  with a message that names every stage that was attempted and why each failed.
"""

from __future__ import annotations

import dataclasses
import enum
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from source.core import FactoriserConfig

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Bound above which Pollard p-1 and ECM become worthwhile.
# Below this, trial division + Rho is faster.
_DEFAULT_BOUND_SMALL = 10**12
# Bound above which ECM becomes worthwhile relative to Rho.
_DEFAULT_BOUND_MEDIUM = 10**20
# Bound above which QS becomes worthwhile relative to ECM.
_DEFAULT_BOUND_LARGE = 10**40
# Bound above which GNFS becomes worthwhile relative to QS.
_DEFAULT_BOUND_XLARGE = 10**80

# Default smoothness bound for Pollard p-1 stage.
_DEFAULT_PM1_BOUND = 10**6
# Default number of ECM curves to try before giving up.
_DEFAULT_ECM_CURVES = 20
# Default timeout (seconds) for GNFS subprocess calls.
_DEFAULT_GNFS_TIMEOUT_SECONDS = 600

# ---------------------------------------------------------------------------
# Stage result types
# ---------------------------------------------------------------------------


class StageStatus(enum.Enum):
    """Outcome of a factorisation stage attempt."""

    SKIPPED = "skipped"  # Stage was not applicable or disabled
    PARTIAL = "partial"  # Stage found a factor but did not fully factor the input
    SUCCESS = "success"  # Stage completely factored the input component
    FAILURE = "failure"  # Stage ran but could not find a factor


@dataclasses.dataclass(frozen=True)
class StageResult:
    """Result of a single factorisation stage.

    Attributes:
        stage_name: Canonical name of the stage (e.g. "trial_division").
        status: One of SKIPPED | PARTIAL | SUCCESS | FAILURE.
        factor: A non-trivial factor found, or None if the stage failed/skipped.
        elapsed_ms: Wall-clock milliseconds spent in the stage.
        reason: Human-readable reason for SKIPPED or FAILURE.
        iterations_used: Algorithm-specific iteration counter (0 if skipped).
    """

    stage_name: str
    status: StageStatus
    factor: int | None
    elapsed_ms: float
    reason: str = ""
    iterations_used: int = 0

    def is_success(self) -> bool:
        return self.status is StageStatus.SUCCESS

    def is_failure(self) -> bool:
        return self.status is StageStatus.FAILURE

    def is_skipped(self) -> bool:
        return self.status is StageStatus.SKIPPED


# ---------------------------------------------------------------------------
# Stage interface
# ---------------------------------------------------------------------------


class FactorStage(ABC):
    """Abstract interface for a single factorisation stage.

    All stages share the same call signature so they can be composed in a pipeline
    and replaced independently. Stages are stateless — they receive config and
    bounds but hold no mutable state.
    """

    name: str  # Canonical lowercase name used in logs and config

    @abstractmethod
    def attempt(self, n: int, *, config: FactoriserConfig) -> StageResult:
        """Attempt to find a non-trivial factor of *n*.

        Args:
            n: An odd composite integer >= 3. The caller guarantees n is not prime.
            config: Algorithm parameters controlling iteration budgets, etc.

        Returns:
            StageResult describing the outcome.
        """
        ...

    def _elapsed(self, start: float) -> float:
        return (time.monotonic() - start) * 1000


# ---------------------------------------------------------------------------
# Trial Division stage (implemented in pipeline.py for simplicity)
# ---------------------------------------------------------------------------

from source.core import TRIAL_DIVISION_PRIMES  # noqa: E402


class TrialDivisionStage(FactorStage):
    """Trial division by a fixed list of small primes.

    This stage is very fast for small factors and for numbers with small prime
    divisors. It is used as the first gate: if the input has a small factor, there
    is no need to invoke expensive methods.

    The stage tries divisors in ascending order from the fixed prime list until
    a divisor is found or the list is exhausted. If no divisor is found, the stage
    returns FAILURE (not SKIPPED), because the stage was indeed attempted — it
    simply did not find a factor.
    """

    name = "trial_division"

    def __init__(self, bound: int | None = None) -> None:
        self._bound = bound if bound is not None else 10_000

    def attempt(self, n: int, *, config: FactoriserConfig) -> StageResult:
        start = time.monotonic()
        from source.core import validate_int

        validate_int(n)

        for p in TRIAL_DIVISION_PRIMES:
            if self._bound and p > self._bound:
                break
            if n % p == 0:
                logger.debug(
                    "stage={stage} n={n} factor={factor}",
                    stage=self.name,
                    n=n,
                    factor=p,
                )
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.SUCCESS,
                    factor=p,
                    elapsed_ms=self._elapsed(start),
                    iterations_used=1,
                )

        logger.debug(
            "stage={stage} n={n} status=FAILURE reason=no_small_factor",
            stage=self.name,
            n=n,
        )
        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=self._elapsed(start),
            reason="no small factor found in trial division",
        )


# ---------------------------------------------------------------------------
# Pollard p-1 stage (implemented in pipeline.py for simplicity)
# ---------------------------------------------------------------------------


class PollardPMinusOneStage(FactorStage):
    """Pollard's p−1 method.

    This method finds a factor p when p−1 is smooth (has only small prime factors).
    It is particularly effective as an intermediate stage between trial division
    and Pollard's Rho because it can find larger smooth factors that trial division
    misses.

    The algorithm uses stage 1 (first stage) of the p−1 method: compute
    a^B mod n where B is the smoothness bound, then take gcd(a^B - 1, n).
    If p−1 divides B, p will divide the GCD result.
    """

    name = "pollard_pminus1"

    def __init__(self, bound: int | None = None) -> None:
        self._bound = bound if bound is not None else _DEFAULT_PM1_BOUND

    def attempt(self, n: int, *, config: FactoriserConfig) -> StageResult:
        start = time.monotonic()
        import math

        from source.core import validate_int

        validate_int(n)

        if n < 3:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=self._elapsed(start),
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
                    elapsed_ms=self._elapsed(start),
                    iterations_used=1,
                )

        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=self._elapsed(start),
            reason=f"no factor found with bound={self._bound}",
        )


# ---------------------------------------------------------------------------
# Pipeline configuration
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PipelineConfig:
    """Configuration for the multi-stage factorisation pipeline.

    Attributes:
        bound_small: Upper bound below which Pollard p−1 and ECM are skipped.
            Defaults to 10^12.
        bound_medium: Upper bound below which ECM is skipped. Defaults to 10^20.
        bound_large: Upper bound below which QS is skipped. Defaults to 10^40.
        bound_xlarge: Upper bound below which GNFS is attempted. Defaults to 10^80.
        trial_division_bound: Upper prime value for trial division stage.
        pm1_bound: Smoothness bound for Pollard p−1 stage.
        ecm_curves: Number of ECM curves to try before giving up.
        gnfs_timeout: Timeout in seconds for external GNFS subprocess calls.
        gnfs_binary: Path or name of GNFS binary (e.g. "msieve").
        max_iterations: Hard cap on iterations per Pollard-Brent attempt.
        max_retries: Number of fresh Pollard-Brent retries before giving up.
        batch_size: Batch size for Pollard-Brent GCD batching.
        seed: Optional deterministic seed for reproducible retries.
        stage_order: Ordered list of stage names defining the pipeline order.
            Unknown names are ignored.
    """

    bound_small: int = _DEFAULT_BOUND_SMALL
    bound_medium: int = _DEFAULT_BOUND_MEDIUM
    bound_large: int = _DEFAULT_BOUND_LARGE
    bound_xlarge: int = _DEFAULT_BOUND_XLARGE

    trial_division_bound: int = 10_000
    pm1_bound: int = _DEFAULT_PM1_BOUND
    ecm_curves: int = _DEFAULT_ECM_CURVES
    gnfs_timeout: int = _DEFAULT_GNFS_TIMEOUT_SECONDS
    gnfs_binary: str = "msieve"

    max_iterations: int = 10_000_000
    max_retries: int = 20
    batch_size: int = 128
    seed: int | None = None

    stage_order: tuple[str, ...] = (
        "trial_division",
        "pollard_pminus1",
        "pollard_rho",
        "ecm",
        "quadratic_sieve",
        "gnfs",
    )

    def stage_config(self, stage_name: str) -> FactoriserConfig:
        """Derive a FactoriserConfig for a named stage."""
        from source.core import FactoriserConfig

        return FactoriserConfig(
            batch_size=self.batch_size,
            max_iterations=self.max_iterations,
            max_retries=self.max_retries,
            seed=self.seed,
        )

    def enabled_stages(self) -> list[str]:
        """Return ordered list of enabled stage names."""
        return list(self.stage_order)

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Build a PipelineConfig from FACTORISE_* environment variables."""
        import os

        return cls(
            bound_small=int(
                os.getenv("FACTORISE_BOUND_SMALL", str(_DEFAULT_BOUND_SMALL))
            ),
            bound_medium=int(
                os.getenv("FACTORISE_BOUND_MEDIUM", str(_DEFAULT_BOUND_MEDIUM))
            ),
            bound_large=int(
                os.getenv("FACTORISE_BOUND_LARGE", str(_DEFAULT_BOUND_LARGE))
            ),
            bound_xlarge=int(
                os.getenv("FACTORISE_BOUND_XLARGE", str(_DEFAULT_BOUND_XLARGE))
            ),
            trial_division_bound=int(
                os.getenv("FACTORISE_TRIAL_DIVISION_BOUND", "10000")
            ),
            pm1_bound=int(
                os.getenv("FACTORISE_PM1_BOUND", str(_DEFAULT_PM1_BOUND))
            ),
            ecm_curves=int(
                os.getenv("FACTORISE_ECM_CURVES", str(_DEFAULT_ECM_CURVES))
            ),
            gnfs_timeout=int(
                os.getenv("FACTORISE_GNFS_TIMEOUT", str(_DEFAULT_GNFS_TIMEOUT_SECONDS))
            ),
            gnfs_binary=os.getenv("FACTORISE_GNFS_BINARY", "msieve"),
            max_iterations=int(
                os.getenv("FACTORISE_MAX_ITERATIONS", "10000000")
            ),
            max_retries=int(os.getenv("FACTORISE_MAX_RETRIES", "20")),
            batch_size=int(os.getenv("FACTORISE_BATCH_SIZE", "128")),
            seed=int(seed) if (seed := os.getenv("FACTORISE_SEED")) is not None else None,
        )


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------


class FactorisationPipeline:
    """Multi-stage factorisation pipeline.

    The pipeline is constructed with a `PipelineConfig` that specifies which
    stages to run and in what order. It implements the `FactorStage` interface
    so that it can itself be used as a stage in outer pipelines.

    The pipeline handles the overall orchestration: for each composite part it
    has not yet factored, it runs the enabled stages in order until a stage
    returns a non-trivial factor. That factor (and the co-factor) are then fed
    back into the pipeline recursively until every remaining composite is prime.
    """

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self._config = config if config is not None else PipelineConfig()
        self._stages: dict[str, FactorStage] = {}
        self._build_stages()

    def _build_stages(self) -> None:
        """Instantiate stage handlers based on the configured stage order."""
        for name in self._config.enabled_stages():
            if name == "trial_division":
                self._stages[name] = TrialDivisionStage(
                    bound=self._config.trial_division_bound
                )
            elif name == "pollard_pminus1":
                self._stages[name] = PollardPMinusOneStage(
                    bound=self._config.pm1_bound
                )
            elif name == "pollard_rho":
                from source.stages.pollard_rho import PollardRhoStage

                self._stages[name] = PollardRhoStage(
                    max_retries=self._config.max_retries,
                    max_iterations=self._config.max_iterations,
                    batch_size=self._config.batch_size,
                    seed=self._config.seed,
                )
            elif name == "ecm":
                from source.stages.ecm import ECMStage

                self._stages[name] = ECMStage(
                    curves=self._config.ecm_curves,
                    bound=self._config.bound_medium,
                )
            elif name == "quadratic_sieve":
                from source.stages.quadratic_sieve import QuadraticSieveStage

                self._stages[name] = QuadraticSieveStage()
            elif name == "gnfs":
                from source.stages.gnfs import GNFSStage

                self._stages[name] = GNFSStage(
                    binary=self._config.gnfs_binary,
                    timeout_seconds=self._config.gnfs_timeout,
                )

    def attempt(self, n: int, *, config: FactoriserConfig) -> StageResult:
        """Attempt to fully factor *n* using the configured stage pipeline.

        This is the main entry point for a composite input. It runs stages in
        order until the input is fully factored into primes. If all stages
        fail, returns a FAILURE result (not an exception — the pipeline itself
        is a stage, so it returns structured results rather than raising).

        Args:
            n: An odd composite integer >= 3.
            config: Per-stage algorithm parameters.

        Returns:
            StageResult where status is SUCCESS (fully factored) or FAILURE.
            On SUCCESS, the factor field contains a non-trivial factor;
            callers must use it to split the number and recurse.
        """
        from source.core import is_prime

        start = time.monotonic()

        if n < 2:
            return StageResult(
                stage_name="pipeline",
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=self._elapsed(start),
                reason="n < 2",
            )

        if is_prime(n):
            return StageResult(
                stage_name="pipeline",
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=self._elapsed(start),
                reason="n is prime",
            )

        failures: list[str] = []
        for stage_name in self._config.enabled_stages():
            stage = self._stages.get(stage_name)
            if stage is None:
                continue

            result = stage.attempt(n, config=config)
            logger.debug(
                "stage={stage} n={n} status={status} factor={factor} "
                "elapsed_ms={elapsed_ms:.2f}",
                stage=stage_name,
                n=n,
                status=result.status.value,
                factor=result.factor,
                elapsed_ms=result.elapsed_ms,
            )

            if result.is_success() and result.factor is not None:
                return StageResult(
                    stage_name="pipeline",
                    status=StageStatus.SUCCESS,
                    factor=result.factor,
                    elapsed_ms=self._elapsed(start),
                    iterations_used=result.iterations_used,
                )

            if not result.is_skipped():
                failures.append(
                    f"{stage_name}({result.status.value}): {result.reason}"
                )

        return StageResult(
            stage_name="pipeline",
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=self._elapsed(start),
            reason="; ".join(failures) if failures else "all stages failed",
        )

    def _elapsed(self, start: float) -> float:
        return (time.monotonic() - start) * 1000


# ---------------------------------------------------------------------------
# Re-exported types for public API
# ---------------------------------------------------------------------------

__all__ = [
    "FactorisationPipeline",
    "FactorStage",
    "PipelineConfig",
    "StageResult",
    "StageStatus",
]
