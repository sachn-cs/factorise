"""Shared elliptic curve arithmetic for ECM-based stages.

Provides Montgomery-curve point operations and prime generation used by
ECMStage and TwoPassECMStage. All operations are performed modulo n and
return partial factor discoveries via gcd checks rather than raising.
"""

from __future__ import annotations

import math
import random

from factorise._utils import sieve_primes


def compute_modular_inverse(a: int, n: int) -> int:
    """Return the modular inverse of a modulo n.

    Uses the extended Euclidean algorithm. If a and n are not coprime,
    returns 0 to signal that a factor of n may have been found.

    Args:
        a: The integer to invert.
        n: The modulus (a positive integer).

    Returns:
        The modular inverse of a modulo n, or 0 if gcd(a, n) > 1.

    """
    if a == 0:
        return 0
    t, new_t = 0, 1
    r, new_r = n, a
    while new_r != 0:
        q = r // new_r
        t, new_t = new_t, t - q * new_t
        r, new_r = new_r, r - q * new_r
    if r > 1:
        return 0
    return t if t >= 0 else t + n


def generate_primes_up_to(bound: int) -> list[int]:
    """Return all primes up to bound using the Sieve of Eratosthenes.

    Args:
        bound: The inclusive upper bound for prime generation.

    Returns:
        A sorted list of primes p where 2 <= p <= bound.
        Returns an empty list if bound < 2.

    """
    return sieve_primes(bound)


class EllipticCurveOperations:
    """Shared elliptic curve point operations for ECM stages.

    Implements Montgomery-curve addition and doubling with gcd-aware
    arithmetic. A gcd > 1 during slope computation signals a factor
    discovery and is propagated back to the caller.
    """

    def point_double(
        self,
        x: int,
        y: int,
        a: int,
        n: int,
    ) -> tuple[int, int, int]:
        """Double the point (x, y) on the curve y^2 = x^3 + ax + b (mod n).

        Args:
            x: The x-coordinate of the point.
            y: The y-coordinate of the point.
            a: The curve coefficient a.
            n: The modulus (the composite being factored).

        Returns:
            A tuple (x3, y3, gcd_value) where gcd_value > 1 indicates that
            a non-trivial factor of n was found during the computation.

        """
        if x == 0:
            return (0, 0, 1)
        num = (3 * x * x + a) % n
        denom = (2 * y) % n
        g = math.gcd(denom, n)
        if g > 1:
            return (0, 0, g)
        inv_denom = compute_modular_inverse(denom, n)
        if inv_denom == 0:
            return (0, 0, g if g > 1 else n)
        lam = (num * inv_denom) % n
        x3 = (lam * lam - 2 * x) % n
        y3 = (lam * (x - x3) - y) % n
        return (x3 % n, y3 % n, 1)

    def point_add(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        a: int,
        n: int,
    ) -> tuple[int, int, int]:
        """Add two points (x1, y1) and (x2, y2) on the curve (mod n).

        Args:
            x1: The x-coordinate of the first point.
            y1: The y-coordinate of the first point.
            x2: The x-coordinate of the second point.
            y2: The y-coordinate of the second point.
            a: The curve coefficient a.
            n: The modulus (the composite being factored).

        Returns:
            A tuple (x3, y3, gcd_value) where gcd_value > 1 indicates that
            a non-trivial factor of n was found during the computation.

        """
        if x1 == 0 and y1 == 0:
            return (x2, y2, 1)
        if x2 == 0 and y2 == 0:
            return (x1, y1, 1)
        if x1 == x2:
            if y1 == (-y2) % n:
                return (0, 0, 1)
            return self.point_double(x1, y1, a, n)
        denom = (x2 - x1) % n
        g = math.gcd(denom, n)
        if g > 1:
            return (0, 0, g)
        inv_denom = compute_modular_inverse(denom, n)
        if inv_denom == 0:
            return (0, 0, g if g > 1 else n)
        lam = ((y2 - y1) * inv_denom) % n
        x3 = (lam * lam - x1 - x2) % n
        y3 = (lam * (x1 - x3) - y1) % n
        return (x3 % n, y3 % n, 1)

    def multiply_point(
        self,
        point: list[int],
        k: int,
        a: int,
        n: int,
    ) -> int | None:
        """Scalar multiply a point by k using the Montgomery ladder.

        Args:
            point: A two-element list [x, y] representing the point.
            k: The scalar multiplier.
            a: The curve coefficient a.
            n: The modulus (the composite being factored).

        Returns:
            A non-trivial factor of n if one is discovered during the
            ladder steps, otherwise None.

        """
        if k == 0:
            return None
        x1, y1 = point[0], point[1]
        x2, y2 = x1, y1

        bit = k.bit_length()
        while bit > 0:
            bit -= 1
            if (k >> bit) & 1 == 0:
                x2, y2, f = self.point_add(x2, y2, x1, y1, a, n)
                if f > 1:
                    return f
                x1, y1, f = self.point_double(x1, y1, a, n)
                if f > 1:
                    return f
            else:
                x1, y1, f = self.point_add(x1, y1, x2, y2, a, n)
                if f > 1:
                    return f
                x2, y2, f = self.point_double(x2, y2, a, n)
                if f > 1:
                    return f
        return None

    def run_curve(
        self,
        n: int,
        curve_seed: int,
        primes: list[int],
        _bound: int,
    ) -> int | None:
        """Run one ECM curve and return a factor if found.

        Generates a random Montgomery curve and starting point from the seed,
        then performs stage-1 ECM by multiplying the point by the product of
        all primes in the given list.

        Args:
            n: The composite integer to factor.
            curve_seed: Seed used to derive the random curve parameters.
            primes: List of primes whose product forms the stage-1 multiplier.
            _bound: The smoothness bound (unused, kept for API compatibility).

        Returns:
            A non-trivial factor of n if found, otherwise None.

        """
        rng = random.Random(curve_seed + n)
        a_val = rng.randint(1, n - 1)
        x = rng.randint(1, n - 1)
        y_sq = (x**3 + a_val * x) % n
        y = pow(y_sq, (n + 2) // 8, n)
        if (y * y - y_sq) % n != 0:
            y = pow(y_sq, (n + 5) // 8, n)
        if (y * y - y_sq) % n != 0:
            return None

        k = 1
        for p in primes:
            k *= p
            if k >= n:
                k %= n

        point = [x % n, y % n]
        return self.multiply_point(point, k, a_val, n)
