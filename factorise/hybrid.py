"""Hybrid prime factorisation engine.

A stateful, adaptive factorization pipeline that classifies each composite cofactor
by digit count and routes it to the optimal algorithm:

    ≤ 12 digits  → trial_division → pollard_rho
    13–20 digits → pollard_pm1 → pollard_rho → ecm
    21–40 digits → pollard_rho → ecm → pollard_pm1
    41–70 digits → ecm (two-pass) → siqs → pollard_rho
    71–100 digits → siqs → gnfs
    > 100 digits → gnfs

The cofactor returned by each successful stage is pushed back onto the work stack
and re-routed by digit count. The stack processes the smaller factor first
(depth-first) to keep composites small early.
"""

from __future__ import annotations

__all__ = ["HybridFactorisationEngine", "hybrid_factorise"]

from collections import Counter

from loguru import logger

from factorise.config import GNFS_MAXIMUM_BIT_LENGTH
from factorise.config import GNFS_MINIMUM_BIT_LENGTH
from factorise.config import LARGE_INTEGER_BIT_BOUND
from factorise.config import MEDIUM_INTEGER_BIT_BOUND
from factorise.config import SIQS_INTEGER_BIT_BOUND
from factorise.config import SMALL_INTEGER_BIT_BOUND
from factorise.config import XLARGE_INTEGER_BIT_BOUND
from factorise.config import HybridConfig
from factorise.core import EXTENDED_SMALL_PRIMES
from factorise.core import FactorisationError
from factorise.core import FactorisationResult
from factorise.core import ensure_integer_input
from factorise.core import find_perfect_power
from factorise.core import has_carmichael_property
from factorise.core import is_prime
from factorise.pipeline import StageStatus
from factorise.stages.ecm_two_pass import TwoPassECMStage
from factorise.stages.improved_pm1 import ImprovedPollardPMinusOneStage
from factorise.stages.siqs import SIQSStage
from factorise.stages.trial_division import OptimizedTrialDivisionStage

logger.disable("factorise")

# ---------------------------------------------------------------------------
# Algorithm routing
# ---------------------------------------------------------------------------


def select_algorithm_by_bit_length(
    n: int,
    config: HybridConfig,
    trial_stage: OptimizedTrialDivisionStage,
    pm1_stage: ImprovedPollardPMinusOneStage,
    ecm_stage: TwoPassECMStage,
    siqs_stage: SIQSStage,
) -> int | None:
    """Return a non-trivial factor of *n* using the optimal algorithm, or None.

    Algorithm selection is driven by the bit length of *n*:
      0-40 bits   → trial_division → pollard_rho
      41-66 bits  → pollard_pm1 → pollard_rho → ecm
      67-133 bits → pollard_rho → ecm → pollard_pm1
      134-233 bits → ecm (two-pass) → siqs → pollard_rho
      234-366 bits → siqs → gnfs
      367+ bits   → gnfs
    """
    bit_length = n.bit_length()

    # ---- ≤ 40 bits: trial division + Pollard Rho ----
    if bit_length <= SMALL_INTEGER_BIT_BOUND:
        result = trial_stage.attempt(n, config=config)  # type: ignore[arg-type]
        if result.status is StageStatus.SUCCESS and result.factor is not None:
            return result.factor
        return invoke_pollard_rho(n, config)

    # ---- 41-66 bits: PM1 → Rho → ECM ----
    if bit_length <= MEDIUM_INTEGER_BIT_BOUND:
        result = pm1_stage.attempt(n, config=config)  # type: ignore[arg-type]
        if result.status is StageStatus.SUCCESS and result.factor is not None:
            return result.factor
        factor = invoke_pollard_rho(n, config)
        if factor is not None:
            return factor
        result = ecm_stage.attempt(n, config=config)  # type: ignore[arg-type]
        if result.status is StageStatus.SUCCESS and result.factor is not None:
            return result.factor
        return None

    # ---- 67-133 bits: Rho → ECM → PM1 ----
    if bit_length <= LARGE_INTEGER_BIT_BOUND:
        factor = invoke_pollard_rho(n, config)
        if factor is not None:
            return factor
        result = ecm_stage.attempt(n, config=config)  # type: ignore[arg-type]
        if result.status is StageStatus.SUCCESS and result.factor is not None:
            return result.factor
        result = pm1_stage.attempt(n, config=config)  # type: ignore[arg-type]
        if result.status is StageStatus.SUCCESS and result.factor is not None:
            return result.factor
        return None

    # ---- 134-233 bits: ECM → SIQS → Rho ----
    if bit_length <= XLARGE_INTEGER_BIT_BOUND:
        result = ecm_stage.attempt(n, config=config)  # type: ignore[arg-type]
        if result.status is StageStatus.SUCCESS and result.factor is not None:
            return result.factor
        result = siqs_stage.attempt(n, config=config)  # type: ignore[arg-type]
        if result.status is StageStatus.SUCCESS and result.factor is not None:
            return result.factor
        return invoke_pollard_rho(n, config)

    # ---- 234-366 bits: SIQS → GNFS ----
    if bit_length <= SIQS_INTEGER_BIT_BOUND:
        result = siqs_stage.attempt(n, config=config)  # type: ignore[arg-type]
        if result.status is StageStatus.SUCCESS and result.factor is not None:
            return result.factor
        return invoke_external_gnfs(n, config)

    # ---- 367+ bits: GNFS ----
    return invoke_external_gnfs(n, config)


def invoke_pollard_rho(n: int, config: HybridConfig) -> int | None:
    """Find a non-trivial factor using Pollard's Rho (Brent)."""
    from factorise.core import FactoriserConfig
    from factorise.core import find_nontrivial_factor_pollard_brent

    cfg = FactoriserConfig(
        batch_size=config.rho_batch_size,
        max_iterations=config.rho_max_iterations,
        max_retries=config.rho_max_retries,
    )
    try:
        return find_nontrivial_factor_pollard_brent(n, cfg)
    except FactorisationError:
        return None


def invoke_external_gnfs(n: int, config: HybridConfig) -> int | None:
    """Attempt GNFS via external tool adapter."""
    from factorise.stages.gnfs import GNFSStage

    bit_length = n.bit_length()
    if bit_length < GNFS_MINIMUM_BIT_LENGTH or bit_length > GNFS_MAXIMUM_BIT_LENGTH:
        return None
    stage = GNFSStage(
        binary=config.gnfs_external_tool_name,
        timeout_seconds=config.gnfs_timeout_seconds,
    )
    from factorise.core import FactoriserConfig
    result = stage.attempt(n, config=FactoriserConfig())
    if result.status is StageStatus.SUCCESS and result.factor is not None:
        return result.factor
    return None


# ---------------------------------------------------------------------------
# HybridFactorisationEngine
# ---------------------------------------------------------------------------


class HybridFactorisationEngine:
    """Adaptive hybrid factorisation engine.

    Coordinates trial division, Pollard PM1, Pollard Rho, two-pass ECM,
    SIQS, and GNFS into a single stateful pipeline. Each composite cofactor
    is classified by bit length and routed to the optimal algorithm. The smaller
    factor is processed first to minimise the stack depth.
    """

    def __init__(self, config: HybridConfig | None = None) -> None:
        self.__config = config if config is not None else HybridConfig()
        self.__trial_stage = OptimizedTrialDivisionStage(
            bound=self.__config.trial_division_bound,
            prime_table=EXTENDED_SMALL_PRIMES,
        )
        self.__pm1_stage = ImprovedPollardPMinusOneStage(
            bounds=self.__config.pm1_smoothness_bounds,
            bases=self.__config.pm1_trial_bases,
        )
        self.__ecm_stage = TwoPassECMStage(
            first_pass_curves=self.__config.ecm_first_pass_curves,
            first_pass_bound=self.__config.ecm_first_pass_bound,
            second_pass_curves=self.__config.ecm_second_pass_curves,
            second_pass_bound=self.__config.ecm_second_pass_bound,
        )
        self.__siqs_stage = SIQSStage(
            max_bit_length=self.__config.siqs_max_bit_length)

    def attempt(self, n: int) -> FactorisationResult:
        """Factorise *n* and return the complete prime decomposition.

        Args:
            n: The integer to factorise.

        Returns:
            FactorisationResult with sign, factors, powers, is_prime.

        Raises:
            FactorisationError: If all methods fail for a composite cofactor.
        """
        ensure_integer_input(n)

        # ---- Phase 0: Trivial inputs ----
        if n == 0:
            return FactorisationResult(original=0,
                                       sign=1,
                                       factors=[],
                                       powers={},
                                       is_prime=False)
        if n == 1 or n == -1:
            sign = -1 if n < 0 else 1
            return FactorisationResult(original=n,
                                       sign=sign,
                                       factors=[],
                                       powers={},
                                       is_prime=False)
        if n == 2 or n == -2:
            sign = -1 if n < 0 else 1
            return FactorisationResult(original=n,
                                       sign=sign,
                                       factors=[2],
                                       powers={2: 1},
                                       is_prime=True)

        sign = -1 if n < 0 else 1
        abs_n = abs(n)

        # ---- Phase 1: Perfect power detection ----
        if self.__config.perfect_power_check:
            power_result = find_perfect_power(abs_n)
            if power_result is not None:
                inner = self.attempt(power_result.base)
                factors: list[int] = []
                powers: dict[int, int] = {}
                for p, e in inner.powers.items():
                    new_e = e * power_result.exponent
                    factors.append(p)
                    powers[p] = new_e
                return FactorisationResult(
                    original=n,
                    sign=sign,
                    factors=sorted(factors),
                    powers=powers,
                    is_prime=False,
                )

        # ---- Phase 2: Primality check ----
        if is_prime(abs_n):
            return FactorisationResult(
                original=n,
                sign=sign,
                factors=[abs_n],
                powers={abs_n: 1},
                is_prime=True,
            )

        # ---- Phase 3: Carmichael detection (optional) ----
        if self.__config.carmichael_check and has_carmichael_property(abs_n):
            logger.info("n={n} is Carmichael, proceeding with factorisation",
                        n=n)

        # ---- Phase 4: Even number fast path ----
        if abs_n % 2 == 0:
            cofactor = abs_n // 2
            co_result = self.attempt(cofactor)
            factors = [2] + co_result.factors
            powers = dict(co_result.powers)
            powers[2] = powers.get(2, 0) + 1
            return FactorisationResult(
                original=n,
                sign=sign,
                factors=sorted(factors),
                powers=powers,
                is_prime=False,
            )

        # ---- Phase 5: Adaptive stack-based factorization ----
        composite_stack: list[int] = [abs_n]
        discovered_primes: list[int] = []

        while composite_stack:
            current = composite_stack.pop()
            if is_prime(current):
                discovered_primes.append(current)
                continue

            factor = select_algorithm_by_bit_length(
                current,
                self.__config,
                self.__trial_stage,
                self.__pm1_stage,
                self.__ecm_stage,
                self.__siqs_stage,
            )
            if factor is None:
                raise FactorisationError(f"all methods failed for n={current}")

            cofactor = current // factor
            if is_prime(factor):
                discovered_primes.append(factor)
            else:
                composite_stack.append(factor)
            if is_prime(cofactor):
                discovered_primes.append(cofactor)
            else:
                composite_stack.append(cofactor)

            # Depth-first: process larger composite next (break it down first)
            if len(composite_stack) > 1:
                max_idx = composite_stack.index(max(composite_stack))
                composite_stack[max_idx], composite_stack[-1] = (
                    composite_stack[-1],
                    composite_stack[max_idx],
                )

        # ---- Phase 6: Build final result ----
        counts = Counter(discovered_primes)
        factors = sorted(counts.keys())
        powers = {prime: counts[prime] for prime in factors}
        is_prime_result = len(factors) == 1 and sum(powers.values()) == 1

        return FactorisationResult(
            original=n,
            sign=sign,
            factors=factors,
            powers=powers,
            is_prime=is_prime_result,
        )


# ---------------------------------------------------------------------------
# Convenience API
# ---------------------------------------------------------------------------


def hybrid_factorise(
    n: int,
    config: HybridConfig | None = None,
) -> FactorisationResult:
    """Factorise *n* using the hybrid engine.

    Args:
        n: The integer to factorise.
        config: Optional HybridConfig. Uses defaults if omitted.

    Returns:
        FactorisationResult with sign, factors, powers, is_prime.
    """
    engine = HybridFactorisationEngine(config)
    return engine.attempt(n)
