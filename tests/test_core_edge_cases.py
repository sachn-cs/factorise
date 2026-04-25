"""Edge-case tests for internal core algorithm paths."""

from pickle import dumps
from unittest.mock import patch

import pytest

from factorise.config import FactoriserConfig
from factorise.core import BrentPollardCycleResult as AttemptResult
from factorise.core import PollardBrentOutcome as AttemptStatus
from factorise.core import ensure_integer_input
from factorise.core import execute_brent_pollard_cycle as pollard_brent_attempt
from factorise.core import find_nontrivial_factor_pollard_brent as pollard_brent

PRIMES_IN_LIST: int = 73
LARGE_COMPOSITE: int = (10**9 + 7) * (10**9 + 9)
COLLAPSE_N: int = 10001


def test_config_from_env_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that FactoriserConfig.from_env handles invalid types gracefully."""
    monkeypatch.setenv("FACTORISE_BATCH_SIZE", "not-an-int")
    with pytest.raises(ValueError):
        FactoriserConfig.from_env()


@pytest.mark.parametrize("value", [1.0, "1", None, [1], {1: 1}])
def test_validate_int_failures(value: object) -> None:
    """Verify that ensure_integer_input raises TypeError for various non-integer types."""
    with pytest.raises(TypeError) as excinfo:
        ensure_integer_input(value)
    assert "must be a plain int" in str(excinfo.value)


def test_validate_int_boolean() -> None:
    """Verify that booleans (True/False) are rejected by ensure_integer_input."""
    with pytest.raises(TypeError):
        ensure_integer_input(True)
    with pytest.raises(TypeError):
        ensure_integer_input(False)


def test_pollard_brent_attempt_iteration_cap() -> None:
    """Verify that pollard_brent_attempt terminates when the iteration cap is hit."""
    config = FactoriserConfig(max_iterations=1, batch_size=1)
    result = pollard_brent_attempt(LARGE_COMPOSITE,
                                   2,
                                   1,
                                   config,
                                   max_iterations=1)
    assert result.outcome is AttemptStatus.ITERATION_CAP_HIT


def test_pollard_brent_attempt_backtrack_cap() -> None:
    """Verify pollard_brent_attempt returns ITERATION_CAP_HIT when backtrack budget is exhausted.

    With max_iterations=1, after 1 iteration is used in the main loop,
    backtrack_budget = max_iterations - iterations = 1 - 1 = 0,
    triggering ITERATION_CAP_HIT before any backtrack stepping occurs.
    """
    config = FactoriserConfig(max_iterations=1, batch_size=1)
    # First gcd (line 329 checkpoint): returns 1 -> g=1, no factor found
    # Second gcd (line 335 post-batch): returns n -> g=n, main loop exits
    # Then backtrack_budget = 1 - 1 = 0 -> ITERATION_CAP_HIT
    with patch("math.gcd", side_effect=[1, 10001, 1, 1, 1]):
        result = pollard_brent_attempt(10001, 2, 1, config, max_iterations=1)
        assert result.outcome is AttemptStatus.ITERATION_CAP_HIT


def test_pollard_brent_trial_division_path() -> None:
    """Verify that pollard_brent succeeds using trial division for small factors."""
    config = FactoriserConfig()
    assert pollard_brent(PRIMES_IN_LIST * 2, config) == 2
    assert (pollard_brent(PRIMES_IN_LIST * PRIMES_IN_LIST,
                          config) == PRIMES_IN_LIST)


def test_pollard_brent_exhaustion() -> None:
    """Verify that pollard_brent raises when all retries are exhausted.

    Uses a number (233*239=55687) whose prime factors are all > 229 so trial
    division can't find them, bypassing that fast-path.
    """
    # 233 and 239 are both > 229 (end of TRIAL_DIVISION_PRIMES)
    n_large = 233 * 239  # = 55687
    config = FactoriserConfig(max_retries=1, max_iterations=1)
    failed_attempt = AttemptResult(
        AttemptStatus.ALGORITHM_FAILURE,
        iterations_used=1,
        factor=None,
    )
    with patch(
            "factorise.core.execute_brent_pollard_cycle",
            return_value=failed_attempt,
    ):
        with pytest.raises(Exception) as excinfo:
            pollard_brent(n_large, config)
        assert "failed" in str(excinfo.value)


def test_stress_worker_pickling_smoke() -> None:
    """Verify that the stress benchmark workers are properly pickleable."""
    from benchmarks.stress import CONFIG
    from benchmarks.stress import process_chunk

    dumps(CONFIG)
    dumps(process_chunk)


def test_pollard_brent_perfect_square() -> None:
    """Verify that Pollard-Brent handles perfect squares correctly."""
    config = FactoriserConfig()
    assert pollard_brent(10201, config) == 101
