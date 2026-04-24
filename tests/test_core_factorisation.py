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
    """Verify factorisation for small composite integers."""
    res = factorise(12, DEFAULT_CONFIG)
    assert res.factors == [2, 3]
    assert res.powers == {2: 2, 3: 1}


def test_factorise_prime() -> None:
    """Verify that prime inputs return themselves as the single factor."""
    res = factorise(13, DEFAULT_CONFIG)
    assert res.is_prime is True
    assert res.factors == [13]


def test_factorise_composite_large() -> None:
    """Verify factorisation for large composite integers using Pollard-Brent."""
    res = factorise(123456789, DEFAULT_CONFIG)
    assert res.factors == [3, 3607, 3803]


def test_factorise_powers_of_2_and_3() -> None:
    """Verify factorisation for numbers composed of small prime powers."""
    res = factorise(24, DEFAULT_CONFIG)
    assert res.factors == [2, 3]


def test_factorise_perfect_square() -> None:
    """Verify that perfect squares are correctly factorized into prime powers."""
    res = factorise(121, DEFAULT_CONFIG)
    assert res.factors == [11]


def test_factorise_zero_one() -> None:
    """Verify that 0 and 1 return an empty factor list."""
    assert not factorise(0, DEFAULT_CONFIG).factors
    assert not factorise(1, DEFAULT_CONFIG).factors


def test_factorise_negative() -> None:
    """Verify factorisation of negative integers (sign preservation)."""
    res = factorise(-12, DEFAULT_CONFIG)
    assert res.sign == -1
    assert res.factors == [2, 3]


def test_factorise_original_preserved() -> None:
    """Verify that the original input is preserved in the result model."""
    for n in [0, 1, -1, 2, -12, 123456789]:
        assert factorise(n, DEFAULT_CONFIG).original == n


@pytest.mark.parametrize("n,expected_sign", [(2, 1), (100, 1), (-2, -1),
                                             (-100, -1)])
def test_factorise_sign(n: int, expected_sign: int) -> None:
    assert factorise(n, DEFAULT_CONFIG).sign == expected_sign


@pytest.mark.parametrize(
    "n, expected_factors, expected_powers",
    [
        (12, [2, 3], {
            2: 2,
            3: 1
        }),
        (24, [2, 3], {
            2: 3,
            3: 1
        }),
        (8, [2], {
            2: 3
        }),
        (360, [2, 3, 5], {
            2: 3,
            3: 2,
            5: 1
        }),
        (123456789, [3, 3607, 3803], {
            3: 2,
            3607: 1,
            3803: 1
        }),
        (30030, [2, 3, 5, 7, 11, 13], {
            2: 1,
            3: 1,
            5: 1,
            7: 1,
            11: 1,
            13: 1
        }),
        (97, [97], {
            97: 1
        }),
        (1, [], {}),
        (-1, [], {}),
        (-12, [2, 3], {
            2: 2,
            3: 1
        }),
        (0, [], {}),
    ],
)
def test_factorise_factors_and_powers(
    n: int,
    expected_factors: list[int],
    expected_powers: dict[int, int],
) -> None:
    """Verify factors and powers for various inputs via parameterization."""
    res = factorise(n, DEFAULT_CONFIG)
    assert res.factors == expected_factors
    assert res.powers == expected_powers
    assert all(is_prime(factor) for factor in res.factors)
    if res.factors:
        reconstructed_product = _product(
            (prime**power for prime, power in res.powers.items()))
        assert reconstructed_product == abs(n)


@pytest.mark.parametrize("n", [12, 60, 360, 2**10, 3**7, 2**5 * 3**3 * 7])
def test_factorise_powers_consistent_with_factors(n: int) -> None:
    """Verify that the powers dictionary is consistent with the factor list."""
    res = factorise(n, DEFAULT_CONFIG)
    reconstructed = sorted(
        (prime for prime, power in res.powers.items() for _ in range(power)))
    assert sorted(set(reconstructed)) == res.factors


@pytest.mark.parametrize("p", SMALL_PRIMES + [997, 10**9 + 7])
def test_factorise_is_prime_flag_true_for_primes(p: int) -> None:
    """Verify that the is_prime flag is correctly set for prime inputs."""
    assert factorise(p, DEFAULT_CONFIG).is_prime is True


@pytest.mark.parametrize("c", [0, 1, 4, 6, 12, 100, 123456789])
def test_factorise_is_prime_flag_false_for_composites(c: int) -> None:
    """Verify that the is_prime flag is correctly cleared for composite inputs."""
    assert factorise(c, DEFAULT_CONFIG).is_prime is False


@pytest.mark.parametrize("exp", range(1, 20))
def test_factorise_powers_of_two(exp: int) -> None:
    """Verify and stress test factorisation of powers of 2."""
    res = factorise(2**exp, DEFAULT_CONFIG)
    assert res.factors == [2]
    assert res.powers == {2: exp}


@pytest.mark.parametrize("exp", range(1, 12))
def test_factorise_powers_of_three(exp: int) -> None:
    """Verify factorisation of powers of 3."""
    assert factorise(3**exp, DEFAULT_CONFIG).factors == [3]


@pytest.mark.parametrize("p", [5, 7, 11, 13, 17, 19, 23])
def test_factorise_prime_squared(p: int) -> None:
    """Verify factorisation for squares of primes."""
    res = factorise(p * p, DEFAULT_CONFIG)
    assert res.factors == [p]
    assert res.powers == {p: 2}


def test_factorise_primorial() -> None:
    """Verify factorisation for a primorial (product of first k primes)."""
    res = factorise(30030, DEFAULT_CONFIG)
    assert res.factors == [2, 3, 5, 7, 11, 13]


@pytest.mark.parametrize("p,q", [(9973, 9967), (99991, 99989),
                                 (999983, 999979)])
def test_factorise_semiprime(p: int, q: int) -> None:
    """Verify factorisation of semiprimes (p * q)."""
    res = factorise(p * q, DEFAULT_CONFIG)
    assert sorted(res.factors) == sorted([p, q])


def test_factorise_large_highly_composite() -> None:
    """Verify factorisation of highly composite large numbers."""
    n = 2**10 * 3**5 * 5**2 * 7
    res = factorise(n, DEFAULT_CONFIG)
    assert res.factors == [2, 3, 5, 7]
    assert res.powers[2] == 10
    assert res.powers[3] == 5
    assert res.powers[5] == 2
    assert res.powers[7] == 1


def test_factorise_large_prime() -> None:
    """Verify primality detection for a large unsigned 64-bit prime."""
    p = 32416189987
    assert factorise(p, DEFAULT_CONFIG).is_prime is True


def test_factorise_product_of_two_large_primes() -> None:
    """Verify factorisation for the product of two large distant primes."""
    p, q = (32416189987, 15485863)
    res = factorise(p * q, DEFAULT_CONFIG)
    assert sorted(res.factors) == [q, p]


def test_factorise_zero_structure() -> None:
    """Verify the structural invariants of the result model for input 0."""
    res = factorise(0, DEFAULT_CONFIG)
    assert res.original == 0
    assert not res.factors
    assert not res.powers
    assert res.is_prime is False


def test_factorise_negative_one() -> None:
    """Verify factorisation for input -1."""
    res = factorise(-1, DEFAULT_CONFIG)
    assert not res.factors
    assert res.is_prime is False


@pytest.mark.parametrize("bad",
                         [None, 1.5, "12", [12], (12,), {12}, True, False])
def test_factorise_invalid_type_raises(bad: object) -> None:
    """Verify that factorise raises TypeError for non-integer inputs."""
    with pytest.raises(TypeError):
        factorise(bad, DEFAULT_CONFIG)  # type: ignore[arg-type]


def test_factorise_uses_provided_config() -> None:
    """Verify that factorise respects the FactoriserConfig instance if provided."""
    cfg = FactoriserConfig(batch_size=64,
                           max_iterations=1000000,
                           max_retries=10)
    res = factorise(60, cfg)
    assert res.factors == [2, 3, 5]


def test_factorise_invalid_config_type_raises() -> None:
    """Verify that an invalid config type results in a defensive TypeError."""
    with pytest.raises(TypeError):
        factorise(60, config=cast(FactoriserConfig, object()))


def test_factorise_default_config_from_env() -> None:
    """Verify that factorise correctly bootstraps config from env when none is passed."""
    res = factorise(12)
    assert res.factors == [2, 3]


@pytest.mark.parametrize("n", [12, 997, 123456789, 2**31 - 1, 9973 * 9967])
def test_factorise_is_deterministic(n: int) -> None:
    """Verify that factorisation is bit-deterministic across many calls."""
    results = [tuple(factorise(n, DEFAULT_CONFIG).factors) for _ in range(10)]
    assert len(set(results)) == 1


def test_factorise_no_shared_state() -> None:
    """Verify that multiple factorise calls do not pollute shared state."""
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
    expected = {
        n: tuple(factorise(n, DEFAULT_CONFIG).factors) for n in thread_inputs
    }
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
        threading.Thread(target=worker, args=(n,))
        for n in thread_inputs
        for _ in range(per_input_threads)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=THREAD_JOIN_TIMEOUT_SECONDS)
        if thread.is_alive():
            raise ThreadNotJoinedError(
                f"thread {thread.name} did not finish within timeout")
    assert not errors, "\n".join(errors)
