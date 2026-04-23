"""Shared elliptic curve arithmetic for ECM-based stages."""

from __future__ import annotations

import math


def compute_modular_inverse(a: int, n: int) -> int:
    """Modular inverse of a mod n using extended Euclidean algorithm.

    Returns 0 if a and n are not coprime (i.e., gcd(a, n) > 1).
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
    """Return list of primes up to bound using simple sieve."""
    if bound < 2:
        return []
    sieve = list(range(bound + 1))
    sieve[0] = sieve[1] = 0
    for i in range(2, int(bound**0.5) + 1):
        if sieve[i]:
            for j in range(i * i, bound + 1, i):
                sieve[j] = 0
    return [p for p in sieve if p]


class EllipticCurveOperations:
    """Shared elliptic curve point operations for ECM stages.

    Subclasses must provide a `name` attribute and handle stage result
    construction. Uses Montgomery ladder for constant-time point multiplication.
    """

    name: str

    def point_double(
        self, x: int, y: int, a: int, n: int
    ) -> tuple[int, int, int]:
        """Double point (x, y) on the curve y² = x³ + ax + b (mod n).

        Returns (x3, y3, gcd_value) where gcd_value > 1 if a factor was found.
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
        self, x1: int, y1: int, x2: int, y2: int, a: int, n: int
    ) -> tuple[int, int, int]:
        """Add points (x1, y1) and (x2, y2) on the curve (mod n).

        Returns (x3, y3, gcd_value) where gcd_value > 1 if a factor was found.
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
        self, point: list[int], k: int, a: int, n: int
    ) -> int | None:
        """Multiply point [x,y] by scalar k using Montgomery ladder.

        Returns a factor if a gcd during computation reveals one, else None.
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

    def run_curve(self, n: int, curve_seed: int, primes: list[int], bound: int) -> int | None:
        """Run one ECM curve and return a factor if found, else None.

        Uses the Montgomery ladder approach for efficient point multiplication.
        """
        import random

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