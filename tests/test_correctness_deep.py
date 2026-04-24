"""Deterministic deep correctness tests for large bit-depths.

These tests verify the algorithm's ability to factorise semiprimes and
composites in the 64-128 bit range. Primes used are selected to ensure
Pollard-Brent completion within CI time limits.
"""

import pytest

from factorise.core import FactoriserConfig
from factorise.core import factorise

# High-precision prime constants verified for this suite
P31 = 2147483647  # 2^31 - 1
P43 = 8796093022151  # Near 2^43
P47 = 140737488355213  # 2^47 - 115
P61 = 2305843009213693951  # 2^61 - 1

# Deterministic config for stable CI execution
DEEP_CONFIG = FactoriserConfig(seed=42, max_iterations=5_000_000)


@pytest.mark.parametrize(
    "p, q, label",
    [
        (P31, P31, "62-bit semiprime"),
        (P61, P31, "92-bit semiprime"),
        (P61, P43, "104-bit semiprime"),
    ],
)
def test_correctness_large_semiprimes(p: int, q: int, label: str) -> None:
    """Verify factorisation of large semiprimes up to 104 bits."""
    n = p * q
    result = factorise(n, DEEP_CONFIG)
    # result.factors is unique primes; p, q might be same
    expected = sorted({p, q})
    assert result.factors == expected, f"Failed {label} factors"
    assert result.original == n

    # Also verify powers sum to 2 for a semiprime
    assert sum(result.powers.values()) == 2


def test_correctness_124_bit_composite() -> None:
    """Verify factorisation of a 124-bit three-factor composite.

    n = P61 * P31 * P31
    """
    n = P61 * P31 * P31
    result = factorise(n, DEEP_CONFIG)
    assert sorted(result.factors) == sorted([P31, P61])
    assert result.powers[P31] == 2
    assert result.powers[P61] == 1
    assert result.original == n


@pytest.mark.parametrize("p", [P47, P61])
def test_correctness_large_primes(p: int) -> None:
    """Verify primality detection for known large primes near 64 bits."""
    result = factorise(p, DEEP_CONFIG)
    assert result.is_prime is True
    assert result.factors == [p]


def test_correctness_powers_of_large_prime() -> None:
    """Verify factorisation of P31^3 (93 bits)."""
    n = P31**3
    result = factorise(n, DEEP_CONFIG)
    assert result.factors == [P31]
    assert result.powers[P31] == 3
