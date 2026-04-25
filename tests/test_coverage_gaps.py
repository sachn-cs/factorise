"""Targeted tests for coverage gaps in hybrid, gnfs, ecm, and core."""

import subprocess
import unittest.mock as mock

import pytest

from factorise.config import HybridConfig
from factorise.core import BrentPollardCycleResult
from factorise.core import FactorisationError
from factorise.core import PollardBrentOutcome
from factorise.core import execute_brent_pollard_cycle
from factorise.core import has_carmichael_property
from factorise.hybrid import HybridFactorisationEngine
from factorise.hybrid import hybrid_factorise
from factorise.pipeline import StageStatus
from factorise.pipeline import yield_prime_factors_via_pipeline
from factorise.stages.ecm import ECMStage
from factorise.stages.ecm_two_pass import TwoPassECMStage
from factorise.stages.gnfs import GNFSStage
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
# gnfs.py — all branches via mocking
# ---------------------------------------------------------------------------


def test_gnfs_skips_too_small() -> None:
    """Verify GNFS skips n < 3."""
    stage = GNFSStage(binary="msieve")
    result = stage.attempt(2)
    assert result.status is StageStatus.SKIPPED


def test_gnfs_skips_prime() -> None:
    """Verify GNFS skips prime inputs."""
    stage = GNFSStage(binary="msieve")
    result = stage.attempt(97)
    assert result.status is StageStatus.SKIPPED


def test_gnfs_build_command_msieve() -> None:
    """Verify build_command for msieve."""
    stage = GNFSStage(binary="msieve")
    cmd = stage.build_command("input.txt", "fact.txt", "/tmp", 12345)
    assert "msieve" in cmd
    assert "input.txt" in cmd


def test_gnfs_build_command_cado() -> None:
    """Verify build_command for cado-nfs."""
    stage = GNFSStage(binary="cado-nfs")
    cmd = stage.build_command("input.txt", "fact.txt", "/tmp", 12345)
    assert "cado-nfs" in cmd
    assert "tasks.factor.bswap_nwords=1" in cmd


def test_gnfs_build_command_generic() -> None:
    """Verify build_command for generic binary."""
    stage = GNFSStage(binary="gnfs")
    cmd = stage.build_command("input.txt", "fact.txt", "/tmp", 12345)
    assert cmd == ["gnfs", "input.txt"]


def test_gnfs_parse_factor_output_fact_file(tmp_path) -> None:
    """Verify parse_factor_output reads fact file."""
    stage = GNFSStage()
    fact_file = tmp_path / "factors.txt"
    fact_file.write_text("1234567\n8901234\n")
    factors = stage.parse_factor_output("", str(fact_file))
    assert 1234567 in factors
    assert 8901234 in factors


def test_gnfs_parse_factor_output_p_notation() -> None:
    """Verify parse_factor_output parses pN = notation."""
    stage = GNFSStage()
    output = "p1 = 1234567\nP2 = 8901234\n"
    factors = stage.parse_factor_output(output, None)
    assert 1234567 in factors
    assert 8901234 in factors


def test_gnfs_parse_factor_output_large_digits() -> None:
    """Verify parse_factor_output parses large digit lines."""
    stage = GNFSStage()
    # Use a prime with >= 5 digits so is_small_prime includes it
    output = "\n  10007  \n"
    factors = stage.parse_factor_output(output, None)
    assert 10007 in factors


def test_gnfs_run_external_timeout() -> None:
    """Verify run_external_gnfs raises on timeout."""
    stage = GNFSStage(binary="msieve", timeout_seconds=1)
    with mock.patch("shutil.which", return_value="/bin/msieve"):
        with mock.patch("subprocess.run",
                        side_effect=subprocess.TimeoutExpired("cmd", 1)):
            with pytest.raises(FactorisationError):
                stage.run_external_gnfs(2**90 + 1)


def test_gnfs_run_external_bad_exit() -> None:
    """Verify run_external_gnfs raises on non-zero exit."""
    stage = GNFSStage(binary="msieve")
    mock_result = mock.Mock()
    mock_result.stdout = ""
    mock_result.stderr = "error"
    mock_result.returncode = 1
    with mock.patch("shutil.which", return_value="/bin/msieve"):
        with mock.patch("subprocess.run", return_value=mock_result):
            with mock.patch.object(stage,
                                   "parse_factor_output",
                                   return_value=[]):
                with pytest.raises(FactorisationError):
                    stage.run_external_gnfs(2**90 + 1)


def test_gnfs_run_external_no_factors() -> None:
    """Verify run_external_gnfs raises when no factors found."""
    stage = GNFSStage(binary="msieve")
    mock_result = mock.Mock()
    mock_result.stdout = ""
    mock_result.stderr = ""
    mock_result.returncode = 0
    with mock.patch("shutil.which", return_value="/bin/msieve"):
        with mock.patch("subprocess.run", return_value=mock_result):
            with mock.patch.object(stage,
                                   "parse_factor_output",
                                   return_value=[]):
                with pytest.raises(FactorisationError):
                    stage.run_external_gnfs(2**90 + 1)


def test_gnfs_attempt_successful() -> None:
    """Verify GNFS attempt returns SUCCESS when factor found."""
    stage = GNFSStage(binary="msieve")
    with mock.patch.object(stage, "is_tool_available", return_value=True):
        with mock.patch.object(stage, "run_external_gnfs", return_value=7):
            n = 2**90 + 1  # Must be >= 80 bits
            result = stage.attempt(n)
            assert result.status is StageStatus.SUCCESS
            assert result.factor is not None


def test_gnfs_attempt_tool_unavailable() -> None:
    """Verify GNFS skips when binary not available."""
    stage = GNFSStage(binary="nonexistent_tool_xyz")
    result = stage.attempt(2**90 + 1)
    assert result.status is StageStatus.SKIPPED


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
