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
from collections import Counter

from factorise.config import HybridConfig
from factorise.core import (
    EXTENDED_SMALL_PRIMES,
    FactorisationError,
    FactorisationResult,
    ensure_integer_input,
    find_perfect_power,
    has_carmichael_property,
    is_prime,
)
from factorise.pipeline import FactorStage
from factorise.pipeline import StageStatus
from factorise.stages.ecm_two_pass import TwoPassECMStage
from factorise.stages.gnfs_optimized import OptimizedGNFSStage
from factorise.stages.improved_pm1 import ImprovedPollardPMinusOneStage
from factorise.stages.pollard_rho import PollardRhoStage
from factorise.stages.siqs import SIQSStage
from factorise.stages.trial_division import OptimizedTrialDivisionStage

_LOG = logging.getLogger("factorise")


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
        self._config = config if config is not None else HybridConfig()
        self._trial_stage = OptimizedTrialDivisionStage(
            bound=self._config.trial_division_bound,
            prime_table=EXTENDED_SMALL_PRIMES,
        )
        self._pm1_stage = ImprovedPollardPMinusOneStage(
            bounds=self._config.pm1_smoothness_bounds,
            bases=self._config.pm1_trial_bases,
        )
        self._ecm_stage = TwoPassECMStage(
            first_pass_curves=self._config.ecm_first_pass_curves,
            first_pass_bound=self._config.ecm_first_pass_bound,
            second_pass_curves=self._config.ecm_second_pass_curves,
            second_pass_bound=self._config.ecm_second_pass_bound,
        )
        self._siqs_stage = SIQSStage(
            max_bit_length=self._config.siqs_max_bit_length,
        )
        self._rho_stage = PollardRhoStage(
            max_retries=self._config.rho_max_retries,
            max_iterations=self._config.rho_max_iterations,
            batch_size=self._config.rho_batch_size,
        )
        self._gnfs_stage = OptimizedGNFSStage()
        self._stage_map: dict[str, FactorStage] = {
            "trial_division": self._trial_stage,
            "improved_pollard_pminus1": self._pm1_stage,
            "pollard_rho": self._rho_stage,
            "ecm": self._ecm_stage,
            "siqs": self._siqs_stage,
            "gnfs": self._gnfs_stage,
        }

    def _select_algorithm(self, n: int) -> int | None:
        """Return a non-trivial factor of *n* using the optimal algorithm, or None."""
        bucket = self._config.digit_threshold_bucket(n.bit_length())
        stage_names = self._config.stages_for_threshold(bucket)
        for name in stage_names:
            stage = self._stage_map.get(name)
            if stage is None:
                continue
            result = stage.attempt(n)
            if (result.status is StageStatus.SUCCESS and
                    result.factor is not None):
                return result.factor
        return None

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

        if n == 0:
            return FactorisationResult(
                original=0,
                sign=1,
                factors=[],
                powers={},
                is_prime=False,
            )
        if n in (1, -1):
            sign = -1 if n < 0 else 1
            return FactorisationResult(
                original=n,
                sign=sign,
                factors=[],
                powers={},
                is_prime=False,
            )
        if n in (2, -2):
            sign = -1 if n < 0 else 1
            return FactorisationResult(
                original=n,
                sign=sign,
                factors=[2],
                powers={2: 1},
                is_prime=True,
            )

        sign = -1 if n < 0 else 1
        abs_n = abs(n)

        if self._config.perfect_power_check:
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

        if is_prime(abs_n):
            return FactorisationResult(
                original=n,
                sign=sign,
                factors=[abs_n],
                powers={abs_n: 1},
                is_prime=True,
            )

        if self._config.carmichael_check and has_carmichael_property(abs_n):
            _LOG.info("n=%d is Carmichael, proceeding with factorisation", n)

        if abs_n % 2 == 0:
            cofactor = abs_n // 2
            co_result = self.attempt(cofactor)
            factors = [2, *co_result.factors]
            powers = dict(co_result.powers)
            powers[2] = powers.get(2, 0) + 1
            return FactorisationResult(
                original=n,
                sign=sign,
                factors=sorted(factors),
                powers=powers,
                is_prime=False,
            )

        composite_stack: list[int] = [abs_n]
        discovered_primes: list[int] = []

        while composite_stack:
            current = composite_stack.pop()
            if is_prime(current):
                discovered_primes.append(current)
                continue

            factor = self._select_algorithm(current)
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
