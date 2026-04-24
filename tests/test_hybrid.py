"""Comprehensive tests for the hybrid factorisation engine and config."""

import pytest

from factorise.config import GNFS_MAXIMUM_BIT_LENGTH
from factorise.config import HybridConfig
from factorise.config import HybridFactorisationState
from factorise.hybrid import HybridFactorisationEngine
from factorise.hybrid import hybrid_factorise
from factorise.hybrid import invoke_external_gnfs
from factorise.hybrid import invoke_pollard_rho
from factorise.hybrid import select_algorithm_by_bit_length
from factorise.stages.ecm_two_pass import TwoPassECMStage
from factorise.stages.improved_pm1 import ImprovedPollardPMinusOneStage
from factorise.stages.siqs import SIQSStage
from factorise.stages.trial_division import OptimizedTrialDivisionStage

# ---------------------------------------------------------------------------
# HybridConfig
# ---------------------------------------------------------------------------


def test_hybrid_config_defaults() -> None:
    """Verify HybridConfig initializes with sensible defaults."""
    cfg = HybridConfig()
    assert cfg.trial_division_bound == 10_000
    assert cfg.rho_max_retries == 20
    assert cfg.rho_max_iterations == 10_000_000
    assert cfg.rho_batch_size == 128


def test_hybrid_config_custom() -> None:
    """Verify HybridConfig accepts custom overrides."""
    cfg = HybridConfig(trial_division_bound=5000, rho_batch_size=64)
    assert cfg.trial_division_bound == 5000
    assert cfg.rho_batch_size == 64


@pytest.mark.parametrize(
    "kwargs",
    [
        {"trial_division_bound": 0},
        {"trial_division_bound": -1},
        {"rho_max_retries": 0},
        {"rho_max_iterations": 0},
        {"rho_batch_size": 0},
        {"ecm_first_pass_curves": 0},
        {"ecm_second_pass_curves": 0},
        {"siqs_max_bit_length": 0},
        {"gnfs_timeout_seconds": 0},
    ],
)
def test_hybrid_config_invalid(kwargs: dict[str, int]) -> None:
    """Verify HybridConfig rejects invalid values."""
    with pytest.raises(ValueError):
        HybridConfig(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# HybridFactorisationState
# ---------------------------------------------------------------------------


def test_state_pop_next_composite() -> None:
    """Verify state stack management."""
    cfg = HybridConfig()
    state = HybridFactorisationState(
        original_input=91,
        sign=1,
        composite_stack=[91, 15],
        discovered_prime_factors=[],
        config=cfg,
    )
    assert state.pop_next_composite() == 15
    assert state.pop_next_composite() == 91
    assert state.pop_next_composite() is None


# ---------------------------------------------------------------------------
# invoke_pollard_rho
# ---------------------------------------------------------------------------


def test_invoke_pollard_rho_small() -> None:
    """Verify invoke_pollard_rho finds a factor for a small composite."""
    cfg = HybridConfig()
    factor = invoke_pollard_rho(91, cfg)
    assert factor is not None
    assert 91 % factor == 0


def test_invoke_pollard_rho_prime() -> None:
    """Verify invoke_pollard_rho returns the prime itself for primes."""
    cfg = HybridConfig()
    factor = invoke_pollard_rho(97, cfg)
    assert factor == 97


# ---------------------------------------------------------------------------
# invoke_external_gnfs
# ---------------------------------------------------------------------------


def test_invoke_external_gnfs_too_small() -> None:
    """Verify invoke_external_gnfs skips very small inputs."""
    cfg = HybridConfig()
    factor = invoke_external_gnfs(91, cfg)
    assert factor is None


def test_invoke_external_gnfs_too_large() -> None:
    """Verify invoke_external_gnfs skips very large inputs."""
    cfg = HybridConfig()
    n = 2 ** (GNFS_MAXIMUM_BIT_LENGTH + 1)
    factor = invoke_external_gnfs(n, cfg)
    assert factor is None


# ---------------------------------------------------------------------------
# select_algorithm_by_bit_length
# ---------------------------------------------------------------------------


def test_select_small_bits() -> None:
    """Verify routing for small inputs (≤ 40 bits)."""
    cfg = HybridConfig()
    trial = OptimizedTrialDivisionStage()
    pm1 = ImprovedPollardPMinusOneStage()
    ecm = TwoPassECMStage()
    siqs = SIQSStage()
    factor = select_algorithm_by_bit_length(91, cfg, trial, pm1, ecm, siqs)
    assert factor is not None
    assert 91 % factor == 0


def test_select_medium_bits() -> None:
    """Verify routing for medium inputs (41-66 bits)."""
    cfg = HybridConfig()
    trial = OptimizedTrialDivisionStage()
    pm1 = ImprovedPollardPMinusOneStage()
    ecm = TwoPassECMStage()
    siqs = SIQSStage()
    n = 2 ** 50 + 1
    _factor = select_algorithm_by_bit_length(n, cfg, trial, pm1, ecm, siqs)
    # May or may not find a factor; just verify no crash


def test_select_large_bits() -> None:
    """Verify routing for large inputs (> 66 bits)."""
    cfg = HybridConfig()
    trial = OptimizedTrialDivisionStage()
    pm1 = ImprovedPollardPMinusOneStage()
    ecm = TwoPassECMStage()
    siqs = SIQSStage()
    n = 2 ** 70 + 1
    _factor = select_algorithm_by_bit_length(n, cfg, trial, pm1, ecm, siqs)
    # May or may not find a factor; just verify no crash


# ---------------------------------------------------------------------------
# HybridFactorisationEngine
# ---------------------------------------------------------------------------


def test_hybrid_engine_factorise_small() -> None:
    """Verify the hybrid engine factors a small composite."""
    engine = HybridFactorisationEngine()
    result = engine.attempt(360)
    assert result.factors is not None
    assert 2 in result.factors
    assert 3 in result.factors
    assert 5 in result.factors


def test_hybrid_engine_factorise_prime() -> None:
    """Verify the hybrid engine handles a prime."""
    engine = HybridFactorisationEngine()
    result = engine.attempt(97)
    assert result.factors == [97]
    assert result.is_prime is True


# ---------------------------------------------------------------------------
# hybrid_factorise convenience wrapper
# ---------------------------------------------------------------------------


def test_hybrid_factorise_wrapper() -> None:
    """Verify the convenience wrapper works."""
    result = hybrid_factorise(360)
    assert 2 in result.factors
    assert 3 in result.factors
    assert 5 in result.factors
    assert result.is_prime is False


def test_hybrid_factorise_wrapper_prime() -> None:
    """Verify hybrid_factorise handles primes."""
    result = hybrid_factorise(97)
    assert result.factors == [97]
    assert result.is_prime is True


def test_hybrid_factorise_wrapper_negative() -> None:
    """Verify hybrid_factorise handles negative numbers."""
    result = hybrid_factorise(-12)
    assert result.sign == -1
    assert 2 in result.factors
    assert 3 in result.factors


def test_hybrid_factorise_wrapper_zero_one() -> None:
    """Verify edge cases for 0 and 1."""
    assert hybrid_factorise(0).factors == []
    assert hybrid_factorise(1).factors == []
