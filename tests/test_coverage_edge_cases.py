"""Dedicated tests for defensive edge cases and logic paths to push coverage to >99%."""

from unittest.mock import patch

import pytest

from source.cli import app
from source.core import AttemptResult
from source.core import AttemptStatus
from source.core import FactorisationError
from source.core import FactoriserConfig
from source.core import pollard_brent
from source.core import pollard_brent_attempt
from source.core import validate_int
from tests.conftest import DEFAULT_CONFIG

# n=8051 is 83 * 97. Neither factor is in TRIAL_DIVISION_PRIMES.
SEMIPRIME_8051 = 8051

# ---------------------------------------------------------------------------
# Core Defensive Checks
# ---------------------------------------------------------------------------


def test_validate_int_error_message() -> None:
    """Verify the error message content for validate_int."""
    with pytest.raises(TypeError) as excinfo:
        validate_int("42", name="test_param")
    assert "test_param must be a plain int, got 'str'" in str(excinfo.value)


def test_pollard_brent_attempt_invalid_config() -> None:
    """Trigger the defensive type check for config in pollard_brent_attempt."""
    with pytest.raises(TypeError) as excinfo:
        # Pass something that isn't a FactoriserConfig
        pollard_brent_attempt(15, 2, 1, "not_a_config", 100)  # type: ignore
    assert "config must be FactoriserConfig" in str(excinfo.value)


def test_pollard_brent_invalid_config() -> None:
    """Trigger the defensive type check for config in pollard_brent."""
    with pytest.raises(TypeError) as excinfo:
        pollard_brent(15, "not_a_config")  # type: ignore
    assert "config must be FactoriserConfig" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Algorithm Failure Paths
# ---------------------------------------------------------------------------


def test_pollard_brent_backtrack_failure() -> None:
    """Trigger the backtrack exhaustion (else) branch in pollard_brent_attempt."""
    # To reach the backtrack fail (line 310) in core.py:
    # 1. Main loop must exit with g == n.
    # 2. Backtrack loop must finish without finding g > 1.
    # We provide a large list of 1s to avoid StopIteration.
    with patch("source.core.math.gcd", side_effect=[8051] + ([1] * 500)):
        result = pollard_brent_attempt(
            n=8051, y=2, c=1, config=DEFAULT_CONFIG, max_iterations=50
        )
        assert result.status == AttemptStatus.ALGORITHM_FAILURE


def test_pollard_brent_success_without_factor_bug() -> None:
    """Verify defensive check when algorithm claims success but provides no factor."""
    fake_success = AttemptResult(
        status=AttemptStatus.SUCCESS, iterations_used=1, factor=None
    )
    with patch("source.core.pollard_brent_attempt", return_value=fake_success):
        with patch("source.core.is_prime", return_value=False):
            with pytest.raises(FactorisationError) as excinfo:
                pollard_brent(SEMIPRIME_8051, DEFAULT_CONFIG)
            assert "returned SUCCESS without a factor" in str(excinfo.value)


def test_pollard_brent_global_iteration_cap_hit() -> None:
    """Verify behavior when the global iteration cap is hit."""
    cap_hit = AttemptResult(
        status=AttemptStatus.ITERATION_CAP_HIT, iterations_used=10
    )
    with patch("source.core.pollard_brent_attempt", return_value=cap_hit):
        with patch("source.core.is_prime", return_value=False):
            # Using a large semiprime to bypass trial division
            with pytest.raises(FactorisationError) as excinfo:
                pollard_brent(SEMIPRIME_8051, DEFAULT_CONFIG)
            assert f"failed for n={SEMIPRIME_8051}" in str(excinfo.value)


# ---------------------------------------------------------------------------
# CLI Polish
# ---------------------------------------------------------------------------


def test_cli_main_invalid_input_value() -> None:
    """Hit the ValueError catch block in cli.main (e.g. invalid config from env)."""
    from typer.testing import CliRunner

    runner = CliRunner()
    with patch(
        "source.cli.FactoriserConfig.from_env",
        side_effect=ValueError("bad config"),
    ):
        result = runner.invoke(app, ["8051"])
        assert result.exit_code == 1
        assert "Value Error" in result.output


def test_cli_main_type_error_catch() -> None:
    """Hit the TypeError catch block in cli.main."""
    from typer.testing import CliRunner

    runner = CliRunner()
    # Mock factorise to raise TypeError
    with patch("source.cli.factorise", side_effect=TypeError("not an int")):
        result = runner.invoke(app, ["8051"])
        assert result.exit_code == 1
        assert "Input Error" in result.output


def test_pollard_brent_all_retries_fail() -> None:
    """Exhaust all retries in pollard_brent to hit loop termination branch."""
    # This hits the 'for' loop completion in pollard_brent (line 351 BrPart)
    fail_res = AttemptResult(
        status=AttemptStatus.ALGORITHM_FAILURE, iterations_used=1
    )
    with patch("source.core.pollard_brent_attempt", return_value=fail_res):
        with patch("source.core.is_prime", return_value=False):
            # Using a very low max_retries to speed up the test
            cfg = FactoriserConfig(max_retries=1)
            with pytest.raises(RuntimeError):
                pollard_brent(8051, cfg)
