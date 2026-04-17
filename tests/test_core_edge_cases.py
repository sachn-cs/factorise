"""Edge-case tests for internal core algorithm paths."""

from pickle import dumps
from unittest.mock import patch

import pytest

from factorise.core import AttemptResult
from factorise.core import AttemptStatus
from factorise.core import FactoriserConfig
from factorise.core import pollard_brent
from factorise.core import pollard_brent_attempt
from factorise.core import validate_int

PRIMES_IN_LIST: int = 73
LARGE_COMPOSITE: int = (10**9 + 7) * (10**9 + 9)
COLLAPSE_N: int = 10001


def test_config_from_env_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FACTORISE_BATCH_SIZE", "not-an-int")
    with pytest.raises(ValueError):
        FactoriserConfig.from_env()


@pytest.mark.parametrize("value", [1.0, "1", None, [1], {1: 1}])
def test_validate_int_failures(value: object) -> None:
    with pytest.raises(TypeError) as excinfo:
        validate_int(value)
    assert "must be a plain int" in str(excinfo.value)


def test_validate_int_boolean() -> None:
    with pytest.raises(TypeError):
        validate_int(True)
    with pytest.raises(TypeError):
        validate_int(False)


# Internal API contracts may change without notice.
def test_pollard_brent_attempt_iteration_cap() -> None:
    config = FactoriserConfig(max_iterations=1, batch_size=1)
    result = pollard_brent_attempt(LARGE_COMPOSITE, 2, 1, config, max_iterations=1)
    assert result.status is AttemptStatus.ITERATION_CAP_HIT


def test_pollard_brent_attempt_backtrack_cap() -> None:
    config = FactoriserConfig(max_iterations=1, batch_size=1)
    with patch("math.gcd", side_effect=[COLLAPSE_N, 1]):
        result = pollard_brent_attempt(COLLAPSE_N, 2, 1, config, max_iterations=1)
        assert result.status is AttemptStatus.ITERATION_CAP_HIT


def test_pollard_brent_trial_division_path() -> None:
    config = FactoriserConfig()
    assert pollard_brent(PRIMES_IN_LIST * 2, config) == 2
    assert pollard_brent(PRIMES_IN_LIST * PRIMES_IN_LIST, config) == PRIMES_IN_LIST


def test_pollard_brent_runtime_error_exhaustion() -> None:
    config = FactoriserConfig(max_retries=1, max_iterations=1)
    with patch("factorise.core.is_prime", return_value=False):
        failed_attempt = AttemptResult(
            status=AttemptStatus.ALGORITHM_FAILURE, iterations_used=1, factor=None
        )
        with patch("factorise.core.pollard_brent_attempt", return_value=failed_attempt):
            with pytest.raises(RuntimeError) as excinfo:
                pollard_brent(8051, config)
            assert "failed" in str(excinfo.value)


def test_stress_worker_pickling_smoke() -> None:
    from benchmarks.stress import CONFIG
    from benchmarks.stress import process_chunk

    dumps(CONFIG)
    dumps(process_chunk)


def test_pollard_brent_perfect_square() -> None:
    config = FactoriserConfig()
    assert pollard_brent(10201, config) == 101
