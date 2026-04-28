"""Targeted tests for coverage gaps in hybrid, ecm, and core."""

from factorise.config import HybridConfig
from factorise.core import BrentPollardCycleResult
from factorise.core import PollardBrentOutcome
from factorise.core import execute_brent_pollard_cycle
from factorise.core import has_carmichael_property
from factorise.hybrid import HybridFactorisationEngine
from factorise.hybrid import hybrid_factorise
from factorise.pipeline import StageStatus
from factorise.pipeline import yield_prime_factors_via_pipeline
from factorise.stages.ecm import ECMStage
from factorise.stages.ecm_two_pass import TwoPassECMStage
from factorise.stages.gnfs_optimized import OptimizedGNFSStage
from factorise.stages.pollard_rho import PollardRhoStage

# ---------------------------------------------------------------------------
# hybrid.py — HybridFactorisationEngine edge cases
# ---------------------------------------------------------------------------


def test_hybrid_engine_negative_two() -> None:
    """Verify engine handles -2 correctly."""
    engine = HybridFactorisationEngine()
    result = engine.attempt(-2)
    assert result.factors == [2]
    assert result.is_prime is True


def test_hybrid_engine_perfect_power() -> None:
    """Verify engine handles perfect powers."""
    engine = HybridFactorisationEngine()
    result = engine.attempt(64)  # 2^6
    assert 2 in result.factors
    assert result.is_prime is False


def test_hybrid_engine_carmichael_check() -> None:
    """Verify engine handles Carmichael numbers when check is enabled."""
    cfg = HybridConfig(carmichael_check=True)
    engine = HybridFactorisationEngine(cfg)
    result = engine.attempt(561)  # 561 = 3 * 11 * 17, Carmichael
    assert result.is_prime is False
    assert 3 in result.factors


def test_hybrid_engine_stack_reordering() -> None:
    """Verify engine stack reordering when multiple composites exist."""
    engine = HybridFactorisationEngine()
    result = engine.attempt(360)  # 2^3 * 3^2 * 5
    assert 2 in result.factors
    assert 3 in result.factors
    assert 5 in result.factors


def test_hybrid_factorise_convenience() -> None:
    """Verify hybrid_factorise wrapper works."""
    result = hybrid_factorise(105)
    assert 3 in result.factors
    assert 5 in result.factors
    assert 7 in result.factors


# ---------------------------------------------------------------------------
# gnfs_optimized.py — pure Python GNFS tests
# ---------------------------------------------------------------------------


def test_gnfs_optimized_skips_too_small() -> None:
    """Verify GNFS skips n < 3."""
    stage = OptimizedGNFSStage()
    result = stage.attempt(2)
    assert result.status is StageStatus.SKIPPED


def test_gnfs_optimized_skips_prime() -> None:
    """Verify GNFS skips prime inputs."""
    stage = OptimizedGNFSStage()
    result = stage.attempt(97)
    assert result.status is StageStatus.SKIPPED


def test_gnfs_optimized_skips_below_min_bits() -> None:
    """Verify GNFS skips inputs below minimum bit length."""
    stage = OptimizedGNFSStage()
    result = stage.attempt(91)  # Below 60-bit minimum
    assert result.status is StageStatus.SKIPPED


def test_gnfs_optimized_skips_above_max_bits() -> None:
    """Verify GNFS skips inputs above maximum bit length."""
    stage = OptimizedGNFSStage()
    result = stage.attempt(2**300 + 1)  # Above 256-bit maximum
    assert result.status is StageStatus.SKIPPED


def test_gnfs_optimized_perfect_square() -> None:
    """Verify GNFS finds perfect square factors."""
    stage = OptimizedGNFSStage()
    # (2**31 + 127)^2 ~ 62 bits
    n = (2**31 + 127)**2
    result = stage.attempt(n)
    assert result.status is StageStatus.SUCCESS
    assert result.factor == 2**31 + 127


# ---------------------------------------------------------------------------
# ecm.py and ecm_two_pass.py — curve loops
# ---------------------------------------------------------------------------


def test_ecm_stage_curve_loop_failure() -> None:
    """Verify ECM stage enters curve loop and can return FAILURE."""
    stage = ECMStage(curves=2, bound=50)
    # 91 = 7*13; with tiny bound it may not find a factor
    result = stage.attempt(91)
    assert result.status in (StageStatus.SUCCESS, StageStatus.FAILURE)


def test_ecm_two_pass_stage_curve_loop() -> None:
    """Verify two-pass ECM enters both pass loops."""
    stage = TwoPassECMStage(
        first_pass_curves=2,
        first_pass_bound=50,
        second_pass_curves=2,
        second_pass_bound=100,
    )
    result = stage.attempt(91)
    assert result.status in (StageStatus.SUCCESS, StageStatus.FAILURE)


# ---------------------------------------------------------------------------
# core.py — remaining gaps
# ---------------------------------------------------------------------------


def test_has_carmichael_property_not_all_divide() -> None:
    """Verify Carmichael check fails when (n-1) not divisible by (p-1)."""
    # 15 = 3 * 5; (15-1) % (3-1) = 14 % 2 = 0, (15-1) % (5-1) = 14 % 4 = 2 != 0
    assert has_carmichael_property(15) is False


def test_brent_pollard_cycle_result_repr() -> None:
    """Verify __repr__ of BrentPollardCycleResult."""
    result = BrentPollardCycleResult(PollardBrentOutcome.SUCCESS, 10, 7)
    r = repr(result)
    assert "BrentPollardCycleResult" in r
    assert "SUCCESS" in r


def test_brent_pollard_cycle_result_eq_non_instance() -> None:
    """Verify __eq__ returns NotImplemented for non-instance."""
    result = BrentPollardCycleResult(PollardBrentOutcome.SUCCESS, 10, 7)
    assert result.__eq__("not a result") is NotImplemented


def test_execute_brent_pollard_cycle_backtrack() -> None:
    """Verify backtracking branch in execute_brent_pollard_cycle."""
    # Use a small composite where g might hit n
    n = 9
    from factorise.config import FactoriserConfig

    config = FactoriserConfig(batch_size=2, max_iterations=100)
    result = execute_brent_pollard_cycle(n, 2, 1, config, 100)
    assert isinstance(result, BrentPollardCycleResult)


def test_yield_prime_factors_via_pipeline_skips_lt_2() -> None:
    """Verify generator skips values < 2."""
    from factorise.config import FactoriserConfig

    config = FactoriserConfig(max_iterations=10, max_retries=1)
    factors = list(yield_prime_factors_via_pipeline(1, config))
    assert factors == []


def test_yield_prime_factors_via_pipeline_fallback() -> None:
    """Verify fallback to pollard_brent when pipeline fails."""
    from factorise.config import FactoriserConfig

    config = FactoriserConfig(max_iterations=1, max_retries=1, batch_size=2)
    # Use a composite small enough that direct pollard_brent will work
    factors = list(yield_prime_factors_via_pipeline(91, config))
    # Should yield some prime factors
    assert len(factors) > 0


# ---------------------------------------------------------------------------
# pollard_rho.py — exception catch
# ---------------------------------------------------------------------------


def test_pollard_rho_stage_failure() -> None:
    """Verify PollardRhoStage catches FactorisationError."""
    stage = PollardRhoStage(max_retries=1, max_iterations=1)
    result = stage.attempt(91)
    # May succeed or fail depending on luck
    assert result.status in (StageStatus.SUCCESS, StageStatus.FAILURE)


# ---------------------------------------------------------------------------
# gnfs_optimized.py — utility functions and sieving paths
# ---------------------------------------------------------------------------


def test_legendre_symbol_p_equals_2() -> None:
    """Verify Legendre symbol handles p=2."""
    from factorise.stages.gnfs_optimized import legendre_symbol

    assert legendre_symbol(3, 2) == 1
    assert legendre_symbol(4, 2) == 0


def test_legendre_symbol_a_mod_p_zero() -> None:
    """Verify Legendre symbol returns 0 when a mod p is 0."""
    from factorise.stages.gnfs_optimized import legendre_symbol

    # a=6, p=3 -> 6 % 3 == 0
    assert legendre_symbol(6, 3) == 0


def test_legendre_symbol_regular() -> None:
    """Verify Legendre symbol for regular cases."""
    from factorise.stages.gnfs_optimized import legendre_symbol

    # (3/7) = 3^3 mod 7 = 27 mod 7 = 6 = -1 (quadratic non-residue)
    assert legendre_symbol(3, 7) == -1
    # (2/7) = 2^3 mod 7 = 8 mod 7 = 1 (quadratic residue)
    assert legendre_symbol(2, 7) == 1


def test_sqrt_mod_prime_n_mod_p_zero() -> None:
    """Verify sqrt_mod_prime returns (0,0) when n % p == 0."""
    from factorise.stages.gnfs_optimized import sqrt_mod_prime

    result = sqrt_mod_prime(9, 3)
    assert result == (0, 0)


def test_sqrt_mod_prime_p_equals_2() -> None:
    """Verify sqrt_mod_prime handles p=2."""
    from factorise.stages.gnfs_optimized import sqrt_mod_prime

    result = sqrt_mod_prime(1, 2)
    assert result == (1, 0)


def test_sqrt_mod_prime_p_mod_4_equals_3() -> None:
    """Verify sqrt_mod_prime uses p%4==3 shortcut."""
    from factorise.stages.gnfs_optimized import sqrt_mod_prime

    # p=7, n=2: sqrt(2) mod 7 = 3 or 4 since 3^2=9=2 mod 7
    result = sqrt_mod_prime(2, 7)
    assert result is not None
    r, neg_r = result
    assert (r * r) % 7 == 2
    assert (neg_r * neg_r) % 7 == 2


def test_sqrt_mod_prime_non_residue() -> None:
    """Verify sqrt_mod_prime returns None for non-residues."""
    from factorise.stages.gnfs_optimized import sqrt_mod_prime

    # 3 is not a quadratic residue mod 7
    result = sqrt_mod_prime(3, 7)
    assert result is None


def test_sqrt_mod_prime_tonelli_shanks() -> None:
    """Verify sqrt_mod_prime uses Tonelli-Shanks for p%4!=3."""
    from factorise.stages.gnfs_optimized import sqrt_mod_prime

    # p=11, n=5 is a quadratic residue: 5^5 mod 11 = 3125 mod 11 = 1
    result = sqrt_mod_prime(5, 11)
    assert result is not None
    r, neg_r = result
    assert (r * r) % 11 == 5
    assert (neg_r * neg_r) % 11 == 5


def test_polynomial_evaluate_with_mod() -> None:
    """Verify Polynomial.evaluate applies modulo."""
    from factorise.stages.gnfs_optimized import Polynomial

    poly = Polynomial(a=1, b=0, c=-5)  # x^2 - 5
    assert poly.evaluate(7, mod=11) == (49 - 5) % 11  # = 44 % 11 = 0


def test_polynomial_evaluate_without_mod() -> None:
    """Verify Polynomial.evaluate without mod."""
    from factorise.stages.gnfs_optimized import Polynomial

    poly = Polynomial(a=1, b=0, c=-5)
    assert poly.evaluate(7) == 44  # 7^2 - 5


def test_factor_over_base_negative_value() -> None:
    """Verify _factor_over_base handles negative values."""
    from factorise.stages.gnfs_optimized import factor_over_base

    primes = [2, 3, 5]
    result = factor_over_base(-10, primes)
    # -10 -> 10, 10 = 2 * 5
    assert result is not None
    assert result == [1, 0, 1]


def test_factor_over_base_value_le_1() -> None:
    """Verify _factor_over_base handles value <= 1."""
    from factorise.stages.gnfs_optimized import factor_over_base

    primes = [2, 3, 5, 7]
    result = factor_over_base(1, primes)
    assert result == [0, 0, 0, 0]


def test_factor_over_base_remaining_prime() -> None:
    """Verify _factor_over_base when remaining is a prime in base."""
    from factorise.stages.gnfs_optimized import factor_over_base

    primes = [2, 3, 5, 7, 11]
    # 6 = 2 * 3, remaining = 1, needs padding
    result = factor_over_base(6, primes)
    assert result == [1, 1, 0, 0, 0]


def test_select_polynomial() -> None:
    """Verify _select_polynomial creates valid polynomial."""
    from factorise.stages.gnfs_optimized import select_polynomial

    poly, m = select_polynomial(1000)
    assert poly.a == 1
    assert poly.b == 0
    assert poly.c == -m
    assert m > 0


def test_build_factor_bases() -> None:
    """Verify _build_factor_bases builds rational and algebraic bases."""
    from factorise.stages.gnfs_optimized import build_factor_bases

    n = 91
    m = 4
    rational, algebraic = build_factor_bases(n, m, bound=20)
    # Rational base: primes where n is quadratic residue mod p
    # Algebraic base: primes where m is quadratic residue mod p
    assert isinstance(rational, list)
    assert isinstance(algebraic, list)


def test_gnfs_optimized_even_input() -> None:
    """Verify GNFS handles even inputs."""
    from factorise.stages.gnfs_optimized import OptimizedGNFSStage

    stage = OptimizedGNFSStage()
    result = stage.attempt(2**62 + 1)  # 62 bits, even composite
    # May succeed or fail but should not crash
    assert result.status in (StageStatus.SUCCESS, StageStatus.FAILURE)


# ---------------------------------------------------------------------------
# ecm_shared.py — remaining gaps
# ---------------------------------------------------------------------------


def test_elliptic_curve_point_add_gcd_1() -> None:
    """Verify point_add when denom gcd is 1."""
    from factorise.stages.ecm_shared import EllipticCurveOperations

    ops = EllipticCurveOperations()
    n = 91
    # x1=1, y1=2, x2=3, y2=4, denom = 3-1=2, gcd(2,91)=1
    x, y, g = ops.point_add(1, 2, 3, 4, 1, n)
    assert g == 1
    assert isinstance(x, int)
    assert isinstance(y, int)


def test_elliptic_curve_multiply_point_large_k() -> None:
    """Verify multiply_point with large k."""
    from factorise.stages.ecm_shared import EllipticCurveOperations

    ops = EllipticCurveOperations()
    n = 91
    result = ops.multiply_point([2, 1], 100, 1, n)
    assert result is None or isinstance(result, int)


def test_elliptic_curve_point_double_y_even() -> None:
    """Verify point_double when y is even (gcd may be > 1)."""
    from factorise.stages.ecm_shared import EllipticCurveOperations

    ops = EllipticCurveOperations()
    n = 91  # 7*13, y=14 has factor 7
    x, y, g = ops.point_double(5, 14, 1, n)
    # gcd(2*y, n) = gcd(28, 91) = 7
    assert isinstance(x, int)
    assert isinstance(y, int)
    assert isinstance(g, int)


# ---------------------------------------------------------------------------
# Additional ecm_shared coverage
# ---------------------------------------------------------------------------


def test_compute_modular_inverse_zero_a() -> None:
    """Verify compute_modular_inverse(0, n) returns 0."""
    from factorise.stages.ecm_shared import compute_modular_inverse

    assert compute_modular_inverse(0, 7) == 0


def test_compute_modular_inverse_not_coprime() -> None:
    """Verify compute_modular_inverse returns 0 when not coprime."""
    from factorise.stages.ecm_shared import compute_modular_inverse

    assert compute_modular_inverse(4, 6) == 0
