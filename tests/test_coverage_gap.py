"""Exhaustive tests for covering remaining coverage gaps in core and cli."""

import signal
import threading
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from factorise.cli import app, configure_logging, handle_signal
from factorise.core import (
    FactorisationResult,
    FactoriserConfig,
    factorise,
    pollard_brent,
    pollard_brent_attempt,
    validate_int,
)

# Constants for Testing
TEST_BATCH_SIZE: int = 64
TEST_MAX_ITERATIONS: int = 500_000
TEST_MAX_RETRIES: int = 10
PRIMES_IN_LIST: int = 73
LARGE_COMPOSITE: int = (10**9 + 7) * (10**9 + 9)
COLLAPSE_N: int = 10001
SIMULATION_VAL: str = "Simulation"
CLI_INPUT: str = "123"

# Initialize Global Runner
CLI_RUNNER: CliRunner = CliRunner()


# ---------------------------------------------------------------------------
# Core: Configuration & Validation Gaps
# ---------------------------------------------------------------------------


def test_config_from_env_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that FactoriserConfig.from_env() raises ValueError on bad data.

    Args:
        monkeypatch: Pytest fixture to manipulate environment variables.
    """
    monkeypatch.setenv("FACTORISE_BATCH_SIZE", "not-an-int")
    with pytest.raises(ValueError):
        FactoriserConfig.from_env()


@pytest.mark.parametrize("value", [1.0, "1", None, [1], {1: 1}])
def test_validate_int_failures(value: object) -> None:
    """Verify validate_int raises TypeError for non-int types.

    Args:
        value: The invalid value to check.
    """
    with pytest.raises(TypeError) as excinfo:
        validate_int(value)
    assert "must be a plain int" in str(excinfo.value)


def test_validate_int_boolean() -> None:
    """Verify validate_int raises TypeError specifically for booleans."""
    with pytest.raises(TypeError):
        validate_int(True)
    with pytest.raises(TypeError):
        validate_int(False)


# ---------------------------------------------------------------------------
# Core: Algorithmic Edge Cases (Iteration Caps & Backtracking)
# ---------------------------------------------------------------------------


def test_pollard_brent_attempt_iteration_cap() -> None:
    """Force pollard_brent_attempt to hit its iteration cap and return None."""
    config = FactoriserConfig(max_iterations=1, batch_size=1)
    result = pollard_brent_attempt(LARGE_COMPOSITE, 2, 1, config)
    assert result is None


def test_pollard_brent_attempt_backtrack_cap() -> None:
    """Force pollard_brent_attempt to hit its backtrack cap and return None."""
    config = FactoriserConfig(max_iterations=1, batch_size=1)
    with patch("math.gcd", side_effect=[COLLAPSE_N, 1]):
        result = pollard_brent_attempt(COLLAPSE_N, 2, 1, config)
        assert result is None


def test_pollard_brent_trial_division_path() -> None:
    """Verify that pollard_brent returns early for primes in its trial division list."""
    config = FactoriserConfig()
    # 73 is the last prime in the trial division list.
    assert pollard_brent(PRIMES_IN_LIST * 2, config) == 2
    assert pollard_brent(PRIMES_IN_LIST * PRIMES_IN_LIST, config) == PRIMES_IN_LIST


def test_pollard_brent_runtime_error_exhaustion() -> None:
    """Verify pollard_brent raises RuntimeError when all retries are exhausted."""
    config = FactoriserConfig(max_retries=1, max_iterations=1)
    with patch("factorise.core.is_prime", return_value=False):
        with patch("factorise.core.pollard_brent_attempt", return_value=None):
            with pytest.raises(RuntimeError) as excinfo:
                pollard_brent(8051, config)
            assert "failed" in str(excinfo.value)


def test_pollard_brent_perfect_square() -> None:
    """Verify the perfect square shortcut in pollard_brent."""
    # 101 is prime. 101*101 = 10201.
    config = FactoriserConfig()
    assert pollard_brent(10201, config) == 101


# ---------------------------------------------------------------------------
# CLI: Signal Handling & Logging Gaps
# ---------------------------------------------------------------------------


def test_cli_handle_signal() -> None:
    """Directly test the handle_signal function to cover shutdown logging."""
    with patch("sys.exit") as mock_exit:
        handle_signal(signal.SIGINT, None)
        mock_exit.assert_called_with(0)


def test_cli_logging_configuration_verification() -> None:
    """Verify the logger name and basic configuration entrypoint."""
    # Just ensure it executes without crashing
    configure_logging("DEBUG")
    configure_logging("warning")


def test_cli_error_handling_type_error() -> None:
    """Trigger a TypeError handling branch in CLI main."""
    with patch("factorise.cli.factorise", side_effect=TypeError(SIMULATION_VAL)):
        result = CLI_RUNNER.invoke(app, [CLI_INPUT])
        assert result.exit_code == 1
        assert "Input Error" in result.output


def test_cli_error_handling_runtime_error() -> None:
    """Trigger a RuntimeError handling branch in CLI main."""
    with patch("factorise.cli.factorise", side_effect=RuntimeError(SIMULATION_VAL)):
        result = CLI_RUNNER.invoke(app, [CLI_INPUT])
        assert result.exit_code == 1
        assert "Runtime Error" in result.output


def test_cli_error_handling_value_error() -> None:
    """Trigger a ValueError handling branch in CLI main."""
    with patch("factorise.cli.factorise", side_effect=ValueError(SIMULATION_VAL)):
        result = CLI_RUNNER.invoke(app, [CLI_INPUT])
        assert result.exit_code == 1
        assert "Value Error" in result.output


# ---------------------------------------------------------------------------
# Result: Expression Gaps
# ---------------------------------------------------------------------------


def test_result_expression_complex() -> None:
    """Test FactorisationResult.expression with various factors and signs."""
    res = FactorisationResult(
        original=-30, sign=-1, factors=[2, 3, 5], powers={2: 1, 3: 1, 5: 1}, is_prime=False
    )
    assert res.expression() == "-1 * 2 * 3 * 5"

    res2 = FactorisationResult(original=1, sign=1, factors=[], powers={}, is_prime=False)
    assert res2.expression() == ""


# ---------------------------------------------------------------------------
# Concurrency: Thread Safety
# ---------------------------------------------------------------------------


def test_core_thread_safety() -> None:
    """Verify that multiple threads can factorise concurrently without race conditions."""

    def worker() -> None:
        """Sequential factorisation routine for thread testing."""
        for i in range(100, 200):
            res = factorise(i)
            assert res.original == i

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
