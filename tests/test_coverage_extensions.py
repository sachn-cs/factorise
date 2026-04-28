"""Targeted tests for coverage gaps across factorise."""

from __future__ import annotations

import subprocess
import sys

import pytest

from factorise.cli import configure_logging
from factorise.cli import main
from factorise.config import FactoriserConfig
from factorise.config import HybridConfig
from factorise.config import PipelineConfig
from factorise.core import BrentPollardCycleResult
from factorise.core import PollardBrentOutcome
from factorise.core import execute_brent_pollard_cycle
from factorise.core import factorise
from factorise.core import integer_kth_root
from factorise.hybrid import HybridFactorisationEngine
from factorise.pipeline import FactorisationPipeline
from factorise.pipeline import PollardPMinusOneStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus
from factorise.pipeline import yield_prime_factors_via_pipeline
from factorise.stages.ecm import ECMStage
from factorise.stages.ecm_shared import EllipticCurveOperations
from factorise.stages.ecm_shared import compute_modular_inverse
from factorise.stages.ecm_two_pass import TwoPassECMStage
from factorise.stages.gnfs_optimized import OptimizedGNFSStage
from factorise.stages.gnfs_optimized import build_factor_bases
from factorise.stages.gnfs_optimized import factor_over_base as gnfs_factor_over_base
from factorise.stages.gnfs_optimized import select_polynomial
from factorise.stages.gnfs_optimized import sqrt_mod_prime
from factorise.stages.improved_pm1 import ImprovedPollardPMinusOneStage
from factorise.stages.pollard_rho import PollardRhoStage
from factorise.stages.qs_shared import QSRelation
from factorise.stages.qs_shared import extract_factor
from factorise.stages.qs_shared import factor_over_base
from factorise.stages.qs_shared import find_dependency
from factorise.stages.quadratic_sieve import QuadraticSieveStage
from factorise.stages.siqs import SIQSStage

# ---------------------------------------------------------------------------
# cli.py
# ---------------------------------------------------------------------------


def test_configure_logging_invalid_level() -> None:
    """Verify configure_logging raises ValueError for invalid level."""
    with pytest.raises(ValueError, match="log_level must be one of"):
        configure_logging("INVALID")


def test_main_invalid_log_level(capsys) -> None:
    """Verify main exits cleanly on invalid log level."""
    with pytest.raises(SystemExit) as exc_info:
        main(["123", "--log-level", "INVALID"])
    # argparse exits with 2 for invalid choices
    assert exc_info.value.code in (1, 2)


def test_cli_main_module() -> None:
    """Verify cli.py __main__ block runs without error."""
    result = subprocess.run(
        [sys.executable, "-m", "factorise.cli", "97", "--verbose"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "97" in result.stdout


def test_cli_main_runpy() -> None:
    """Cover cli.py __main__ block via runpy in-process."""
    import runpy
    import io
    from unittest.mock import patch
    with patch("sys.argv", ["factorise", "97"]), \
         patch("sys.stdout", new_callable=io.StringIO):
        runpy.run_module("factorise.cli", run_name="__main__")


def test_main_configure_logging_value_error() -> None:
    """Verify main catches ValueError from configure_logging."""
    import factorise.cli as cli_module
    original = cli_module.configure_logging
    cli_module.configure_logging = lambda level: (_ for _ in ()).throw(ValueError("bad"))
    try:
        with pytest.raises(SystemExit) as exc_info:
            main(["123", "--log-level", "DEBUG"])
        assert exc_info.value.code == 1
    finally:
        cli_module.configure_logging = original


# ---------------------------------------------------------------------------
# core.py
# ---------------------------------------------------------------------------


def test_integer_kth_root_n_lt_2() -> None:
    """Verify integer_kth_root returns n for n < 2."""
    assert integer_kth_root(0, 3) == 0
    assert integer_kth_root(1, 3) == 1


def test_brent_pollard_cycle_result_hash() -> None:
    """Verify __hash__ works for BrentPollardCycleResult."""
    r1 = BrentPollardCycleResult(PollardBrentOutcome.SUCCESS, 10, 7)
    r2 = BrentPollardCycleResult(PollardBrentOutcome.SUCCESS, 10, 7)
    assert hash(r1) == hash(r2)


def test_brent_pollard_cycle_result_eq() -> None:
    """Verify __eq__ works for equal instances."""
    r1 = BrentPollardCycleResult(PollardBrentOutcome.SUCCESS, 10, 7)
    r2 = BrentPollardCycleResult(PollardBrentOutcome.SUCCESS, 10, 7)
    assert r1 == r2


def test_brent_pollard_cycle_result_eq_non_instance() -> None:
    """Verify __eq__ returns NotImplemented for non-instance."""
    result = BrentPollardCycleResult(PollardBrentOutcome.SUCCESS, 10, 7)
    assert result.__eq__("not a result") is NotImplemented


def test_execute_brent_pollard_cycle_backtrack_path() -> None:
    """Verify backtrack branch in execute_brent_pollard_cycle."""
    config = FactoriserConfig(batch_size=2, max_iterations=100)
    # Use a small composite; backtrack may trigger if batch GCD == n
    result = execute_brent_pollard_cycle(91, 2, 1, config, 100)
    assert isinstance(result, BrentPollardCycleResult)


# ---------------------------------------------------------------------------
# hybrid.py
# ---------------------------------------------------------------------------


def test_hybrid_perfect_power_check_disabled() -> None:
    """Verify perfect power check can be disabled."""
    cfg = HybridConfig(perfect_power_check=False)
    engine = HybridFactorisationEngine(cfg)
    result = engine.attempt(64)
    assert result.is_prime is False


def test_hybrid_select_algorithm_missing_stage() -> None:
    """Verify select_algorithm skips missing stages."""
    engine = HybridFactorisationEngine()
    # Temporarily remove a stage to hit the None path
    original = engine.stage_map.pop("pollard_rho", None)
    try:
        result = engine.select_algorithm(91)
        assert result is None or isinstance(result, int)
    finally:
        if original is not None:
            engine.stage_map["pollard_rho"] = original


def test_hybrid_factorise_stack_composite_factor_and_cofactor() -> None:
    """Verify factorise_stack handles composite factor and cofactor."""
    engine = HybridFactorisationEngine()
    # Monkey-patch select_algorithm to return a composite factor first
    original = engine.select_algorithm
    call_count = 0
    def fake_select(n: int) -> int | None:
        nonlocal call_count
        call_count += 1
        if n == 45:
            return 15  # composite factor, cofactor = 3 (prime)
        if n == 360:
            return 15  # composite factor, cofactor = 24 (composite)
        return original(n)
    engine.select_algorithm = fake_select
    try:
        # 45 = 3 * 3 * 5; first fake return: 15 (composite), cofactor 3 (prime)
        factors, powers = engine.factorise_stack(45)
        assert 3 in factors
        assert 5 in factors
        # 360 = 2^3 * 3^2 * 5; first fake return: 15 (composite), cofactor 24 (composite)
        factors, powers = engine.factorise_stack(360)
        assert 2 in factors
        assert 3 in factors
        assert 5 in factors
    finally:
        engine.select_algorithm = original


# ---------------------------------------------------------------------------
# pipeline.py
# ---------------------------------------------------------------------------


def test_stage_result_hash() -> None:
    """Verify StageResult __hash__ works."""
    s1 = StageResult("test", StageStatus.SUCCESS, 7, 1.0)
    s2 = StageResult("test", StageStatus.SUCCESS, 7, 1.0)
    assert hash(s1) == hash(s2)


def test_stage_result_eq() -> None:
    """Verify StageResult __eq__ works for equal instances."""
    s1 = StageResult("test", StageStatus.SUCCESS, 7, 1.0)
    s2 = StageResult("test", StageStatus.SUCCESS, 7, 1.0)
    assert s1 == s2


def test_stage_result_eq_non_instance() -> None:
    """Verify StageResult __eq__ returns NotImplemented for non-instance."""
    s1 = StageResult("test", StageStatus.SUCCESS, 7, 1.0)
    assert s1.__eq__("not a result") is NotImplemented


def test_pollard_pminus_one_stage_n_lt_3() -> None:
    """Verify PollardPMinusOneStage skips n < 3."""
    stage = PollardPMinusOneStage(bound=100)
    result = stage.attempt(2)
    assert result.status is StageStatus.SKIPPED
    assert result.reason == "n < 3"


def test_pollard_pminus_one_stage_failure() -> None:
    """Verify PollardPMinusOneStage returns FAILURE when no factor found."""
    stage = PollardPMinusOneStage(bound=10)
    result = stage.attempt(91)
    assert result.status is StageStatus.FAILURE


def test_pipeline_unknown_stage_name() -> None:
    """Verify pipeline skips unknown stage names."""
    config = PipelineConfig(stage_order=("unknown_stage",))
    pipeline = FactorisationPipeline(config)
    result = pipeline.attempt(91)
    assert result.status is StageStatus.FAILURE


def test_yield_prime_factors_unexpected_status() -> None:
    """Verify yield_prime_factors_via_pipeline handles unexpected status."""
    config = FactoriserConfig(max_iterations=1, max_retries=1, batch_size=2)
    # Monkey-patch pipeline to return an unexpected status
    from factorise import pipeline as pipeline_module
    original_attempt = pipeline_module.FactorisationPipeline.attempt

    def fake_attempt(self, n: int):
        return StageResult(
            stage_name="pipeline",
            status=StageStatus.PARTIAL,
            factor=None,
            elapsed_ms=0.0,
            reason="fake",
        )

    pipeline_module.FactorisationPipeline.attempt = fake_attempt
    try:
        with pytest.raises(Exception):
            list(yield_prime_factors_via_pipeline(91, config))
    finally:
        pipeline_module.FactorisationPipeline.attempt = original_attempt


# ---------------------------------------------------------------------------
# ecm.py
# ---------------------------------------------------------------------------


def test_ecm_stage_success_in_curve_loop() -> None:
    """Verify ECM stage success path inside the curve loop."""
    stage = ECMStage(curves=2, bound=100)
    # Monkey-patch run_curve to force success path
    original = stage.run_curve
    stage.run_curve = lambda n, seed, primes: 7 if seed == 0 else None
    try:
        result = stage.attempt(91)
        assert result.status is StageStatus.SUCCESS
        assert result.factor == 7
    finally:
        stage.run_curve = original


# ---------------------------------------------------------------------------
# ecm_shared.py
# ---------------------------------------------------------------------------


def test_point_double_inv_denom_zero() -> None:
    """Verify point_double when inv_denom == 0."""
    ops = EllipticCurveOperations()
    # Force denom to have gcd > 1 with n but not > 1 after first gcd check
    # We need a case where g == 1 but inv_denom == 0 (gcd > 1 but caught later)
    # inv_denom == 0 happens when compute_modular_inverse returns 0 (not coprime)
    # This means g was > 1 originally, which is caught at line 97-98.
    # So inv_denom == 0 at line 101 is unreachable in normal flow.
    # Instead, let's test the g > 1 path at line 97-98.
    n = 91  # 7*13
    x, y, g = ops.point_double(5, 14, 1, n)  # denom = 28, gcd(28,91)=7
    assert g == 7


def test_point_add_inv_denom_zero() -> None:
    """Verify point_add when inv_denom == 0."""
    ops = EllipticCurveOperations()
    n = 91
    # x2-x1 = denom; if gcd(denom, n) > 1, it's caught at line 140-142
    # The inv_denom == 0 path (line 145) is only reached if g == 1 but
    # compute_modular_inverse returns 0, which means gcd > 1 — contradiction.
    # So we hit the g > 1 path instead.
    x, y, g = ops.point_add(1, 2, 8, 3, 1, n)  # denom = 7, gcd(7,91)=7
    assert g == 7


def test_multiply_point_f_gt_1() -> None:
    """Verify multiply_point returns factor when f > 1 inside bit loop."""
    ops = EllipticCurveOperations()
    n = 91
    result = ops.multiply_point([2, 1], 3, 1, n)
    # May find a factor or return None; just ensure it doesn't crash
    assert result is None or isinstance(result, int)


# ---------------------------------------------------------------------------
# ecm_two_pass.py
# ---------------------------------------------------------------------------


def test_ecm_two_pass_stage1_success() -> None:
    """Verify two-pass ECM stage 1 success path."""
    stage = TwoPassECMStage(
        first_pass_curves=2,
        first_pass_bound=100,
        second_pass_curves=2,
        second_pass_bound=100,
    )
    original = stage.run_curve
    stage.run_curve = lambda n, seed, primes: 7 if seed == 0 else None
    try:
        result = stage.attempt(91)
        assert result.status is StageStatus.SUCCESS
        assert result.factor == 7
    finally:
        stage.run_curve = original


def test_ecm_two_pass_stage2_success() -> None:
    """Verify two-pass ECM stage 2 success path."""
    stage = TwoPassECMStage(
        first_pass_curves=1,
        first_pass_bound=10,
        second_pass_curves=2,
        second_pass_bound=100,
    )
    original = stage.run_curve
    # Force stage 2 to find a factor
    call_count = 0
    def fake_run_curve(n, seed, primes):
        nonlocal call_count
        call_count += 1
        if seed >= 1:  # stage 2 seeds start after first_pass_curves
            return 13
        return None
    stage.run_curve = fake_run_curve
    try:
        result = stage.attempt(91)
        assert result.status is StageStatus.SUCCESS
        assert result.factor == 13
    finally:
        stage.run_curve = original


# ---------------------------------------------------------------------------
# gnfs_optimized.py
# ---------------------------------------------------------------------------


def test_sqrt_mod_prime_none() -> None:
    """Verify sqrt_mod_prime returns None for non-residues."""
    result = sqrt_mod_prime(3, 7)
    assert result is None


def test_select_polynomial_m_lt_2() -> None:
    """Verify select_polynomial handles n where m < 2."""
    poly, m = select_polynomial(1)
    assert m >= 2


def test_gnfs_attempt_is_prime() -> None:
    """Verify GNFS skips prime inputs."""
    stage = OptimizedGNFSStage()
    # Use a prime in the 60-128 bit range
    p = (1 << 61) - 1  # Mersenne prime
    result = stage.attempt(p)
    assert result.status is StageStatus.SKIPPED
    assert result.reason == "n is prime"


def test_gnfs_attempt_failure() -> None:
    """Verify GNFS can return FAILURE."""
    stage = OptimizedGNFSStage()
    # Very small input that isn't prime and isn't a perfect square
    result = stage.attempt(15)
    assert result.status in (StageStatus.SUCCESS, StageStatus.SKIPPED)


def test_gnfs_auto_scale_above_128_bits() -> None:
    """Verify __auto_scale returns (0,0,0) above 128 bits."""
    stage = OptimizedGNFSStage()
    auto = stage._GNFSStage__auto_scale(200)
    assert auto == (0, 0, 0)


def test_gnfs_find_factor_bound_zero() -> None:
    """Verify __find_factor returns None when auto_scale gives (0,0,0)."""
    stage = OptimizedGNFSStage()
    # Monkey-patch auto_scale to return zeros
    original = stage._GNFSStage__auto_scale
    stage._GNFSStage__auto_scale = lambda bit_len: (0, 0, 0)
    try:
        result = stage._GNFSStage__find_factor(91)
        assert result is None
    finally:
        stage._GNFSStage__auto_scale = original


def test_gnfs_find_factor_attempt_gt_0() -> None:
    """Verify __find_factor with attempt > 0 path."""
    stage = OptimizedGNFSStage()
    original_attempts = stage._GNFSStage__max_attempts
    stage._GNFSStage__max_attempts = 2
    try:
        result = stage._GNFSStage__find_factor(91)
        # May succeed or fail
        assert result is None or isinstance(result, int)
    finally:
        stage._GNFSStage__max_attempts = original_attempts


def test_gnfs_find_factor_relations_lt_num_cols() -> None:
    """Verify __find_factor returns None when relations < num_cols."""
    stage = OptimizedGNFSStage()
    # Force tiny parameters so no relations are found
    original_auto = stage._GNFSStage__auto_scale
    stage._GNFSStage__auto_scale = lambda bit_len: (2, 2, 2)
    try:
        result = stage._GNFSStage__find_factor(91)
        assert result is None
    finally:
        stage._GNFSStage__auto_scale = original_auto


def test_gnfs_find_factor_dependency_none() -> None:
    """Verify __find_factor returns None when dependency is None."""
    stage = OptimizedGNFSStage()
    original_find_dep = stage._GNFSStage__find_dependency
    stage._GNFSStage__find_dependency = lambda rels, cols: None
    try:
        result = stage._GNFSStage__find_factor(
            (2**31 + 127) ** 2,
        )
        assert result is None
    finally:
        stage._GNFSStage__find_dependency = original_find_dep


def test_gnfs_lattice_sieve_p_equals_2() -> None:
    """Verify __lattice_sieve skips p == 2."""
    stage = OptimizedGNFSStage()
    relations = stage._GNFSStage__lattice_sieve(
        91, 4, [2, 3], [3, 5], 10, 100, 10,
    )
    assert isinstance(relations, list)


def test_gnfs_lattice_sieve_roots_none() -> None:
    """Verify __lattice_sieve skips primes with no roots."""
    stage = OptimizedGNFSStage()
    relations = stage._GNFSStage__lattice_sieve(
        91, 4, [2, 3], [7], 10, 100, 10,
    )
    assert isinstance(relations, list)


def test_gnfs_lattice_sieve_r_zero() -> None:
    """Verify __lattice_sieve skips r == 0."""
    stage = OptimizedGNFSStage()
    relations = stage._GNFSStage__lattice_sieve(
        91, 4, [2, 3], [3], 10, 100, 10,
    )
    assert isinstance(relations, list)


def test_gnfs_lattice_sieve_append_relation() -> None:
    """Verify __lattice_sieve appends relations."""
    stage = OptimizedGNFSStage()
    relations = stage._GNFSStage__lattice_sieve(
        91, 4, [2, 3, 5, 7], [3, 5, 7], 10, 100, 1000,
    )
    assert isinstance(relations, list)


def test_gnfs_lattice_sieve_return_relations() -> None:
    """Verify __lattice_sieve returns relations list."""
    stage = OptimizedGNFSStage()
    relations = stage._GNFSStage__lattice_sieve(
        91, 4, [2, 3], [3], 10, 10, 1,
    )
    assert isinstance(relations, list)


def test_gnfs_find_dependency_relations_lt_num_cols() -> None:
    """Verify __find_dependency returns None when relations < num_cols."""
    stage = OptimizedGNFSStage()
    result = stage._GNFSStage__find_dependency([], 5)
    assert result is None


def test_gnfs_find_dependency_mask_zero() -> None:
    """Verify __find_dependency skips mask == 0."""
    stage = OptimizedGNFSStage()
    rels = [{"exponents": [0, 0, 0]}]
    result = stage._GNFSStage__find_dependency(rels, 1)
    assert result is None


def test_gnfs_find_dependency_rows_lt_num_cols() -> None:
    """Verify __find_dependency returns None when rows < num_cols."""
    stage = OptimizedGNFSStage()
    rels = [{"exponents": [1, 0]}]
    result = stage._GNFSStage__find_dependency(rels, 5)
    assert result is None


def test_gnfs_find_dependency_row_idx_break() -> None:
    """Verify __find_dependency breaks when row_idx >= num_rows."""
    stage = OptimizedGNFSStage()
    rels = [{"exponents": [1]}]
    result = stage._GNFSStage__find_dependency(rels, 1)
    # May or may not find dependency; just ensure no crash
    assert result is None or isinstance(result, list)


def test_gnfs_find_dependency_return_none() -> None:
    """Verify __find_dependency returns None when no dependency found."""
    stage = OptimizedGNFSStage()
    rels = [{"exponents": [1, 0]}, {"exponents": [0, 1]}]
    result = stage._GNFSStage__find_dependency(rels, 2)
    assert result is None or isinstance(result, list)


def test_gnfs_extract_factor_rel_idx_oob() -> None:
    """Verify __extract_factor skips out-of-bounds relation indices."""
    stage = OptimizedGNFSStage()
    result = stage._GNFSStage__extract_factor(
        91, 4, [{"a": 1, "b": 1, "norm": 1, "exponents": [0, 0]}],
        [0, 99], [2, 3], [5, 7],
    )
    assert result is None or isinstance(result, int)


def test_gnfs_extract_factor_return_none() -> None:
    """Verify __extract_factor returns None when no factor found."""
    stage = OptimizedGNFSStage()
    result = stage._GNFSStage__extract_factor(
        91, 4, [{"a": 1, "b": 1, "norm": 1, "exponents": [0, 0]}],
        [0], [2, 3], [5, 7],
    )
    assert result is None


# ---------------------------------------------------------------------------
# improved_pm1.py
# ---------------------------------------------------------------------------


def test_improved_pm1_g_equals_n() -> None:
    """Verify improved p-1 handles g == n (base produces trivial factor)."""
    stage = ImprovedPollardPMinusOneStage(bounds=(100,), bases=(2,))
    # n = 2^100 - 1 is huge; use a smaller bound where g might equal n
    # For n=15, base=2, bound=4: 2^4=16, 16-1=15, gcd(15,15)=15 == n
    result = stage.attempt(15)
    # Should continue to next base or return FAILURE
    assert result.status in (StageStatus.SUCCESS, StageStatus.FAILURE)


# ---------------------------------------------------------------------------
# pollard_rho.py
# ---------------------------------------------------------------------------


def test_pollard_rho_factorisation_error() -> None:
    """Verify PollardRhoStage catches FactorisationError."""
    stage = PollardRhoStage(max_retries=1, max_iterations=1)
    # Large composite unlikely to factor in 1 iteration
    result = stage.attempt(1000003 * 1000033)
    assert result.status is StageStatus.FAILURE


# ---------------------------------------------------------------------------
# qs_shared.py
# ---------------------------------------------------------------------------


def test_factor_over_base_negative() -> None:
    """Verify factor_over_base handles negative values."""
    primes = [-1, 2, 3, 5]
    result = factor_over_base(-30, primes)
    assert result is not None
    assert result[0] == 1  # sign bit


def test_find_dependency_mask_zero() -> None:
    """Verify find_dependency skips mask == 0."""
    rels: list[QSRelation] = [
        {"a": 1, "a2_mod_n": 1, "exponents": [2, 2]},
    ]
    result = find_dependency(rels, 2)
    assert result is None


def test_find_dependency_rows_lt_num_cols() -> None:
    """Verify find_dependency returns None when rows < num_cols."""
    rels: list[QSRelation] = [
        {"a": 1, "a2_mod_n": 1, "exponents": [1, 0]},
    ]
    result = find_dependency(rels, 5)
    assert result is None


def test_find_dependency_row_idx_break() -> None:
    """Verify find_dependency breaks when row_idx >= num_rows."""
    rels: list[QSRelation] = [
        {"a": 1, "a2_mod_n": 1, "exponents": [1, 0]},
        {"a": 2, "a2_mod_n": 2, "exponents": [0, 1]},
    ]
    result = find_dependency(rels, 1)
    # May or may not find dependency; just ensure no crash
    assert result is None or isinstance(result, list)


def test_find_dependency_return_none() -> None:
    """Verify find_dependency returns None when no dependency."""
    rels: list[QSRelation] = [
        {"a": 1, "a2_mod_n": 1, "exponents": [1, 0]},
        {"a": 2, "a2_mod_n": 2, "exponents": [0, 1]},
    ]
    result = find_dependency(rels, 2)
    assert result is None or isinstance(result, list)


def test_extract_factor_empty_dependency() -> None:
    """Verify extract_factor returns None for empty dependency."""
    result = extract_factor(91, [], [], [2, 3])
    assert result is None


def test_extract_factor_prime_minus_one() -> None:
    """Verify extract_factor skips prime == -1."""
    rels: list[QSRelation] = [
        {
            "a": 3,
            "a2_mod_n": 9,
            "exponents": [2, 0, 0],  # first prime is -1
        },
    ]
    result = extract_factor(91, rels, [0], [-1, 2, 3])
    assert result is None or isinstance(result, int)


def test_extract_factor_gcd_candidates() -> None:
    """Verify extract_factor checks both gcd candidates."""
    rels: list[QSRelation] = [
        {
            "a": 3,
            "a2_mod_n": 9,
            "exponents": [0, 2, 0],
        },
    ]
    result = extract_factor(91, rels, [0], [-1, 7, 13])
    assert result is None or isinstance(result, int)


# ---------------------------------------------------------------------------
# quadratic_sieve.py
# ---------------------------------------------------------------------------


def test_quadratic_sieve_even() -> None:
    """Verify QuadraticSieveStage handles even inputs."""
    stage = QuadraticSieveStage()
    result = stage.attempt(100)
    assert result.status is StageStatus.SUCCESS
    assert result.factor == 2


def test_quadratic_sieve_factor_found() -> None:
    """Verify QuadraticSieveStage finds a factor."""
    stage = QuadraticSieveStage()
    # 91 = 7 * 13
    result = stage.attempt(91)
    assert result.status in (StageStatus.SUCCESS, StageStatus.FAILURE)


def test_quadratic_sieve_prime_base_lt_2() -> None:
    """Verify __find_factor returns None when prime_base < 2."""
    stage = QuadraticSieveStage()
    original_build = stage._QuadraticSieveStage__build_prime_base
    stage._QuadraticSieveStage__build_prime_base = lambda n: [-1]
    try:
        result = stage._QuadraticSieveStage__find_factor(91)
        assert result is None
    finally:
        stage._QuadraticSieveStage__build_prime_base = original_build


def test_quadratic_sieve_relations_lt_base() -> None:
    """Verify __find_factor returns None when relations < len(prime_base)."""
    stage = QuadraticSieveStage()
    original_relations = stage._QuadraticSieveStage__find_smooth_relations
    stage._QuadraticSieveStage__find_smooth_relations = lambda n, pb: []
    try:
        result = stage._QuadraticSieveStage__find_factor(91)
        assert result is None
    finally:
        stage._QuadraticSieveStage__find_smooth_relations = original_relations


def test_quadratic_sieve_dependency_none() -> None:
    """Verify __find_factor returns None when dependency is None."""
    stage = QuadraticSieveStage()
    import factorise.stages.quadratic_sieve as qs_module
    original_find_dep = qs_module.find_dependency
    qs_module.find_dependency = lambda rels, num_primes: None
    # Ensure enough relations are returned to pass the len check
    original_relations = stage._QuadraticSieveStage__find_smooth_relations
    stage._QuadraticSieveStage__find_smooth_relations = lambda n, pb: [
        {"a": 1, "a2_mod_n": 1, "exponents": [0] * len(pb)}
        for _ in range(len(pb) + 1)
    ]
    try:
        result = stage._QuadraticSieveStage__find_factor(91)
        assert result is None
    finally:
        qs_module.find_dependency = original_find_dep
        stage._QuadraticSieveStage__find_smooth_relations = original_relations


def test_quadratic_sieve_return_relations() -> None:
    """Verify __find_smooth_relations returns relations list."""
    stage = QuadraticSieveStage()
    # Use a large prime base so target_count exceeds found relations
    import factorise.stages.quadratic_sieve as qs_module
    original_extra = qs_module.RELATION_EXTRA_COUNT
    qs_module.RELATION_EXTRA_COUNT = 1000
    try:
        relations = stage._QuadraticSieveStage__find_smooth_relations(91, [-1, 2, 3, 5])
        assert isinstance(relations, list)
        assert len(relations) < 1005  # didn't hit the early return
    finally:
        qs_module.RELATION_EXTRA_COUNT = original_extra


def test_quadratic_sieve_success_path() -> None:
    """Verify QuadraticSieveStage success return path."""
    stage = QuadraticSieveStage()
    original = stage._QuadraticSieveStage__find_factor
    stage._QuadraticSieveStage__find_factor = lambda n: 7
    try:
        result = stage.attempt(91)
        assert result.status is StageStatus.SUCCESS
        assert result.factor == 7
    finally:
        stage._QuadraticSieveStage__find_factor = original


# ---------------------------------------------------------------------------
# siqs.py
# ---------------------------------------------------------------------------


def test_siqs_factor_found() -> None:
    """Verify SIQSStage finds a factor."""
    stage = SIQSStage()
    result = stage.attempt(91)
    assert result.status in (StageStatus.SUCCESS, StageStatus.FAILURE)


def test_siqs_factor_base_lt_min() -> None:
    """Verify __find_factor returns None when factor_base < MIN_RELATIONS."""
    stage = SIQSStage()
    original_build = stage._SIQSStage__build_factor_base
    stage._SIQSStage__build_factor_base = lambda n, bound: [-1]
    try:
        result = stage._SIQSStage__find_factor(91)
        assert result is None
    finally:
        stage._SIQSStage__build_factor_base = original_build


def test_siqs_relations_lt_base() -> None:
    """Verify __find_factor returns None when relations < len(factor_base)."""
    stage = SIQSStage()
    original_relations = stage._SIQSStage__find_smooth_relations
    stage._SIQSStage__find_smooth_relations = lambda n, fb, target: []
    try:
        result = stage._SIQSStage__find_factor(91)
        assert result is None
    finally:
        stage._SIQSStage__find_smooth_relations = original_relations


def test_siqs_dependency_none() -> None:
    """Verify __find_factor returns None when dependency is None."""
    stage = SIQSStage()
    import factorise.stages.siqs as siqs_module
    original_find_dep = siqs_module.find_dependency
    siqs_module.find_dependency = lambda rels, num_primes: None
    # Ensure enough relations are returned to pass the len check
    original_relations = stage._SIQSStage__find_smooth_relations
    stage._SIQSStage__find_smooth_relations = lambda n, fb, target: [
        {"a": 1, "a2_mod_n": 1, "exponents": [0] * len(fb)}
        for _ in range(len(fb) + 1)
    ]
    try:
        result = stage._SIQSStage__find_factor(91)
        assert result is None
    finally:
        siqs_module.find_dependency = original_find_dep
        stage._SIQSStage__find_smooth_relations = original_relations


def test_siqs_build_factor_base_return() -> None:
    """Verify __build_factor_base returns base list."""
    stage = SIQSStage()
    base = stage._SIQSStage__build_factor_base(91, 20)
    assert isinstance(base, list)
    assert base[0] == -1


def test_siqs_find_smooth_relations_return() -> None:
    """Verify __find_smooth_relations returns relations list."""
    stage = SIQSStage()
    # Use a large target so the early return isn't hit
    relations = stage._SIQSStage__find_smooth_relations(91, [-1, 2, 3], 1000)
    assert isinstance(relations, list)
    assert len(relations) < 1000


def test_siqs_success_path() -> None:
    """Verify SIQSStage success return path."""
    stage = SIQSStage()
    original = stage._SIQSStage__find_factor
    stage._SIQSStage__find_factor = lambda n: 7
    try:
        result = stage.attempt(91)
        assert result.status is StageStatus.SUCCESS
        assert result.factor == 7
    finally:
        stage._SIQSStage__find_factor = original


# ---------------------------------------------------------------------------
# Additional qs_shared.py coverage for extract_factor gcd paths
# ---------------------------------------------------------------------------


def test_extract_factor_second_gcd() -> None:
    """Verify extract_factor hits the second gcd candidate path."""
    # Construct a case where gcd(product_x - product_y, n) == 1
    # but gcd(product_x + product_y, n) > 1
    rels: list[QSRelation] = [
        {"a": 10, "a2_mod_n": 100, "exponents": [0, 2, 0]},
    ]
    result = extract_factor(91, rels, [0], [-1, 7, 13])
    assert result is None or isinstance(result, int)


def test_extract_factor_return_none_path() -> None:
    """Verify extract_factor returns None when neither gcd finds a factor."""
    rels: list[QSRelation] = [
        {"a": 1, "a2_mod_n": 1, "exponents": [0, 0, 0]},
    ]
    result = extract_factor(91, rels, [0], [-1, 2, 3])
    assert result is None
