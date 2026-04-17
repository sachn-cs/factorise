"""Factorisation result behavior tests for factorise.core.factorise."""

import threading
from collections.abc import Iterable
from functools import reduce
from typing import cast

import pytest

from factorise.core import FactoriserConfig
from factorise.core import factorise
from factorise.core import is_prime
from tests.conftest import DEFAULT_CONFIG

SMALL_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
THREAD_JOIN_TIMEOUT_SECONDS = 15.0


class ThreadNotJoinedError(RuntimeError):
    """Raised when a worker thread fails to join within timeout."""


def _product(factors: Iterable[int]) -> int:
    return reduce(lambda a, b: a * b, factors, 1)


def test_factorise_small() -> None:
    res = factorise(12, DEFAULT_CONFIG)
    assert res.factors == [2, 3]
    assert res.powers == {2: 2, 3: 1}


def test_factorise_prime() -> None:
    res = factorise(13, DEFAULT_CONFIG)
    assert res.is_prime is True
    assert res.factors == [13]


def test_factorise_composite_large() -> None:
    res = factorise(123456789, DEFAULT_CONFIG)
    assert res.factors == [3, 3607, 3803]


def test_factorise_powers_of_2_and_3() -> None:
    res = factorise(24, DEFAULT_CONFIG)
    assert res.factors == [2, 3]


def test_factorise_perfect_square() -> None:
    res = factorise(121, DEFAULT_CONFIG)
    assert res.factors == [11]


def test_factorise_zero_one() -> None:
    assert not factorise(0, DEFAULT_CONFIG).factors
    assert not factorise(1, DEFAULT_CONFIG).factors


def test_factorise_negative() -> None:
    res = factorise(-12, DEFAULT_CONFIG)
    assert res.sign == -1
    assert res.factors == [2, 3]


def test_factorise_original_preserved() -> None:
    for n in [0, 1, -1, 2, -12, 123456789]:
        assert factorise(n, DEFAULT_CONFIG).original == n


@pytest.mark.parametrize("n,expected_sign", [(2, 1), (100, 1), (-2, -1), (-100, -1)])
def test_factorise_sign(n: int, expected_sign: int) -> None:
    assert factorise(n, DEFAULT_CONFIG).sign == expected_sign


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
    n: int,
    expected_factors: list[int],
    expected_powers: dict[int, int],
) -> None:
    res = factorise(n, DEFAULT_CONFIG)
    assert res.factors == expected_factors
    assert res.powers == expected_powers
    assert all(is_prime(factor) for factor in res.factors)
    if res.factors:
        reconstructed_product = _product((prime**power for prime, power in res.powers.items()))
        assert reconstructed_product == abs(n)


@pytest.mark.parametrize("n", [12, 60, 360, 2**10, 3**7, 2**5 * 3**3 * 7])
def test_factorise_powers_consistent_with_factors(n: int) -> None:
    res = factorise(n, DEFAULT_CONFIG)
    reconstructed = sorted((prime for prime, power in res.powers.items() for _ in range(power)))
    assert sorted(set(reconstructed)) == res.factors


@pytest.mark.parametrize("p", SMALL_PRIMES + [997, 10**9 + 7])
def test_factorise_is_prime_flag_true_for_primes(p: int) -> None:
    assert factorise(p, DEFAULT_CONFIG).is_prime is True


@pytest.mark.parametrize("c", [0, 1, 4, 6, 12, 100, 123456789])
def test_factorise_is_prime_flag_false_for_composites(c: int) -> None:
    assert factorise(c, DEFAULT_CONFIG).is_prime is False


@pytest.mark.parametrize("exp", range(1, 20))
def test_factorise_powers_of_two(exp: int) -> None:
    res = factorise(2**exp, DEFAULT_CONFIG)
    assert res.factors == [2]
    assert res.powers == {2: exp}


@pytest.mark.parametrize("exp", range(1, 12))
def test_factorise_powers_of_three(exp: int) -> None:
    assert factorise(3**exp, DEFAULT_CONFIG).factors == [3]


@pytest.mark.parametrize("p", [5, 7, 11, 13, 17, 19, 23])
def test_factorise_prime_squared(p: int) -> None:
    res = factorise(p * p, DEFAULT_CONFIG)
    assert res.factors == [p]
    assert res.powers == {p: 2}


def test_factorise_primorial() -> None:
    res = factorise(30030, DEFAULT_CONFIG)
    assert res.factors == [2, 3, 5, 7, 11, 13]


@pytest.mark.parametrize("p,q", [(9973, 9967), (99991, 99989), (999983, 999979)])
def test_factorise_semiprime(p: int, q: int) -> None:
    res = factorise(p * q, DEFAULT_CONFIG)
    assert sorted(res.factors) == sorted([p, q])


def test_factorise_large_highly_composite() -> None:
    n = 2**10 * 3**5 * 5**2 * 7
    res = factorise(n, DEFAULT_CONFIG)
    assert res.factors == [2, 3, 5, 7]
    assert res.powers[2] == 10
    assert res.powers[3] == 5
    assert res.powers[5] == 2
    assert res.powers[7] == 1


def test_factorise_large_prime() -> None:
    p = 32416189987
    assert factorise(p, DEFAULT_CONFIG).is_prime is True


def test_factorise_product_of_two_large_primes() -> None:
    p, q = (32416189987, 15485863)
    res = factorise(p * q, DEFAULT_CONFIG)
    assert sorted(res.factors) == [q, p]


def test_factorise_zero_structure() -> None:
    res = factorise(0, DEFAULT_CONFIG)
    assert res.original == 0
    assert not res.factors
    assert not res.powers
    assert res.is_prime is False


def test_factorise_negative_one() -> None:
    res = factorise(-1, DEFAULT_CONFIG)
    assert not res.factors
    assert res.is_prime is False


@pytest.mark.parametrize("bad", [None, 1.5, "12", [12], (12,), {12}, True, False])
def test_factorise_invalid_type_raises(bad: object) -> None:
    with pytest.raises(TypeError):
        factorise(bad, DEFAULT_CONFIG)  # type: ignore[arg-type]


def test_factorise_uses_provided_config() -> None:
    cfg = FactoriserConfig(batch_size=64, max_iterations=1000000, max_retries=10)
    res = factorise(60, cfg)
    assert res.factors == [2, 3, 5]


def test_factorise_invalid_config_type_raises() -> None:
    with pytest.raises(TypeError):
        factorise(60, config=cast(FactoriserConfig, object()))


def test_factorise_default_config_from_env() -> None:
    res = factorise(12)
    assert res.factors == [2, 3]


@pytest.mark.parametrize("n", [12, 997, 123456789, 2**31 - 1, 9973 * 9967])
def test_factorise_is_deterministic(n: int) -> None:
    results = [tuple(factorise(n, DEFAULT_CONFIG).factors) for _ in range(10)]
    assert len(set(results)) == 1


def test_factorise_no_shared_state() -> None:
    res_a = factorise(12, DEFAULT_CONFIG)
    res_b = factorise(60, DEFAULT_CONFIG)
    assert factorise(12, DEFAULT_CONFIG).factors == res_a.factors
    assert factorise(60, DEFAULT_CONFIG).factors == res_b.factors


def test_factorise_thread_safety() -> None:
    """Verify factorise produces correct results under heavy concurrency."""
    num_threads = 20
    iterations = 100
    thread_inputs = [
        2,
        12,
        60,
        997,
        123_456_789,
        2**20,
        9973 * 9967,
        2**31 - 1,
        32_416_189_987,
        15_485_863,
    ]
    expected = {n: tuple(factorise(n, DEFAULT_CONFIG).factors) for n in thread_inputs}
    errors: list[str] = []
    lock = threading.Lock()

    def worker(n: int) -> None:
        for _ in range(iterations):
            got = tuple(factorise(n, DEFAULT_CONFIG).factors)
            if got != expected[n]:
                with lock:
                    errors.append(f"n={n}: got {got}, want {expected[n]}")

    per_input_threads = max(1, num_threads // len(thread_inputs))
    threads = [
        threading.Thread(target=worker, args=(n,)) for n in thread_inputs for _ in range(per_input_threads)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=THREAD_JOIN_TIMEOUT_SECONDS)
        if thread.is_alive():
            raise ThreadNotJoinedError(f"thread {thread.name} did not finish within timeout")
    assert not errors, "\n".join(errors)
