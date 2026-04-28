"""Hybrid prime factorisation engine.

A stateful, adaptive factorization pipeline that classifies each composite cofactor
by digit count and routes it to the optimal algorithm.

The cofactor returned by each successful stage is pushed back onto the work stack
and re-routed by digit count. The stack processes the smaller factor first
to keep composites small early.
"""

from __future__ import annotations

__all__ = ["HybridFactorisationEngine", "hybrid_factorise"]

import logging
import time
from collections import Counter

from factorise.config import HybridConfig
from factorise.core import EXTENDED_SMALL_PRIMES
from factorise.core import FactorisationError
from factorise.core import FactorisationResult
from factorise.core import ensure_integer_input
from factorise.core import find_perfect_power
from factorise.core import has_carmichael_property
from factorise.core import is_prime
from factorise.pipeline import FactorStage
from factorise.pipeline import StageStatus
from factorise.stages.ecm_two_pass import TwoPassECMStage
from factorise.stages.gnfs_optimized import OptimizedGNFSStage
from factorise.stages.improved_pm1 import ImprovedPollardPMinusOneStage
from factorise.stages.pollard_rho import PollardRhoStage
from factorise.stages.siqs import SIQSStage
from factorise.stages.trial_division import OptimizedTrialDivisionStage

LOGGER = logging.getLogger("factorise")


def elapsed_ms(start: float) -> float:
    """Return elapsed milliseconds since *start* (from time.monotonic())."""
    return (time.monotonic() - start) * 1000


class HybridFactorisationEngine:
    """Adaptive hybrid factorisation engine.

    Coordinates trial division, Pollard PM1, Pollard Rho, two-pass ECM,
    SIQS, and GNFS into a single stateful pipeline. Each composite cofactor
    is classified by bit length and routed to the optimal algorithm. The smaller
    factor is processed first to minimise the stack depth.
    """

    def __init__(self, config: HybridConfig | None = None) -> None:
        """Initialise the hybrid engine with an optional configuration.

        Args:
            config: Hybrid configuration. Uses defaults if omitted.

        """
        self.config = config if config is not None else HybridConfig()
        self.trial_stage = OptimizedTrialDivisionStage(
            bound=self.config.trial_division_bound,
            prime_table=EXTENDED_SMALL_PRIMES,
        )
        self.pm1_stage = ImprovedPollardPMinusOneStage(
            bounds=self.config.pm1_smoothness_bounds,
            bases=self.config.pm1_trial_bases,
        )
        self.ecm_stage = TwoPassECMStage(
            first_pass_curves=self.config.ecm_first_pass_curves,
            first_pass_bound=self.config.ecm_first_pass_bound,
            second_pass_curves=self.config.ecm_second_pass_curves,
            second_pass_bound=self.config.ecm_second_pass_bound,
        )
        self.siqs_stage = SIQSStage(
            max_bit_length=self.config.siqs_max_bit_length,
        )
        self.rho_stage = PollardRhoStage(
            max_retries=self.config.rho_max_retries,
            max_iterations=self.config.rho_max_iterations,
            batch_size=self.config.rho_batch_size,
        )
        self.gnfs_stage = OptimizedGNFSStage()
        self.stage_map: dict[str, FactorStage] = {
            "trial_division": self.trial_stage,
            "improved_pollard_pminus1": self.pm1_stage,
            "pollard_rho": self.rho_stage,
            "ecm": self.ecm_stage,
            "siqs": self.siqs_stage,
            "gnfs": self.gnfs_stage,
        }

    # -----------------------------------------------------------------------
    # Edge-case handlers
    # -----------------------------------------------------------------------

    def try_zero(self, n: int) -> FactorisationResult | None:
        """Return a result for n == 0, or None."""
        if n == 0:
            return FactorisationResult(
                original=0,
                sign=1,
                factors=[],
                powers={},
                is_prime=False,
            )
        return None

    def try_unit(self, n: int) -> FactorisationResult | None:
        """Return a result for n in {1, -1}, or None."""
        if n in (1, -1):
            sign = -1 if n < 0 else 1
            return FactorisationResult(
                original=n,
                sign=sign,
                factors=[],
                powers={},
                is_prime=False,
            )
        return None

    def try_two(self, n: int) -> FactorisationResult | None:
        """Return a result for n in {2, -2}, or None."""
        if n in (2, -2):
            sign = -1 if n < 0 else 1
            return FactorisationResult(
                original=n,
                sign=sign,
                factors=[2],
                powers={2: 1},
                is_prime=True,
            )
        return None

    def try_perfect_power(
        self, abs_n: int, sign: int
    ) -> FactorisationResult | None:
        """Return a result if abs_n is a perfect power, or None."""
        if not self.config.perfect_power_check:
            return None
        power_result = find_perfect_power(abs_n)
        if power_result is None:
            return None
        inner = self.attempt(power_result.base)
        factors: list[int] = []
        powers: dict[int, int] = {}
        for p, e in inner.powers.items():
            new_e = e * power_result.exponent
            factors.append(p)
            powers[p] = new_e
        return FactorisationResult(
            original=sign * abs_n,
            sign=sign,
            factors=sorted(factors),
            powers=powers,
            is_prime=False,
        )

    def try_even(self, abs_n: int, sign: int) -> FactorisationResult | None:
        """Return a result if abs_n is even, or None."""
        if abs_n % 2 != 0:
            return None
        cofactor = abs_n // 2
        co_result = self.attempt(cofactor)
        factors = [2, *co_result.factors]
        powers = dict(co_result.powers)
        powers[2] = powers.get(2, 0) + 1
        return FactorisationResult(
            original=sign * abs_n,
            sign=sign,
            factors=sorted(factors),
            powers=powers,
            is_prime=False,
        )

    def result_for_prime(self, n: int, sign: int, abs_n: int) -> FactorisationResult:
        """Return a result when abs_n is known to be prime."""
        return FactorisationResult(
            original=n,
            sign=sign,
            factors=[abs_n],
            powers={abs_n: 1},
            is_prime=True,
        )

    # -----------------------------------------------------------------------
    # Algorithm selection
    # -----------------------------------------------------------------------

    def select_algorithm(self, n: int) -> int | None:
        """Return a non-trivial factor of *n* using the optimal algorithm, or None."""
        bucket = self.config.digit_threshold_bucket(n.bit_length())
        stage_names = self.config.stages_for_threshold(bucket)
        LOGGER.debug(
            "select_algorithm n=%d bucket=%d stages=%s",
            n,
            bucket,
            stage_names,
        )
        for name in stage_names:
            stage = self.stage_map.get(name)
            if stage is None:
                continue
            result = stage.attempt(n)
            if (
                result.status is StageStatus.SUCCESS
                and result.factor is not None
            ):
                LOGGER.debug(
                    "select_algorithm n=%d stage=%s factor=%d elapsed_ms=%.2f",
                    n,
                    name,
                    result.factor,
                    result.elapsed_ms,
                )
                return result.factor
        return None

    # -----------------------------------------------------------------------
    # Core stack factorisation
    # -----------------------------------------------------------------------

    def factorise_stack(
        self, abs_n: int
    ) -> tuple[list[int], dict[int, int]]:
        """Factorise abs_n using the composite stack and return factors + powers."""
        composite_stack: list[int] = [abs_n]
        discovered_primes: list[int] = []

        while composite_stack:
            current = composite_stack.pop()
            if is_prime(current):
                discovered_primes.append(current)
                continue

            factor = self.select_algorithm(current)
            if factor is None:
                raise FactorisationError(
                    f"all methods failed for n={current}"
                )

            cofactor = current // factor
            if is_prime(factor):
                discovered_primes.append(factor)
            else:
                composite_stack.append(factor)
            if is_prime(cofactor):
                discovered_primes.append(cofactor)
            else:
                composite_stack.append(cofactor)

        counts = Counter(discovered_primes)
        factors = sorted(counts.keys())
        powers = {prime: counts[prime] for prime in factors}
        return factors, powers

    # -----------------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------------

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
        start = time.monotonic()
        LOGGER.info("hybrid_attempt n=%d", n)

        # Preserve exact handling order: zero -> unit -> two -> perfect power
        # -> primality -> Carmichael log -> even -> stack loop.
        if (result := self.try_zero(n)) is not None:
            LOGGER.info("hybrid_complete n=%d result=zero elapsed_ms=%.3f", n, elapsed_ms(start))
            return result

        if (result := self.try_unit(n)) is not None:
            LOGGER.info("hybrid_complete n=%d result=unit elapsed_ms=%.3f", n, elapsed_ms(start))
            return result

        if (result := self.try_two(n)) is not None:
            LOGGER.info("hybrid_complete n=%d result=two elapsed_ms=%.3f", n, elapsed_ms(start))
            return result

        sign = -1 if n < 0 else 1
        abs_n = abs(n)

        if (result := self.try_perfect_power(abs_n, sign)) is not None:
            LOGGER.info("hybrid_complete n=%d result=perfect_power elapsed_ms=%.3f", n, elapsed_ms(start))
            return result

        if is_prime(abs_n):
            result = self.result_for_prime(n, sign, abs_n)
            LOGGER.info("hybrid_complete n=%d result=prime elapsed_ms=%.3f", n, elapsed_ms(start))
            return result

        if self.config.carmichael_check and has_carmichael_property(abs_n):
            LOGGER.info("carmichael_detected n=%d", n)

        if (result := self.try_even(abs_n, sign)) is not None:
            LOGGER.info("hybrid_complete n=%d result=even elapsed_ms=%.3f", n, elapsed_ms(start))
            return result

        factors, powers = self.factorise_stack(abs_n)
        is_prime_result = len(factors) == 1 and sum(powers.values()) == 1

        result = FactorisationResult(
            original=n,
            sign=sign,
            factors=factors,
            powers=powers,
            is_prime=is_prime_result,
        )
        LOGGER.info(
            "hybrid_complete n=%d factors=%s is_prime=%s elapsed_ms=%.3f",
            n,
            result.factors,
            result.is_prime,
            elapsed_ms(start),
        )
        return result


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
    start = time.monotonic()
    engine = HybridFactorisationEngine(config)
    result = engine.attempt(n)
    LOGGER.info(
        "hybrid_factorise n=%d factors=%s elapsed_ms=%.3f",
        n,
        result.factors,
        elapsed_ms(start),
    )
    return result
