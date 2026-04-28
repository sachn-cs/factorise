"""Configuration classes for the factorise package.

Defines immutable dataclasses that control algorithm parameters, pipeline
stage ordering, and input-size thresholds. All configs validate their fields
at construction time so that invalid values are rejected immediately.
"""

from __future__ import annotations

import dataclasses
import os
from collections.abc import Sequence

__all__ = [
    "AlgorithmConfig",
    "FactoriserConfig",
    "HybridConfig",
    "HybridFactorisationState",
    "PipelineConfig",
]

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

SMALL_INTEGER_BIT_BOUND: int = 40
MEDIUM_INTEGER_BIT_BOUND: int = 66
LARGE_INTEGER_BIT_BOUND: int = 133
XLARGE_INTEGER_BIT_BOUND: int = 233
SIQS_INTEGER_BIT_BOUND: int = 366

GNFS_MINIMUM_BIT_LENGTH: int = 80
GNFS_MAXIMUM_BIT_LENGTH: int = 500

TRIAL_DIVISION_PRIME_COUNT: int = 1000

PM1_SMOOTHNESS_BOUNDS: tuple[int, ...] = (10**6, 10**7, 10**8, 10**9)
PM1_TRIAL_BASES: tuple[int, ...] = (2, 3, 5, 7, 11)

ECM_FIRST_PASS_CURVES: int = 20
ECM_FIRST_PASS_BOUND: int = 10_000
ECM_SECOND_PASS_CURVES: int = 30
ECM_SECOND_PASS_BOUND: int = 50_000

RHO_MAX_RETRIES: int = 20
RHO_MAX_ITERATIONS: int = 10_000_000
RHO_BATCH_SIZE: int = 128

SIQS_MAX_BIT_LENGTH: int = 110

GNFS_TIMEOUT_SECONDS: int = 600
GNFS_EXTERNAL_TOOL_NAME: str = "msieve"

# ---------------------------------------------------------------------------
# Pipeline defaults
# ---------------------------------------------------------------------------

DEFAULT_BOUND_SMALL: int = 10**12
DEFAULT_BOUND_MEDIUM: int = 10**20
DEFAULT_BOUND_LARGE: int = 10**40
DEFAULT_BOUND_XLARGE: int = 10**80
DEFAULT_PM1_BOUND: int = 10**6
DEFAULT_ECM_CURVES: int = 20
DEFAULT_GNFS_TIMEOUT_SECONDS: int = 600

# ---------------------------------------------------------------------------
# Validation bounds
# ---------------------------------------------------------------------------

BUCKET_SMALL: int = 0
BUCKET_MEDIUM: int = 1
BUCKET_LARGE: int = 2
BUCKET_XLARGE: int = 3
BUCKET_SIQS: int = 4

# AlgorithmConfig validation bounds.
BATCH_SIZE_MIN: int = 1
BATCH_SIZE_MAX: int = 10_000
MAX_ITERATIONS_MIN: int = 1
MAX_ITERATIONS_MAX: int = 100_000_000
MAX_RETRIES_MIN: int = 1
MAX_RETRIES_MAX: int = 100

# HybridConfig validation bounds.
TRIAL_DIVISION_BOUND_MIN: int = 1
TRIAL_DIVISION_BOUND_MAX: int = 100_000
TRIAL_DIVISION_PRIME_COUNT_MIN: int = 1
TRIAL_DIVISION_PRIME_COUNT_MAX: int = 10_000

PM1_SMOOTHNESS_BOUND_MIN: int = 1
PM1_TRIAL_BASE_MIN: int = 2

RHO_MAX_RETRIES_MIN: int = 1
RHO_MAX_RETRIES_MAX: int = 1000
RHO_MAX_ITERATIONS_MIN: int = 1
RHO_MAX_ITERATIONS_MAX: int = 1_000_000_000
RHO_BATCH_SIZE_MIN: int = 1
RHO_BATCH_SIZE_MAX: int = 10_000

ECM_CURVES_MIN: int = 1
ECM_CURVES_MAX: int = 1000
ECM_FIRST_PASS_BOUND_MIN: int = 1
ECM_FIRST_PASS_BOUND_MAX: int = 10_000_000
ECM_SECOND_PASS_BOUND_MIN: int = 1
ECM_SECOND_PASS_BOUND_MAX: int = 10_000_000

SIQS_MAX_BIT_LENGTH_MIN: int = 10
SIQS_MAX_BIT_LENGTH_MAX: int = 500

GNFS_TIMEOUT_MIN: int = 1
GNFS_TIMEOUT_MAX: int = 86400

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def validate_int_range(
    name: str,
    value: int,
    min_val: int,
    max_val: int,
) -> None:
    """Raise ValueError if *value* is outside [*min_val*, *max_val*]."""
    if not min_val <= value <= max_val:
        raise ValueError(
            f"{name} must be {min_val}-{max_val}, got {value}"
        )


def env_int(var: str, default: str) -> int:
    """Parse an environment variable as an integer.

    Args:
        var: The environment variable name.
        default: Default string value if the variable is absent.

    Returns:
        The parsed integer.

    Raises:
        ValueError: If the raw value cannot be parsed as an integer.

    """
    raw = os.getenv(var, default)
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(
            f"Invalid {var}={raw!r}: must be an integer"
        ) from exc


# ---------------------------------------------------------------------------
# Base configuration
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class AlgorithmConfig:
    """Base configuration shared by all factorisation orchestrators.

    Attributes:
        max_iterations: Hard cap on inner steps per attempt.
        max_retries: How many fresh random seeds to try before giving up.
        batch_size: GCD operations to batch per iteration.
        seed: Optional deterministic seed base for reproducible retries.

    """

    max_iterations: int = 10_000_000
    max_retries: int = 20
    batch_size: int = 128
    seed: int | None = None

    def __post_init__(self) -> None:
        """Validate fields immediately and fail fast at construction time.

        Raises:
            ValueError: If any field is outside its allowed range.

        """
        validate_int_range(
            "batch_size", self.batch_size, BATCH_SIZE_MIN, BATCH_SIZE_MAX
        )
        validate_int_range(
            "max_iterations",
            self.max_iterations,
            MAX_ITERATIONS_MIN,
            MAX_ITERATIONS_MAX,
        )
        validate_int_range(
            "max_retries", self.max_retries, MAX_RETRIES_MIN, MAX_RETRIES_MAX
        )


# ---------------------------------------------------------------------------
# Core factorisation configuration
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class FactoriserConfig(AlgorithmConfig):
    """Algorithm parameters for core factorisation."""

    @classmethod
    def from_env(cls) -> FactoriserConfig:
        """Build a config from FACTORISE_* environment variables.

        Falls back to the dataclass defaults when variables are absent.

        Returns:
            A FactoriserConfig populated from the environment.

        Raises:
            ValueError: If any environment variable holds an invalid value.

        """
        seed = os.getenv("FACTORISE_SEED")
        return cls(
            batch_size=env_int("FACTORISE_BATCH_SIZE", "128"),
            max_iterations=env_int("FACTORISE_MAX_ITERATIONS", "10000000"),
            max_retries=env_int("FACTORISE_MAX_RETRIES", "20"),
            seed=int(seed) if seed is not None else None,
        )


# ---------------------------------------------------------------------------
# Pipeline configuration
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PipelineConfig(AlgorithmConfig):
    """Configuration for the multi-stage factorisation pipeline.

    Attributes:
        bound_small: Upper bound below which Pollard p-1 and ECM are skipped.
        bound_medium: Upper bound below which ECM is skipped.
        bound_large: Upper bound below which QS is skipped.
        bound_xlarge: Upper bound below which GNFS is attempted.
        trial_division_bound: Upper prime value for trial division stage.
        pm1_bound: Smoothness bound for Pollard p-1 stage.
        ecm_curves: Number of ECM curves to try before giving up.
        gnfs_timeout: Timeout in seconds for external GNFS subprocess calls.
        gnfs_binary: Path or name of GNFS binary.
        stage_order: Ordered list of stage names defining the pipeline order.

    """

    bound_small: int = DEFAULT_BOUND_SMALL
    bound_medium: int = DEFAULT_BOUND_MEDIUM
    bound_large: int = DEFAULT_BOUND_LARGE
    bound_xlarge: int = DEFAULT_BOUND_XLARGE

    trial_division_bound: int = 10_000
    pm1_bound: int = DEFAULT_PM1_BOUND
    ecm_curves: int = DEFAULT_ECM_CURVES
    gnfs_timeout: int = DEFAULT_GNFS_TIMEOUT_SECONDS
    gnfs_binary: str = "msieve"

    stage_order: tuple[str, ...] = (
        "trial_division",
        "pollard_pminus1",
        "pollard_rho",
        "ecm",
        "quadratic_sieve",
        "gnfs",
    )

    def enabled_stages(self) -> list[str]:
        """Return the ordered list of stage names in the pipeline.

        Returns:
            A list of canonical stage names in execution order.

        """
        return list(self.stage_order)

    @classmethod
    def from_env(cls) -> PipelineConfig:
        """Build a PipelineConfig from FACTORISE_* environment variables.

        Returns:
            A PipelineConfig populated from the environment.

        Raises:
            ValueError: If any environment variable holds an invalid value.

        """
        seed = os.getenv("FACTORISE_SEED")
        return cls(
            bound_small=env_int(
                "FACTORISE_BOUND_SMALL", str(DEFAULT_BOUND_SMALL)
            ),
            bound_medium=env_int(
                "FACTORISE_BOUND_MEDIUM", str(DEFAULT_BOUND_MEDIUM)
            ),
            bound_large=env_int(
                "FACTORISE_BOUND_LARGE", str(DEFAULT_BOUND_LARGE)
            ),
            bound_xlarge=env_int(
                "FACTORISE_BOUND_XLARGE", str(DEFAULT_BOUND_XLARGE)
            ),
            trial_division_bound=env_int(
                "FACTORISE_TRIAL_DIVISION_BOUND", "10000"
            ),
            pm1_bound=env_int(
                "FACTORISE_PM1_BOUND", str(DEFAULT_PM1_BOUND)
            ),
            ecm_curves=env_int(
                "FACTORISE_ECM_CURVES", str(DEFAULT_ECM_CURVES)
            ),
            gnfs_timeout=env_int(
                "FACTORISE_GNFS_TIMEOUT",
                str(DEFAULT_GNFS_TIMEOUT_SECONDS),
            ),
            gnfs_binary=os.getenv("FACTORISE_GNFS_BINARY", "msieve"),
            max_iterations=env_int(
                "FACTORISE_MAX_ITERATIONS", "10000000"
            ),
            max_retries=env_int("FACTORISE_MAX_RETRIES", "20"),
            batch_size=env_int("FACTORISE_BATCH_SIZE", "128"),
            seed=int(seed) if seed is not None else None,
        )


# ---------------------------------------------------------------------------
# Hybrid configuration
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class HybridConfig(AlgorithmConfig):
    """Algorithm parameters and thresholds for the hybrid factorization engine.

    All values are validated in __post_init__. Defaults are chosen for a
    reasonable balance across input sizes from small to large.
    """

    trial_division_bound: int = 10_000
    trial_division_prime_count: int = TRIAL_DIVISION_PRIME_COUNT

    pm1_smoothness_bounds: tuple[int, ...] = PM1_SMOOTHNESS_BOUNDS
    pm1_trial_bases: tuple[int, ...] = PM1_TRIAL_BASES

    rho_max_retries: int = RHO_MAX_RETRIES
    rho_max_iterations: int = RHO_MAX_ITERATIONS
    rho_batch_size: int = RHO_BATCH_SIZE

    ecm_first_pass_curves: int = ECM_FIRST_PASS_CURVES
    ecm_first_pass_bound: int = ECM_FIRST_PASS_BOUND
    ecm_second_pass_curves: int = ECM_SECOND_PASS_CURVES
    ecm_second_pass_bound: int = ECM_SECOND_PASS_BOUND

    siqs_max_bit_length: int = SIQS_MAX_BIT_LENGTH

    gnfs_timeout_seconds: int = GNFS_TIMEOUT_SECONDS
    gnfs_external_tool_name: str = GNFS_EXTERNAL_TOOL_NAME

    perfect_power_check: bool = True
    carmichael_check: bool = False

    stage_order: tuple[str, ...] = (
        "trial_division",
        "pollard_pminus1",
        "pollard_rho",
        "ecm",
        "siqs",
        "gnfs",
    )

    def __post_init__(self) -> None:
        """Validate all fields immediately at construction time.

        Raises:
            ValueError: If any field is outside its allowed range.

        """
        super().__post_init__()
        self._validate_trial_division()
        self._validate_pm1()
        self._validate_rho()
        self._validate_ecm()
        self._validate_siqs()
        self._validate_gnfs()

    def _validate_trial_division(self) -> None:
        """Validate trial division bound and prime count.

        Raises:
            ValueError: If trial_division_bound or trial_division_prime_count
                is outside its allowed range.

        """
        validate_int_range(
            "trial_division_bound",
            self.trial_division_bound,
            TRIAL_DIVISION_BOUND_MIN,
            TRIAL_DIVISION_BOUND_MAX,
        )
        validate_int_range(
            "trial_division_prime_count",
            self.trial_division_prime_count,
            TRIAL_DIVISION_PRIME_COUNT_MIN,
            TRIAL_DIVISION_PRIME_COUNT_MAX,
        )

    def _validate_pm1(self) -> None:
        """Validate Pollard p-1 smoothness bounds and trial bases.

        Raises:
            ValueError: If pm1_smoothness_bounds is empty or any bound/base
                is below its minimum.

        """
        if not self.pm1_smoothness_bounds:
            raise ValueError("pm1_smoothness_bounds must not be empty")
        for bound in self.pm1_smoothness_bounds:
            if bound < PM1_SMOOTHNESS_BOUND_MIN:
                raise ValueError(
                    f"each pm1_smoothness_bound must be >= {PM1_SMOOTHNESS_BOUND_MIN}, "
                    f"got {bound}"
                )
        for base in self.pm1_trial_bases:
            if base < PM1_TRIAL_BASE_MIN:
                raise ValueError(
                    f"each pm1_trial_base must be >= {PM1_TRIAL_BASE_MIN}, got {base}"
                )

    def _validate_rho(self) -> None:
        """Validate Pollard Rho retry, iteration, and batch size limits.

        Raises:
            ValueError: If any rho parameter is outside its allowed range.

        """
        validate_int_range(
            "rho_max_retries",
            self.rho_max_retries,
            RHO_MAX_RETRIES_MIN,
            RHO_MAX_RETRIES_MAX,
        )
        validate_int_range(
            "rho_max_iterations",
            self.rho_max_iterations,
            RHO_MAX_ITERATIONS_MIN,
            RHO_MAX_ITERATIONS_MAX,
        )
        validate_int_range(
            "rho_batch_size",
            self.rho_batch_size,
            RHO_BATCH_SIZE_MIN,
            RHO_BATCH_SIZE_MAX,
        )

    def _validate_ecm(self) -> None:
        """Validate ECM curve counts and smoothness bounds.

        Raises:
            ValueError: If any ECM parameter is outside its allowed range or
                if the second pass bound is not greater than the first.

        """
        validate_int_range(
            "ecm_first_pass_curves",
            self.ecm_first_pass_curves,
            ECM_CURVES_MIN,
            ECM_CURVES_MAX,
        )
        validate_int_range(
            "ecm_first_pass_bound",
            self.ecm_first_pass_bound,
            ECM_FIRST_PASS_BOUND_MIN,
            ECM_FIRST_PASS_BOUND_MAX,
        )
        validate_int_range(
            "ecm_second_pass_curves",
            self.ecm_second_pass_curves,
            ECM_CURVES_MIN,
            ECM_CURVES_MAX,
        )
        validate_int_range(
            "ecm_second_pass_bound",
            self.ecm_second_pass_bound,
            ECM_SECOND_PASS_BOUND_MIN,
            ECM_SECOND_PASS_BOUND_MAX,
        )
        if self.ecm_second_pass_bound <= self.ecm_first_pass_bound:
            raise ValueError(
                f"ecm_second_pass_bound ({self.ecm_second_pass_bound}) must be > "
                f"ecm_first_pass_bound ({self.ecm_first_pass_bound})"
            )

    def _validate_siqs(self) -> None:
        """Validate the SIQS maximum bit length.

        Raises:
            ValueError: If siqs_max_bit_length is outside its allowed range.

        """
        validate_int_range(
            "siqs_max_bit_length",
            self.siqs_max_bit_length,
            SIQS_MAX_BIT_LENGTH_MIN,
            SIQS_MAX_BIT_LENGTH_MAX,
        )

    def _validate_gnfs(self) -> None:
        """Validate the GNFS timeout.

        Raises:
            ValueError: If gnfs_timeout_seconds is outside its allowed range.

        """
        validate_int_range(
            "gnfs_timeout_seconds",
            self.gnfs_timeout_seconds,
            GNFS_TIMEOUT_MIN,
            GNFS_TIMEOUT_MAX,
        )

    def digit_threshold_bucket(self, bit_length: int) -> int:
        """Classify an integer by bit length into a routing bucket.

        The hybrid engine uses the bucket to select an appropriate subset of
        algorithms. Larger buckets correspond to larger integers and trigger
        more powerful (but slower) methods.

        Args:
            bit_length: The number of bits required to represent the integer.

        Returns:
            An integer bucket identifier in the range [0, 5].

        """
        if bit_length <= SMALL_INTEGER_BIT_BOUND:
            return 0
        if bit_length <= MEDIUM_INTEGER_BIT_BOUND:
            return 1
        if bit_length <= LARGE_INTEGER_BIT_BOUND:
            return 2
        if bit_length <= XLARGE_INTEGER_BIT_BOUND:
            return 3
        if bit_length <= SIQS_INTEGER_BIT_BOUND:
            return 4
        return 5

    def stages_for_threshold(self, threshold: int) -> Sequence[str]:
        """Return the ordered stage list for a given digit-count bucket.

        Args:
            threshold: A bucket identifier returned by digit_threshold_bucket.

        Returns:
            A tuple of stage names in the order they should be attempted.

        """
        if threshold == BUCKET_SMALL:
            return ("trial_division", "pollard_rho")
        if threshold == BUCKET_MEDIUM:
            return ("improved_pollard_pminus1", "pollard_rho", "ecm")
        if threshold == BUCKET_LARGE:
            return ("pollard_rho", "ecm", "improved_pollard_pminus1")
        if threshold == BUCKET_XLARGE:
            return ("ecm", "siqs", "pollard_rho")
        if threshold == BUCKET_SIQS:
            return ("siqs", "gnfs")
        return ("gnfs",)


# ---------------------------------------------------------------------------
# Transient factorization state
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class HybridFactorisationState:
    """Mutable transient state for one hybrid factorization run.

    Tracks the work stack of composite cofactors, confirmed prime factors,
    and cumulative iteration counts.

    Attributes:
        original_input: The absolute value of the integer being factored.
        sign: 1 if the original input was non-negative, -1 otherwise.
        composite_stack: Remaining composite cofactors to process.
        discovered_prime_factors: Prime factors found so far.
        config: The HybridConfig governing this run.
        total_iterations: Running total of algorithm iterations consumed.

    """

    original_input: int
    sign: int
    composite_stack: list[int]
    discovered_prime_factors: list[int]
    config: HybridConfig
    total_iterations: int = 0

    def pop_next_composite(self) -> int | None:
        """Remove and return the next value from the composite stack.

        Returns:
            The next composite cofactor, or None if the stack is empty.

        """
        if self.composite_stack:
            return self.composite_stack.pop()
        return None
