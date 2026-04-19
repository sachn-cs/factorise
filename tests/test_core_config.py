"""Configuration, result model, and input validation tests for factorise.core."""

import pytest

from source.core import FactorisationResult
from source.core import FactoriserConfig
from source.core import validate_int
from tests.conftest import DEFAULT_CONFIG


def test_config_defaults() -> None:
    """Verify that FactoriserConfig initializes with standard defaults."""
    cfg = FactoriserConfig()
    assert cfg.batch_size == 128
    assert cfg.max_iterations == 10000000
    assert cfg.max_retries == 20


def test_config_custom_values() -> None:
    """Verify that FactoriserConfig correctly stores custom override values."""
    cfg = FactoriserConfig(batch_size=64, max_iterations=1000, max_retries=5)
    assert cfg.batch_size == 64


@pytest.mark.parametrize(
    "kwargs",
    [
        {"batch_size": 0},
        {"batch_size": -1},
        {"max_iterations": 0},
        {"max_retries": 0},
    ],
)
def test_config_invalid_raises(kwargs: dict[str, int]) -> None:
    """Verify that FactoriserConfig validates its inputs during initialization."""
    with pytest.raises(ValueError):
        FactoriserConfig(**kwargs)


def test_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that config can be correctly bootstrapped from environment vars."""
    monkeypatch.setenv("FACTORISE_BATCH_SIZE", "64")
    monkeypatch.setenv("FACTORISE_MAX_ITERATIONS", "500000")
    monkeypatch.setenv("FACTORISE_MAX_RETRIES", "10")
    monkeypatch.setenv("FACTORISE_SEED", "123")
    cfg = FactoriserConfig.from_env()
    assert cfg.batch_size == 64
    assert cfg.max_iterations == 500000
    assert cfg.max_retries == 10
    assert cfg.seed == 123


def test_result_is_dataclass() -> None:
    """Verify that the result model is a Frozen Dataclass."""
    from source.core import factorise

    res = factorise(12, DEFAULT_CONFIG)
    assert isinstance(res, FactorisationResult)


def test_result_expression_positive() -> None:
    """Verify the string expression for positive composite results."""
    from source.core import factorise

    res = factorise(12, DEFAULT_CONFIG)
    expr = res.expression()
    assert "2^2" in expr
    assert "3" in expr
    assert "-1" not in expr


def test_result_expression_negative() -> None:
    """Verify the string expression for negative composite results."""
    from source.core import factorise

    res = factorise(-12, DEFAULT_CONFIG)
    assert res.expression().startswith("-1 *")


def test_result_expression_prime() -> None:
    """Verify the string expression for prime results."""
    from source.core import factorise

    res = factorise(7, DEFAULT_CONFIG)
    assert res.expression() == "7"


@pytest.mark.parametrize(
    "bad", [None, 1.5, "12", [12], (12,), {12}, True, False]
)
def test_validate_int_rejects_non_int(bad: object) -> None:
    """Verify that validate_int raises TypeError for non-integer types."""
    with pytest.raises(TypeError):
        validate_int(bad)


def test_validate_int_accepts_plain_int() -> None:
    """Verify that validate_int allows plain integers without raising."""
    validate_int(42)
    validate_int(-10)
    validate_int(0)
