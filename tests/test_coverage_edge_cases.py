"""Dedicated tests for defensive edge cases and logic paths to push coverage to >99%."""

from typing import cast
from unittest.mock import patch

import pytest

from factorise.cli import main
from factorise.config import FactoriserConfig
from factorise.core import BrentPollardCycleResult as AttemptResult
from factorise.core import FactorisationError
from factorise.core import PollardBrentOutcome as AttemptStatus
from factorise.core import ensure_integer_input
from factorise.core import execute_brent_pollard_cycle as pollard_brent_attempt
from factorise.core import find_nontrivial_factor_pollard_brent as pollard_brent
from tests.conftest import DEFAULT_CONFIG

# 233 * 239 = 55687 - both primes > 229 (end of TRIAL_DIVISION_PRIMES)
SEMIPRIME_LARGE = 233 * 239
# 1009 * 10007 = 10107263 - another large composite with no small factors
LARGE_COMPOSITE_NO_SMALL_FACTORS = 1009 * 10007


def _run_main(argv: list[str]) -> tuple[int, str, str]:
    """Run main() with argv, capture stdout/stderr, return (exit_code, stdout, stderr)."""
    import sys
    from io import StringIO
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    stdout_buf = StringIO()
    stderr_buf = StringIO()
    try:
        sys.stdout = stdout_buf
        sys.stderr = stderr_buf
        try:
            main(argv)
            exit_code = 0
        except SystemExit as e:
            exit_code = e.code if isinstance(e.code, int) else 1
        return exit_code, stdout_buf.getvalue(), stderr_buf.getvalue()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


# ---------------------------------------------------------------------------
# Core Defensive Checks
# ---------------------------------------------------------------------------


def test_validate_int_error_message() -> None:
    """Verify the error message content for validate_int."""
    with pytest.raises(TypeError) as excinfo:
        ensure_integer_input("42", name="test_param")
    assert "test_param must be a plain int, got 'str'" in str(excinfo.value)


def test_pollard_brent_attempt_invalid_config() -> None:
    """Trigger the defensive type check for config in pollard_brent_attempt."""
    with pytest.raises(TypeError) as excinfo:
        pollard_brent_attempt(15, 2, 1, cast(FactoriserConfig, "not_a_config"), 100)
    assert "config must be FactoriserConfig" in str(excinfo.value)


def test_pollard_brent_invalid_config() -> None:
    """Trigger the defensive type check for config in pollard_brent."""
    with pytest.raises(TypeError) as excinfo:
        pollard_brent(15, cast(FactoriserConfig, "not_a_config"))
    assert "config must be FactoriserConfig" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Algorithm Failure Paths
# ---------------------------------------------------------------------------


def test_pollard_brent_backtrack_failure() -> None:
    """Verify ALGORITHM_FAILURE is returned when pollard_brent_attempt exhausts backtrack budget."""
    n = LARGE_COMPOSITE_NO_SMALL_FACTORS
    config = FactoriserConfig(max_iterations=1, batch_size=1)
    result = pollard_brent_attempt(n, 2, 1, config, max_iterations=1)
    assert result.outcome in (
        AttemptStatus.ITERATION_CAP_HIT,
        AttemptStatus.ALGORITHM_FAILURE,
    )


def test_pollard_brent_success_without_factor_bug() -> None:
    """Verify defensive check when algorithm claims success but provides no factor."""
    fake_success = AttemptResult(AttemptStatus.SUCCESS, iterations_used=1, factor=None)
    with patch("factorise.core.execute_brent_pollard_cycle", return_value=fake_success):
        with patch("factorise.core.is_prime", return_value=False):
            with pytest.raises(FactorisationError) as excinfo:
                pollard_brent(LARGE_COMPOSITE_NO_SMALL_FACTORS, DEFAULT_CONFIG)
            assert "returned SUCCESS without a factor" in str(excinfo.value)


def test_pollard_brent_global_iteration_cap_hit() -> None:
    """Verify behavior when the global iteration cap is hit."""
    cap_hit = AttemptResult(AttemptStatus.ITERATION_CAP_HIT, iterations_used=10)
    with patch("factorise.core.execute_brent_pollard_cycle", return_value=cap_hit):
        with patch("factorise.core.is_prime", return_value=False):
            with pytest.raises(FactorisationError) as excinfo:
                pollard_brent(LARGE_COMPOSITE_NO_SMALL_FACTORS, DEFAULT_CONFIG)
            assert f"failed for n={LARGE_COMPOSITE_NO_SMALL_FACTORS}" in str(excinfo.value)


# ---------------------------------------------------------------------------
# CLI Polish
# ---------------------------------------------------------------------------


def test_cli_main_invalid_input_value() -> None:
    """Hit the ValueError catch block in cli.main (e.g. invalid config from env)."""
    with patch(
        "factorise.cli.FactoriserConfig.from_env",
        side_effect=ValueError("bad config"),
    ):
        exit_code, stdout, stderr = _run_main(["8051"])
        assert exit_code == 1
        assert "Value Error" in stderr


def test_cli_main_type_error_catch() -> None:
    """Hit the TypeError catch block in cli.main."""
    with patch("factorise.cli.factorise", side_effect=TypeError("not an int")):
        exit_code, stdout, stderr = _run_main(["8051"])
        assert exit_code == 1
        assert "Input Error" in stderr


def test_pollard_brent_all_retries_fail() -> None:
    """Exhaust all retries in pollard_brent to hit loop termination branch."""
    fail_res = AttemptResult(AttemptStatus.ALGORITHM_FAILURE, iterations_used=1)
    with patch("factorise.core.execute_brent_pollard_cycle", return_value=fail_res):
        with patch("factorise.core.is_prime", return_value=False):
            cfg = FactoriserConfig(max_retries=1)
            with pytest.raises(FactorisationError):
                pollard_brent(LARGE_COMPOSITE_NO_SMALL_FACTORS, cfg)
