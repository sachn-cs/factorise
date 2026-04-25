"""Extended tests for factorise.config."""

import pytest

from factorise.config import LARGE_INTEGER_BIT_BOUND
from factorise.config import MEDIUM_INTEGER_BIT_BOUND
from factorise.config import SIQS_INTEGER_BIT_BOUND
from factorise.config import SMALL_INTEGER_BIT_BOUND
from factorise.config import XLARGE_INTEGER_BIT_BOUND
from factorise.config import HybridConfig
from factorise.config import HybridFactorisationState

# ---------------------------------------------------------------------------
# HybridConfig validation
# ---------------------------------------------------------------------------


def test_hybrid_config_negative_trial_division_bound() -> None:
    """Verify HybridConfig rejects negative bound."""
    with pytest.raises(ValueError):
        HybridConfig(trial_division_bound=-1)


def test_hybrid_config_negative_rho_max_retries() -> None:
    """Verify HybridConfig rejects negative retries."""
    with pytest.raises(ValueError):
        HybridConfig(rho_max_retries=-1)


def test_hybrid_config_negative_rho_max_iterations() -> None:
    """Verify HybridConfig rejects negative iterations."""
    with pytest.raises(ValueError):
        HybridConfig(rho_max_iterations=-1)


def test_hybrid_config_negative_rho_batch_size() -> None:
    """Verify HybridConfig rejects negative batch size."""
    with pytest.raises(ValueError):
        HybridConfig(rho_batch_size=-1)


def test_hybrid_config_negative_ecm_first_pass_curves() -> None:
    """Verify HybridConfig rejects negative curves."""
    with pytest.raises(ValueError):
        HybridConfig(ecm_first_pass_curves=-1)


def test_hybrid_config_negative_ecm_second_pass_curves() -> None:
    """Verify HybridConfig rejects negative curves."""
    with pytest.raises(ValueError):
        HybridConfig(ecm_second_pass_curves=-1)


def test_hybrid_config_zero_trial_division_bound() -> None:
    """Verify HybridConfig rejects zero bound."""
    with pytest.raises(ValueError):
        HybridConfig(trial_division_bound=0)


def test_hybrid_config_zero_rho_max_retries() -> None:
    """Verify HybridConfig rejects zero retries."""
    with pytest.raises(ValueError):
        HybridConfig(rho_max_retries=0)


def test_hybrid_config_zero_rho_max_iterations() -> None:
    """Verify HybridConfig rejects zero iterations."""
    with pytest.raises(ValueError):
        HybridConfig(rho_max_iterations=0)


def test_hybrid_config_zero_rho_batch_size() -> None:
    """Verify HybridConfig rejects zero batch size."""
    with pytest.raises(ValueError):
        HybridConfig(rho_batch_size=0)


def test_hybrid_config_zero_ecm_first_pass_curves() -> None:
    """Verify HybridConfig rejects zero curves."""
    with pytest.raises(ValueError):
        HybridConfig(ecm_first_pass_curves=0)


def test_hybrid_config_zero_ecm_second_pass_curves() -> None:
    """Verify HybridConfig rejects zero curves."""
    with pytest.raises(ValueError):
        HybridConfig(ecm_second_pass_curves=0)


def test_hybrid_config_invalid_trial_division_prime_count() -> None:
    """Verify HybridConfig rejects invalid prime count."""
    with pytest.raises(ValueError):
        HybridConfig(trial_division_prime_count=0)
    with pytest.raises(ValueError):
        HybridConfig(trial_division_prime_count=-1)
    with pytest.raises(ValueError):
        HybridConfig(trial_division_prime_count=20000)


def test_hybrid_config_empty_pm1_bounds() -> None:
    """Verify HybridConfig rejects empty pm1 bounds."""
    with pytest.raises(ValueError):
        HybridConfig(pm1_smoothness_bounds=())


def test_hybrid_config_negative_pm1_bound() -> None:
    """Verify HybridConfig rejects negative pm1 bound."""
    with pytest.raises(ValueError):
        HybridConfig(pm1_smoothness_bounds=(100, -1))


def test_hybrid_config_invalid_pm1_base() -> None:
    """Verify HybridConfig rejects invalid pm1 trial base."""
    with pytest.raises(ValueError):
        HybridConfig(pm1_trial_bases=(1,))
    with pytest.raises(ValueError):
        HybridConfig(pm1_trial_bases=(0,))


def test_hybrid_config_invalid_ecm_bound() -> None:
    """Verify HybridConfig rejects invalid ECM bounds."""
    with pytest.raises(ValueError):
        HybridConfig(ecm_first_pass_bound=0)
    with pytest.raises(ValueError):
        HybridConfig(ecm_second_pass_bound=0)


def test_hybrid_config_ecm_second_less_than_first() -> None:
    """Verify HybridConfig rejects second_pass_bound <= first_pass_bound."""
    with pytest.raises(ValueError):
        HybridConfig(ecm_first_pass_bound=10000, ecm_second_pass_bound=5000)
    with pytest.raises(ValueError):
        HybridConfig(ecm_first_pass_bound=10000, ecm_second_pass_bound=10000)


def test_hybrid_config_invalid_siqs_max_bit_length() -> None:
    """Verify HybridConfig rejects invalid SIQS bit length."""
    with pytest.raises(ValueError):
        HybridConfig(siqs_max_bit_length=0)
    with pytest.raises(ValueError):
        HybridConfig(siqs_max_bit_length=9)
    with pytest.raises(ValueError):
        HybridConfig(siqs_max_bit_length=501)


def test_hybrid_config_invalid_gnfs_timeout() -> None:
    """Verify HybridConfig rejects invalid GNFS timeout."""
    with pytest.raises(ValueError):
        HybridConfig(gnfs_timeout_seconds=0)
    with pytest.raises(ValueError):
        HybridConfig(gnfs_timeout_seconds=-1)
    with pytest.raises(ValueError):
        HybridConfig(gnfs_timeout_seconds=86401)


# ---------------------------------------------------------------------------
# digit_threshold_bucket
# ---------------------------------------------------------------------------


def test_digit_threshold_bucket_small() -> None:
    """Verify bucket 0 for small inputs."""
    cfg = HybridConfig()
    assert cfg.digit_threshold_bucket((2**30).bit_length()) == 0
    assert cfg.digit_threshold_bucket(SMALL_INTEGER_BIT_BOUND) == 0


def test_digit_threshold_bucket_medium() -> None:
    """Verify bucket 1 for medium inputs."""
    cfg = HybridConfig()
    assert cfg.digit_threshold_bucket((2**50).bit_length()) == 1
    assert cfg.digit_threshold_bucket(MEDIUM_INTEGER_BIT_BOUND) == 1


def test_digit_threshold_bucket_large() -> None:
    """Verify bucket 2 for large inputs."""
    cfg = HybridConfig()
    assert cfg.digit_threshold_bucket((2**100).bit_length()) == 2
    assert cfg.digit_threshold_bucket(LARGE_INTEGER_BIT_BOUND) == 2


def test_digit_threshold_bucket_xlarge() -> None:
    """Verify bucket 3 for extra-large inputs."""
    cfg = HybridConfig()
    assert cfg.digit_threshold_bucket((2**200).bit_length()) == 3
    assert cfg.digit_threshold_bucket(XLARGE_INTEGER_BIT_BOUND) == 3


def test_digit_threshold_bucket_very_large() -> None:
    """Verify bucket 4 for very large inputs."""
    cfg = HybridConfig()
    assert cfg.digit_threshold_bucket((2**300).bit_length()) == 4
    assert cfg.digit_threshold_bucket(SIQS_INTEGER_BIT_BOUND) == 4


def test_digit_threshold_bucket_extreme() -> None:
    """Verify bucket 5 for extreme inputs."""
    cfg = HybridConfig()
    assert cfg.digit_threshold_bucket((2**400).bit_length()) == 5


# ---------------------------------------------------------------------------
# stages_for_threshold
# ---------------------------------------------------------------------------


def test_stages_for_threshold_small() -> None:
    """Verify stage order for bucket 0."""
    cfg = HybridConfig()
    order = cfg.stages_for_threshold(0)
    assert "trial_division" in order
    assert "pollard_rho" in order


def test_stages_for_threshold_medium() -> None:
    """Verify stage order for bucket 1."""
    cfg = HybridConfig()
    order = cfg.stages_for_threshold(1)
    assert "improved_pollard_pminus1" in order
    assert "pollard_rho" in order
    assert "ecm" in order


def test_stages_for_threshold_large() -> None:
    """Verify stage order for bucket 2."""
    cfg = HybridConfig()
    order = cfg.stages_for_threshold(2)
    assert "pollard_rho" in order
    assert "ecm" in order
    assert "improved_pollard_pminus1" in order


def test_stages_for_threshold_xlarge() -> None:
    """Verify stage order for bucket 3."""
    cfg = HybridConfig()
    order = cfg.stages_for_threshold(3)
    assert "ecm" in order
    assert "siqs" in order
    assert "pollard_rho" in order


def test_stages_for_threshold_very_large() -> None:
    """Verify stage order for bucket 4."""
    cfg = HybridConfig()
    order = cfg.stages_for_threshold(4)
    assert "siqs" in order
    assert "gnfs" in order


def test_stages_for_threshold_extreme() -> None:
    """Verify stage order for bucket 5."""
    cfg = HybridConfig()
    order = cfg.stages_for_threshold(5)
    assert "gnfs" in order


# ---------------------------------------------------------------------------
# HybridFactorisationState
# ---------------------------------------------------------------------------


def test_state_total_iterations() -> None:
    """Verify state tracks iterations."""
    cfg = HybridConfig()
    state = HybridFactorisationState(
        original_input=91,
        sign=1,
        composite_stack=[91],
        discovered_prime_factors=[],
        config=cfg,
        total_iterations=10,
    )
    assert state.total_iterations == 10
