"""Pollard-Brent and factor flattening tests for factorise.core."""

from typing import cast

import pytest

from factorise.core import FactoriserConfig
from factorise.core import factor_flatten
from factorise.core import pollard_brent
from tests.conftest import DEFAULT_CONFIG


@pytest.mark.parametrize("n", [-5, -1, 0, 1])
def test_factor_flatten_below_two(n: int) -> None:
    assert not factor_flatten(n, DEFAULT_CONFIG)


def test_factor_flatten_invalid_config_type_raises() -> None:
    with pytest.raises(TypeError):
        factor_flatten(12, config=cast(FactoriserConfig, object()))


@pytest.mark.parametrize("n", [2, 4, 6, 100, 2**20])
def test_pollard_brent_even_returns_two(n: int) -> None:
    assert pollard_brent(n, DEFAULT_CONFIG) == 2


@pytest.mark.parametrize("p", [3, 5, 7, 97, 997])
def test_pollard_brent_prime_returns_self(p: int) -> None:
    assert pollard_brent(p, DEFAULT_CONFIG) == p


def test_pollard_brent_invalid_config_type_raises() -> None:
    with pytest.raises(TypeError):
        pollard_brent(91, config=cast(FactoriserConfig, object()))


def test_pollard_brent_seed_reproducible() -> None:
    n = 99_991 * 99_989
    cfg = FactoriserConfig(seed=123, max_retries=5, max_iterations=1_000_000)
    assert pollard_brent(n, cfg) == pollard_brent(n, cfg)
