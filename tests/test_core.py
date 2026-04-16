"""Tests for factorise.core."""

import math
import threading
from collections.abc import Iterable
from functools import reduce

import pytest

from factorise.core import (
    FactorisationResult,
    FactoriserConfig,
    factor_flatten,
    factorise,
    is_prime,
    pollard_brent,
    validate_int,
)

DEFAULT = FactoriserConfig()


def product(factors: Iterable[int]) -> int:
    """Return the product of all elements in *factors*."""
    return reduce(lambda a, b: a * b, factors, 1)


def is_prime_naive(n: int) -> bool:
    """Brute-force primality — used as ground truth for small n only."""
    if n < 2:
        return False
    return all(n % i != 0 for i in range(2, math.isqrt(n) + 1))


def test_config_defaults():
    """Verify functionality of config_defaults."""
    cfg = FactoriserConfig()
    assert cfg.batch_size == 128
    assert cfg.max_iterations == 10000000
    assert cfg.max_retries == 20


def test_config_custom_values():
    """Verify functionality of config_custom_values."""
    cfg = FactoriserConfig(batch_size=64, max_iterations=1000, max_retries=5)
    assert cfg.batch_size == 64


@pytest.mark.parametrize(
    "kwargs", [{"batch_size": 0}, {"batch_size": -1}, {"max_iterations": 0}, {"max_retries": 0}]
)
def test_config_invalid_raises(kwargs):
    """Verify functionality of config_invalid_raises."""
    with pytest.raises(ValueError):
        FactoriserConfig(**kwargs)


def test_config_from_env(monkeypatch):
    """Verify functionality of config_from_env."""
    monkeypatch.setenv("FACTORISE_BATCH_SIZE", "64")
    monkeypatch.setenv("FACTORISE_MAX_ITERATIONS", "500000")
    monkeypatch.setenv("FACTORISE_MAX_RETRIES", "10")
    cfg = FactoriserConfig.from_env()
    assert cfg.batch_size == 64
    assert cfg.max_iterations == 500000
    assert cfg.max_retries == 10


def test_result_is_dataclass():
    """Verify functionality of result_is_dataclass."""
    res = factorise(12, DEFAULT)
    assert isinstance(res, FactorisationResult)


def test_result_expression_positive():
    """Verify functionality of result_expression_positive."""
    res = factorise(12, DEFAULT)
    expr = res.expression()
    assert "2^2" in expr
    assert "3" in expr
    assert "-1" not in expr


def test_result_expression_negative():
    """Verify functionality of result_expression_negative."""
    res = factorise(-12, DEFAULT)
    assert res.expression().startswith("-1 *")


def test_result_expression_prime():
    """Verify functionality of result_expression_prime."""
    res = factorise(7, DEFAULT)
    assert res.expression() == "7"


@pytest.mark.parametrize("bad", [None, 1.5, "12", [12], (12,), {12}, True, False])
def test_validate_int_rejects_non_int(bad):
    """Verify functionality of validate_int_rejects_non_int."""
    with pytest.raises(TypeError):
        validate_int(bad)


def test_validate_int_accepts_plain_int():
    """Verify functionality of validate_int_accepts_plain_int."""
    validate_int(42)
    validate_int(-10)
    validate_int(0)


@pytest.mark.parametrize("n", [-1000000, -1, 0, 1])
def test_is_prime_below_two_is_false(n: int):
    """Verify functionality of is_prime_below_two_is_false."""
    assert is_prime(n) is False


SMALL_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]


@pytest.mark.parametrize("p", SMALL_PRIMES)
def test_is_prime_small_primes(p: int):
    """Verify functionality of is_prime_small_primes."""
    assert is_prime(p) is True


SMALL_COMPOSITES = [4, 6, 8, 9, 10, 12, 14, 15, 16, 18, 20, 25, 49, 77, 100]


@pytest.mark.parametrize("c", SMALL_COMPOSITES)
def test_is_prime_small_composites(c: int):
    """Verify functionality of is_prime_small_composites."""
    assert is_prime(c) is False


def test_is_prime_agrees_with_naive_up_to_500():
    """Verify functionality of is_prime_agrees_with_naive_up_to_500."""
    for n in range(2, 501):
        assert is_prime(n) == is_prime_naive(n), f"Mismatch at n={n}"


@pytest.mark.parametrize("p", [10**9 + 7, 10**9 + 9, 2**31 - 1, 32416189987])
def test_is_prime_large_primes(p: int):
    """Verify functionality of is_prime_large_primes."""
    assert is_prime(p) is True


@pytest.mark.parametrize("c", [10**9 + 8, 4000000000, 2**31, 100000000000])
def test_is_prime_large_composites(c: int):
    """Verify functionality of is_prime_large_composites."""
    assert is_prime(c) is False


@pytest.mark.parametrize("bad", [None, 1.5, "5", [], True, False])
def test_is_prime_invalid_type_raises(bad):
    """Verify functionality of is_prime_invalid_type_raises."""
    with pytest.raises(TypeError):
        is_prime(bad)


@pytest.mark.parametrize("n", [97, 121, 2**31 - 1, 10**9 + 7])
def test_is_prime_is_deterministic(n: int):
    """Verify functionality of is_prime_is_deterministic."""
    assert len({is_prime(n) for _ in range(20)}) == 1


def test_factorise_small():
    """Verify functionality of factorise_small."""
    res = factorise(12, DEFAULT)
    assert res.factors == [2, 3]
    assert res.powers == {2: 2, 3: 1}


def test_factorise_prime():
    """Verify functionality of factorise_prime."""
    res = factorise(13, DEFAULT)
    assert res.is_prime is True
    assert res.factors == [13]


def test_factorise_composite_large():
    """Verify functionality of factorise_composite_large."""
    res = factorise(123456789, DEFAULT)
    assert res.factors == [3, 3607, 3803]


def test_factorise_powers_of_2_and_3():
    """Verify functionality of factorise_powers_of_2_and_3."""
    res = factorise(24, DEFAULT)
    assert res.factors == [2, 3]


def test_factorise_perfect_square():
    """Verify functionality of factorise_perfect_square."""
    res = factorise(121, DEFAULT)
    assert res.factors == [11]


def test_factorise_zero_one():
    """Verify functionality of factorise_zero_one."""
    assert not factorise(0, DEFAULT).factors
    assert not factorise(1, DEFAULT).factors


def test_factorise_negative():
    """Verify functionality of factorise_negative."""
    res = factorise(-12, DEFAULT)
    assert res.sign == -1
    assert res.factors == [2, 3]


def test_factorise_original_preserved():
    """Verify functionality of factorise_original_preserved."""
    for n in [0, 1, -1, 2, -12, 123456789]:
        assert factorise(n, DEFAULT).original == n


@pytest.mark.parametrize("n,expected_sign", [(2, 1), (100, 1), (-2, -1), (-100, -1)])
def test_factorise_sign(n: int, expected_sign: int):
    """Verify functionality of factorise_sign."""
    assert factorise(n, DEFAULT).sign == expected_sign


@pytest.mark.parametrize(
    "n, expected_factors, expected_powers",
    [
        (12, [2, 3], {2: 2, 3: 1}),
        (24, [2, 3], {2: 3, 3: 1}),
        (8, [2], {2: 3}),
        (360, [2, 3, 5], {2: 3, 3: 2, 5: 1}),
        (123456789, [3, 3607, 3803], {3: 2, 3607: 1, 3803: 1}),
        (30030, [2, 3, 5, 7, 11, 13], {2: 1, 3: 1, 5: 1, 7: 1, 11: 1, 13: 1}),
        (97, [97], {97: 1}),
        (1, [], {}),
        (-1, [], {}),
        (-12, [2, 3], {2: 2, 3: 1}),
        (0, [], {}),
    ],
)
def test_factorise_factors_and_powers(
    n: int, expected_factors: list[int], expected_powers: dict[int, int]
):
    """Verify functionality of factorise_factors_and_powers."""
    res = factorise(n, DEFAULT)
    assert res.factors == expected_factors
    assert res.powers == expected_powers
    assert all(is_prime(f) for f in res.factors)
    if res.factors:
        reconstructed_product = product((p**e for p, e in res.powers.items()))
        assert reconstructed_product == abs(n)


@pytest.mark.parametrize("n", [12, 60, 360, 2**10, 3**7, 2**5 * 3**3 * 7])
def test_factorise_powers_consistent_with_factors(n: int):
    """Verify functionality of factorise_powers_consistent_with_factors."""
    res = factorise(n, DEFAULT)
    reconstructed = sorted((p for p, e in res.powers.items() for _ in range(e)))
    assert sorted(set(reconstructed)) == res.factors


@pytest.mark.parametrize("p", SMALL_PRIMES + [997, 10**9 + 7])
def test_factorise_is_prime_flag_true_for_primes(p: int):
    """Verify functionality of factorise_is_prime_flag_true_for_primes."""
    assert factorise(p, DEFAULT).is_prime is True


@pytest.mark.parametrize("c", [0, 1, 4, 6, 12, 100, 123456789])
def test_factorise_is_prime_flag_false_for_composites(c: int):
    """Verify functionality of factorise_is_prime_flag_false_for_composites."""
    assert factorise(c, DEFAULT).is_prime is False


@pytest.mark.parametrize("exp", range(1, 20))
def test_factorise_powers_of_two(exp: int):
    """Verify functionality of factorise_powers_of_two."""
    res = factorise(2**exp, DEFAULT)
    assert res.factors == [2]
    assert res.powers == {2: exp}


@pytest.mark.parametrize("exp", range(1, 12))
def test_factorise_powers_of_three(exp: int):
    """Verify functionality of factorise_powers_of_three."""
    assert factorise(3**exp, DEFAULT).factors == [3]


@pytest.mark.parametrize("p", [5, 7, 11, 13, 17, 19, 23])
def test_factorise_prime_squared(p: int):
    """Verify functionality of factorise_prime_squared."""
    res = factorise(p * p, DEFAULT)
    assert res.factors == [p]
    assert res.powers == {p: 2}


def test_factorise_primorial():
    """Verify functionality of factorise_primorial."""
    res = factorise(30030, DEFAULT)
    assert res.factors == [2, 3, 5, 7, 11, 13]


@pytest.mark.parametrize("p,q", [(9973, 9967), (99991, 99989), (999983, 999979)])
def test_factorise_semiprime(p: int, q: int):
    """Verify functionality of factorise_semiprime."""
    res = factorise(p * q, DEFAULT)
    assert sorted(res.factors) == sorted([p, q])


def test_factorise_large_highly_composite():
    """Verify functionality of factorise_large_highly_composite."""
    n = 2**10 * 3**5 * 5**2 * 7
    res = factorise(n, DEFAULT)
    assert res.factors == [2, 3, 5, 7]
    assert res.powers[2] == 10
    assert res.powers[3] == 5
    assert res.powers[5] == 2
    assert res.powers[7] == 1


def test_factorise_large_prime():
    """Verify functionality of factorise_large_prime."""
    p = 32416189987
    assert factorise(p, DEFAULT).is_prime is True


def test_factorise_product_of_two_large_primes():
    """Verify functionality of factorise_product_of_two_large_primes."""
    p, q = (32416189987, 15485863)
    res = factorise(p * q, DEFAULT)
    assert sorted(res.factors) == [q, p]


def test_factorise_zero_structure():
    """Verify functionality of factorise_zero_structure."""
    res = factorise(0, DEFAULT)
    assert res.original == 0
    assert not res.factors
    assert not res.powers
    assert res.is_prime is False


def test_factorise_negative_one():
    """Verify functionality of factorise_negative_one."""
    res = factorise(-1, DEFAULT)
    assert not res.factors
    assert res.is_prime is False


@pytest.mark.parametrize("bad", [None, 1.5, "12", [12], (12,), {12}, True, False])
def test_factorise_invalid_type_raises(bad):
    """Verify functionality of factorise_invalid_type_raises."""
    with pytest.raises(TypeError):
        factorise(bad, DEFAULT)


def test_factorise_uses_provided_config():
    """Verify functionality of factorise_uses_provided_config."""
    cfg = FactoriserConfig(batch_size=64, max_iterations=1000000, max_retries=10)
    res = factorise(60, cfg)
    assert res.factors == [2, 3, 5]


def test_factorise_default_config_from_env():
    """Verify functionality of factorise_default_config_from_env."""
    res = factorise(12)
    assert res.factors == [2, 3]


@pytest.mark.parametrize("n", [12, 997, 123456789, 2**31 - 1, 9973 * 9967])
def test_factorise_is_deterministic(n: int):
    """Verify functionality of factorise_is_deterministic."""
    results = [tuple(factorise(n, DEFAULT).factors) for _ in range(10)]
    assert len(set(results)) == 1


def test_factorise_no_shared_state():
    """Verify functionality of factorise_no_shared_state."""
    res_a = factorise(12, DEFAULT)
    res_b = factorise(60, DEFAULT)
    assert factorise(12, DEFAULT).factors == res_a.factors
    assert factorise(60, DEFAULT).factors == res_b.factors


def test_factorise_thread_safety():
    """Verify functionality of factorise_thread_safety."""
    inputs = [12, 60, 997, 123456789, 2**20, 9973 * 9967]
    expected = {n: tuple(factorise(n, DEFAULT).factors) for n in inputs}
    errors: list[str] = []

    def worker(n: int) -> None:
        for _ in range(20):
            got = tuple(factorise(n, DEFAULT).factors)
            if got != expected[n]:
                errors.append(f"n={n}: got {got}, want {expected[n]}")

    threads = [threading.Thread(target=worker, args=(n,)) for n in inputs]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize("n", [-5, -1, 0, 1])
def test_factor_flatten_below_two(n: int):
    """Verify functionality of factor_flatten_below_two."""
    assert not factor_flatten(n, DEFAULT)


@pytest.mark.parametrize("n", [2, 4, 6, 100, 2**20])
def test_pollard_brent_even_returns_two(n: int):
    """Verify functionality of pollard_brent_even_returns_two."""
    assert pollard_brent(n, DEFAULT) == 2


@pytest.mark.parametrize("p", [3, 5, 7, 97, 997])
def test_pollard_brent_prime_returns_self(p: int):
    """Verify functionality of pollard_brent_prime_returns_self."""
    assert pollard_brent(p, DEFAULT) == p
