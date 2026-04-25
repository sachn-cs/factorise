"""Comprehensive tests for the hybrid factorisation engine and config."""

import pytest

from factorise.config import HybridConfig
from factorise.config import HybridFactorisationState
from factorise.hybrid import HybridFactorisationEngine
from factorise.hybrid import hybrid_factorise

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
        {
            "trial_division_bound": 0
        },
        {
            "trial_division_bound": -1
        },
        {
            "rho_max_retries": 0
        },
        {
            "rho_max_iterations": 0
        },
        {
            "rho_batch_size": 0
        },
        {
            "ecm_first_pass_curves": 0
        },
        {
            "ecm_second_pass_curves": 0
        },
        {
            "siqs_max_bit_length": 0
        },
        {
            "gnfs_timeout_seconds": 0
        },
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
