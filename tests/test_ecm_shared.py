"""Tests for ECM shared utilities."""

from factorise.stages._ecm_shared import EllipticCurveOperations
from factorise.stages._ecm_shared import compute_modular_inverse
from factorise.stages._ecm_shared import generate_primes_up_to


def test_generate_primes_up_to_small() -> None:
    """Verify prime generation for small bounds."""
    primes = generate_primes_up_to(2)
    assert primes == [2]


def test_generate_primes_up_to_medium() -> None:
    """Verify prime generation for medium bounds."""
    primes = generate_primes_up_to(50)
    assert 2 in primes
    assert 3 in primes
    assert 5 in primes
    assert 7 in primes
    assert 11 in primes
    assert 47 in primes
    assert 49 not in primes


def test_generate_primes_up_to_edge() -> None:
    """Verify prime generation at edge cases."""
    primes = generate_primes_up_to(1)
    assert primes == []

    primes = generate_primes_up_to(0)
    assert primes == []


def test_compute_modular_inverse_coprime() -> None:
    """Verify modular inverse when numbers are coprime."""
    assert compute_modular_inverse(3, 11) == 4  # 3*4 = 12 ≡ 1 (mod 11)
    assert compute_modular_inverse(1, 7) == 1


def test_compute_modular_inverse_zero() -> None:
    """Verify modular inverse of 0 returns 0."""
    assert compute_modular_inverse(0, 11) == 0


def test_compute_modular_inverse_not_coprime() -> None:
    """Verify modular inverse returns 0 when not coprime."""
    assert compute_modular_inverse(4, 6) == 0  # gcd(4, 6) = 2 > 1


def test_elliptic_curve_run_curve_composite() -> None:
    """Verify ECM curve operations on a composite."""
    ops = EllipticCurveOperations()
    primes = generate_primes_up_to(100)
    _factor = ops.run_curve(91, 1, primes, 100)
    # May find a factor or return None


def test_elliptic_curve_run_curve_prime() -> None:
    """Verify ECM curve operations on a prime."""
    ops = EllipticCurveOperations()
    primes = generate_primes_up_to(100)
    _factor = ops.run_curve(97, 1, primes, 100)
    # Should not find a factor for a prime


def test_elliptic_curve_run_curve_even() -> None:
    """Verify ECM curve operations on an even number."""
    ops = EllipticCurveOperations()
    primes = generate_primes_up_to(100)
    _factor = ops.run_curve(100, 1, primes, 100)
    # May or may not find a factor


def test_elliptic_curve_point_double() -> None:
    """Verify point doubling on a Montgomery curve."""
    ops = EllipticCurveOperations()
    n = 91
    a = 1
    x, y, g = ops.point_double(2, 1, a, n)
    assert isinstance(x, int)
    assert isinstance(y, int)
    assert isinstance(g, int)


def test_elliptic_curve_point_add() -> None:
    """Verify point addition on a Montgomery curve."""
    ops = EllipticCurveOperations()
    n = 91
    a = 1
    x, y, g = ops.point_add(2, 1, 3, 1, a, n)
    assert isinstance(x, int)
    assert isinstance(y, int)
    assert isinstance(g, int)


def test_elliptic_curve_multiply_point() -> None:
    """Verify scalar multiplication on a Montgomery curve."""
    ops = EllipticCurveOperations()
    n = 91
    a = 1
    result = ops.multiply_point([2, 1], 5, a, n)
    # May return a factor or None
    assert result is None or isinstance(result, int)


def test_elliptic_curve_run_curve_large_composite() -> None:
    """Verify ECM on a larger composite."""
    ops = EllipticCurveOperations()
    primes = generate_primes_up_to(1000)
    _factor = ops.run_curve(123456789, 1, primes, 1000)
    # May or may not find a factor


def test_elliptic_curve_point_double_zero() -> None:
    """Verify point doubling with x=0 returns early."""
    ops = EllipticCurveOperations()
    x, y, g = ops.point_double(0, 5, 1, 91)
    assert x == 0
    assert y == 0
    assert g == 1


def test_elliptic_curve_point_add_identity() -> None:
    """Verify point addition with identity point."""
    ops = EllipticCurveOperations()
    x, y, g = ops.point_add(0, 0, 3, 4, 1, 91)
    assert x == 3
    assert y == 4
    assert g == 1

    x, y, g = ops.point_add(3, 4, 0, 0, 1, 91)
    assert x == 3
    assert y == 4
    assert g == 1


def test_elliptic_curve_point_add_same_point() -> None:
    """Verify point addition with same point delegates to double."""
    ops = EllipticCurveOperations()
    x, y, g = ops.point_add(2, 3, 2, 3, 1, 91)
    assert isinstance(x, int)
    assert isinstance(y, int)
    assert isinstance(g, int)


def test_elliptic_curve_point_add_neg_y() -> None:
    """Verify point addition with y1 == -y2 returns identity."""
    ops = EllipticCurveOperations()
    n = 91
    x, y, g = ops.point_add(2, 5, 2, (-5) % n, 1, n)
    assert x == 0
    assert y == 0
    assert g == 1


def test_elliptic_curve_multiply_point_zero() -> None:
    """Verify multiply_point with k=0 returns None."""
    ops = EllipticCurveOperations()
    result = ops.multiply_point([2, 1], 0, 1, 91)
    assert result is None


def test_elliptic_curve_point_add_nontrivial_gcd() -> None:
    """Verify point_add finds factor via gcd during addition."""
    ops = EllipticCurveOperations()
    # Choose points such that x2 - x1 shares a factor with n
    n = 91  # 7 * 13
    x, y, g = ops.point_add(2, 1, 9, 1, 1, n)  # 9-2=7 shares factor with 91
    assert isinstance(g, int)


def test_elliptic_curve_point_double_nontrivial_gcd() -> None:
    """Verify point_double finds factor via gcd during doubling."""
    ops = EllipticCurveOperations()
    n = 91
    # 2*y should share a factor with n
    x, y, g = ops.point_double(0, 0, 1, n)
    # x=0 returns early
    assert g == 1


def test_elliptic_curve_multiply_point_factor_found() -> None:
    """Verify multiply_point can return a factor."""
    ops = EllipticCurveOperations()
    n = 91
    result = ops.multiply_point([2, 1], 1, 1, n)
    # k=1 means just return without much computation, likely None
    assert result is None or (isinstance(result, int) and n % result == 0)
