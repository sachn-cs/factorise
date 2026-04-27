"""Primality testing behavior for factorise.core.is_prime."""

import math
from typing import cast

import pytest

from factorise.core import is_prime

SMALL_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
SMALL_COMPOSITES = [4, 6, 8, 9, 10, 12, 14, 15, 16, 18, 20, 25, 49, 77, 100]


def _is_prime_naive(n: int) -> bool:
    if n < 2:
        return False
    return all(n % i != 0 for i in range(2, math.isqrt(n) + 1))


@pytest.mark.parametrize("n", [-1000000, -1, 0, 1])
def test_is_prime_below_two_is_false(n: int) -> None:
    """Verify that numbers below 2 are never considered prime."""
    assert is_prime(n) is False


@pytest.mark.parametrize("p", SMALL_PRIMES)
def test_is_prime_small_primes(p: int) -> None:
    """Verify primality for a curated list of small primes."""
    assert is_prime(p) is True


@pytest.mark.parametrize("c", SMALL_COMPOSITES)
def test_is_prime_small_composites(c: int) -> None:
    """Verify that small composite numbers are not marked as prime."""
    assert is_prime(c) is False


def test_is_prime_agrees_with_naive_up_to_500() -> None:
    """Verify algorithm consistency against a naive implementation for small n."""
    for n in range(2, 501):
        assert is_prime(n) == _is_prime_naive(n), f"Mismatch at n={n}"


@pytest.mark.parametrize("p", [10**9 + 7, 10**9 + 9, 2**31 - 1, 32416189987])
def test_is_prime_large_primes(p: int) -> None:
    """Verify correct primality detection for known large primes."""
    assert is_prime(p) is True


@pytest.mark.parametrize("c", [10**9 + 8, 4000000000, 2**31, 100000000000])
def test_is_prime_large_composites(c: int) -> None:
    """Verify correct detection of large composite numbers."""
    assert is_prime(c) is False


@pytest.mark.parametrize("bad", [None, 1.5, "5", [], True, False])
def test_is_prime_invalid_type_raises(bad: object) -> None:
    """Verify that is_prime raises TypeError for non-integer inputs."""
    with pytest.raises(TypeError):
        is_prime(cast(int, bad))


@pytest.mark.parametrize("n", [97, 121, 2**31 - 1, 10**9 + 7])
def test_is_prime_is_deterministic(n: int) -> None:
    """Verify that the primality test is deterministic across many repeats."""
    assert len({is_prime(n) for _ in range(20)}) == 1
