"""Hybrid factorization configuration and transient state classes."""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence

__all__ = ["HybridConfig", "HybridFactorisationState"]

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Bit-length boundaries for algorithm selection.
SMALL_INTEGER_BIT_BOUND: int = 40  # ~12 digits; Rho preferred over ECM
MEDIUM_INTEGER_BIT_BOUND: int = 66  # ~20 digits; PM1 viable
LARGE_INTEGER_BIT_BOUND: int = 133  # ~40 digits; ECM competitive
XLARGE_INTEGER_BIT_BOUND: int = 233  # ~70 digits; SIQS territory
SIQS_INTEGER_BIT_BOUND: int = 366  # ~110 digits; SIQS practical limit in pure Python

GNFS_MINIMUM_BIT_LENGTH: int = 80
GNFS_MAXIMUM_BIT_LENGTH: int = 500

# Trial division.
TRIAL_DIVISION_PRIME_COUNT: int = 1000  # primes up to ~7919

# Pollard p-1.
PM1_SMOOTHNESS_BOUNDS: tuple[int, ...] = (10**6, 10**7, 10**8, 10**9)
PM1_TRIAL_BASES: tuple[int, ...] = (2, 3, 5, 7, 11)

# ECM.
ECM_FIRST_PASS_CURVES: int = 20
ECM_FIRST_PASS_BOUND: int = 10_000
ECM_SECOND_PASS_CURVES: int = 30
ECM_SECOND_PASS_BOUND: int = 50_000

# Pollard Rho.
RHO_MAX_RETRIES: int = 20
RHO_MAX_ITERATIONS: int = 10_000_000
RHO_BATCH_SIZE: int = 128

# SIQS.
SIQS_MAX_BIT_LENGTH: int = 110

# GNFS.
GNFS_TIMEOUT_SECONDS: int = 600
GNFS_EXTERNAL_TOOL_NAME: str = "msieve"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class HybridConfig:
    """Algorithm parameters and thresholds for the hybrid factorization engine.

    All values are validated in __post_init__. Defaults are chosen for a
    reasonable balance across input sizes from small (64-bit) to large
    (arbitrary-precision via GNFS).
    """

    # Trial division
    trial_division_bound: int = 10_000
    trial_division_prime_count: int = TRIAL_DIVISION_PRIME_COUNT

    # Pollard p-1
    pm1_smoothness_bounds: tuple[int, ...] = PM1_SMOOTHNESS_BOUNDS
    pm1_trial_bases: tuple[int, ...] = PM1_TRIAL_BASES

    # Pollard Rho
    rho_max_retries: int = RHO_MAX_RETRIES
    rho_max_iterations: int = RHO_MAX_ITERATIONS
    rho_batch_size: int = RHO_BATCH_SIZE

    # ECM
    ecm_first_pass_curves: int = ECM_FIRST_PASS_CURVES
    ecm_first_pass_bound: int = ECM_FIRST_PASS_BOUND
    ecm_second_pass_curves: int = ECM_SECOND_PASS_CURVES
    ecm_second_pass_bound: int = ECM_SECOND_PASS_BOUND

    # SIQS
    siqs_max_bit_length: int = SIQS_MAX_BIT_LENGTH

    # GNFS
    gnfs_timeout_seconds: int = GNFS_TIMEOUT_SECONDS
    gnfs_external_tool_name: str = GNFS_EXTERNAL_TOOL_NAME

    # Detection toggles
    perfect_power_check: bool = True
    carmichael_check: bool = False  # expensive for large n; off by default

    # Stage ordering (future extensibility)
    stage_order: tuple[str, ...] = (
        "trial_division",
        "pollard_pm1",
        "pollard_rho",
        "ecm",
        "siqs",
        "gnfs",
    )

    def __post_init__(self) -> None:
        """Validate all fields immediately at construction time."""
        if not 1 <= self.trial_division_bound <= 100_000:
            raise ValueError(
                f"trial_division_bound must be 1-100000, got {self.trial_division_bound}"
            )
        if not 1 <= self.trial_division_prime_count <= 10_000:
            raise ValueError(f"trial_division_prime_count must be 1-10000, got "
                             f"{self.trial_division_prime_count}")
        if not self.pm1_smoothness_bounds:
            raise ValueError("pm1_smoothness_bounds must not be empty")
        for b in self.pm1_smoothness_bounds:
            if b < 1:
                raise ValueError(
                    f"each pm1_smoothness_bound must be >= 1, got {b}")
        for base in self.pm1_trial_bases:
            if base < 2:
                raise ValueError(
                    f"each pm1_trial_base must be >= 2, got {base}")
        if not 1 <= self.rho_max_retries <= 1000:
            raise ValueError(
                f"rho_max_retries must be 1-1000, got {self.rho_max_retries}")
        if not 1 <= self.rho_max_iterations <= 1_000_000_000:
            raise ValueError(
                f"rho_max_iterations must be 1-1e9, got {self.rho_max_iterations}"
            )
        if not 1 <= self.rho_batch_size <= 10_000:
            raise ValueError(
                f"rho_batch_size must be 1-10000, got {self.rho_batch_size}")
        if not 1 <= self.ecm_first_pass_curves <= 1000:
            raise ValueError(
                f"ecm_first_pass_curves must be 1-1000, got {self.ecm_first_pass_curves}"
            )
        if not 1 <= self.ecm_first_pass_bound <= 10_000_000:
            raise ValueError(
                f"ecm_first_pass_bound must be 1-1e7, got {self.ecm_first_pass_bound}"
            )
        if not 1 <= self.ecm_second_pass_curves <= 1000:
            raise ValueError(
                f"ecm_second_pass_curves must be 1-1000, got {self.ecm_second_pass_curves}"
            )
        if not 1 <= self.ecm_second_pass_bound <= 10_000_000:
            raise ValueError(
                f"ecm_second_pass_bound must be 1-1e7, got {self.ecm_second_pass_bound}"
            )
        if self.ecm_second_pass_bound <= self.ecm_first_pass_bound:
            raise ValueError(
                f"ecm_second_pass_bound ({self.ecm_second_pass_bound}) must be > "
                f"ecm_first_pass_bound ({self.ecm_first_pass_bound})")
        if not 10 <= self.siqs_max_bit_length <= 500:
            raise ValueError(
                f"siqs_max_bit_length must be 10-500, got {self.siqs_max_bit_length}"
            )
        if not 1 <= self.gnfs_timeout_seconds <= 86400:
            raise ValueError(
                f"gnfs_timeout_seconds must be 1-86400, got {self.gnfs_timeout_seconds}"
            )

    def digit_threshold_bucket(self, bit_length: int) -> int:
        """Return digit-count bucket for *bit_length* (0-5) used in route_algorithm."""
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
        """Return ordered stage list appropriate for a digit-count bucket."""
        if threshold == 0:
            return ("trial_division", "pollard_rho")
        if threshold == 1:
            return ("pollard_pm1", "pollard_rho", "ecm")
        if threshold == 2:
            return ("pollard_rho", "ecm", "pollard_pm1")
        if threshold == 3:
            return ("ecm", "siqs", "pollard_rho")
        if threshold == 4:
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
    """

    original_input: int
    sign: int
    composite_stack: list[int]
    discovered_prime_factors: list[int]
    config: HybridConfig
    total_iterations: int = 0

    def pop_next_composite(self) -> int | None:
        """Pop the next value off the composite stack.

        Returns:
            The next value from the stack, or None if the stack is empty.
        """
        while self.composite_stack:
            current = self.composite_stack.pop()
            return current
        return None
