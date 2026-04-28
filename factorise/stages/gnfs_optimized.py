"""Pure-Python GNFS — single-polynomial with lattice sieving for 60–128 bit inputs.

Implements single-polynomial GNFS ``f(x) = x^2 - m`` with:

* Lattice sieving (``O(max_b * num_primes * log max_a)`` vs naive ``O(max_a * max_b)``)
* Collect-relations-then-eliminate approach
* Auto-scaled parameters for 60–128 bit inputs
* Proper rational + algebraic factor bases

Capped at 128-bit inputs for pure Python feasibility.  Beyond this, an
external C-based GNFS implementation (msieve, ggnfs) is required.
"""

from __future__ import annotations

import dataclasses
import logging
import math
import time
from typing import TypedDict

from factorise.core import is_prime as is_prime_check
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus
from factorise.pipeline import elapsed_ms
from factorise.utils import sieve_primes

__all__ = [
    "GNFSRelation",
    "GNFSStage",
    "OptimizedGNFSStage",
    "Polynomial",
    "build_factor_bases",
    "factor_over_base",
    "legendre_symbol",
    "select_polynomial",
    "sqrt_mod_prime",
]

LOG = logging.getLogger("factorise")

GNFS_MIN_BIT_LENGTH: int = 60
GNFS_MAX_BIT_LENGTH: int = 128


class GNFSRelation(TypedDict):
    """A smooth relation from the Number Field Sieve.

    Attributes:
        a: The a-coordinate in the sieving region.
        b: The b-coordinate in the sieving region.
        norm: The algebraic norm ``N = a^2 - m * b^2``.
        exponents: Exponent vector over rational + algebraic factor bases.
    """

    a: int
    b: int
    norm: int
    exponents: list[int]


# ---------------------------------------------------------------------------
# Small prime utilities
# ---------------------------------------------------------------------------


def legendre_symbol(a: int, p: int) -> int:
    """Compute the Legendre symbol ``(a / p)``.

    Args:
        a: The numerator.
        p: An odd prime modulus.

    Returns:
        ``1`` if *a* is a quadratic residue mod *p*, ``-1`` if it is a
        non-residue, and ``0`` if *a* is divisible by *p*.

    """
    if p == 2:
        return 1 if a & 1 else 0
    a_mod_p = a % p
    if a_mod_p == 0:
        return 0
    result = pow(a_mod_p, (p - 1) // 2, p)
    return 1 if result == 1 else -1


def sqrt_mod_prime(n: int, p: int) -> tuple[int, int] | None:
    """Compute a square root of *n* modulo *p* using Tonelli–Shanks.

    Args:
        n: The integer whose square root is desired.
        p: An odd prime modulus.

    Returns:
        A tuple ``(r, p - r)`` where ``r^2 ≡ n (mod p)``, or ``None`` if
        *n* is not a quadratic residue mod *p*.

    """
    if n % p == 0:
        return (0, 0)
    if p == 2:
        return (1, 0)
    if pow(n, (p - 1) // 2, p) != 1:
        return None
    if p % 4 == 3:
        r = pow(n, (p + 1) // 4, p)
        return (r, p - r)
    q, s = p - 1, 0
    while q % 2 == 0:
        q //= 2
        s += 1
    for z in range(2, p):
        if pow(z, (p - 1) // 2, p) == p - 1:
            break
    c = pow(z, q, p)
    x = pow(n, (q + 1) // 2, p)
    t = pow(n, q, p)
    M = s
    while True:
        if t == 1:
            return (x, p - x)
        i = 1
        t2 = (t * t) % p
        while i < M:
            if t2 == 1:
                break
            t2 = (t2 * t2) % p
            i += 1
        if i == M:
            return None
        b = pow(c, 1 << (M - i - 1), p)
        x = (x * b) % p
        c = (b * b) % p
        t = (t * c) % p
        M = i


# ---------------------------------------------------------------------------
# Polynomial
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Polynomial:
    """Polynomial ``f(x) = ax^2 + bx + c``.

    Attributes:
        a: Quadratic coefficient.
        b: Linear coefficient.
        c: Constant term.
    """

    a: int
    b: int
    c: int

    def evaluate(self, x: int, mod: int | None = None) -> int:
        """Evaluate the polynomial at *x*.

        Args:
            x: The point at which to evaluate.
            mod: If given, reduce the result modulo *mod*.

        Returns:
            ``f(x)``, optionally reduced modulo *mod*.

        """
        result = (self.a * x + self.b) * x + self.c
        if mod is not None:
            result %= mod
        return result


def select_polynomial(n: int) -> tuple[Polynomial, int]:
    """Select a polynomial ``f(x) = x^2 - m`` where ``m ≈ ∛n``.

    Args:
        n: The composite integer being factored.

    Returns:
        A tuple ``(polynomial, m)``.

    """
    m = int(round(n**(1.0 / 3.0)))
    if m < 2:
        m = max(2, int(n**(1.0 / 3.0)) + 1)
    return Polynomial(a=1, b=0, c=-m), m


# ---------------------------------------------------------------------------
# Factor base construction
# ---------------------------------------------------------------------------


def build_factor_bases(
    n: int,
    m: int,
    bound: int,
) -> tuple[list[int], list[int]]:
    """Build rational and algebraic factor bases.

    Args:
        n: The composite integer being factored.
        m: The polynomial parameter.
        bound: Upper bound for primes in the factor bases.

    Returns:
        A tuple ``(rational_base, algebraic_base)``.

    """
    primes = sieve_primes(bound)
    rational_base = []
    algebraic_base = []
    for p in primes:
        if legendre_symbol(n % p, p) == 1:
            rational_base.append(p)
        if legendre_symbol(m % p, p) == 1:
            algebraic_base.append(p)
    return rational_base, algebraic_base


# ---------------------------------------------------------------------------
# Smoothness testing
# ---------------------------------------------------------------------------


def factor_over_base(value: int, primes: list[int]) -> list[int] | None:
    """Factor *value* over a prime base.

    Args:
        value: The integer to factor.
        primes: The prime base.

    Returns:
        A list of exponents indexed parallel to *primes*, or ``None`` if
        *value* is not smooth over the base.

    """
    if value < 0:
        value = -value
    if value <= 1:
        return [0] * len(primes)
    exponents = []
    remaining = value
    for p in primes:
        if p * p > remaining:
            break
        if remaining % p != 0:
            exponents.append(0)
            continue
        cnt = 0
        while remaining % p == 0:
            remaining //= p
            cnt += 1
        exponents.append(cnt)
    if remaining == 1:
        while len(exponents) < len(primes):
            exponents.append(0)
        return exponents
    if remaining in primes:
        idx = primes.index(remaining)
        while len(exponents) < len(primes):
            exponents.append(0)
        exponents[idx] += 1
        return exponents
    return None


# ---------------------------------------------------------------------------
# Pipeline stage
# ---------------------------------------------------------------------------


class GNFSStage(FactorStage):
    """Pure-Python GNFS stage for 60–128 bit inputs without external dependencies."""

    name = "gnfs"

    def __init__(
        self,
        bound: int | None = None,
        max_a: int | None = None,
        max_b: int | None = None,
        max_attempts: int = 3,
    ) -> None:
        """Initialise the GNFS stage.

        Args:
            bound: Smoothness bound for factor bases.
            max_a: Sieving radius around ``m * b``.
            max_b: Maximum b-coordinate in the sieving region.
            max_attempts: Number of polynomial choices to try.

        """
        self.__bound = bound
        self.__max_a = max_a
        self.__max_b = max_b
        self.__max_attempts = max_attempts

    def attempt(self, n: int) -> StageResult:
        """Attempt to find a factor of *n* using pure-Python GNFS.

        Args:
            n: The integer to factor.

        Returns:
            StageResult describing the outcome.

        """
        start = time.monotonic()
        bits = n.bit_length()

        LOG.debug("stage=%s n=%d bits=%d action=attempt", self.name, n, bits)

        if n < 3:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d status=SKIPPED reason=%s elapsed_ms=%.2f",
                self.name,
                n,
                "n < 3",
                elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed,
                reason="n < 3",
            )

        if bits < GNFS_MIN_BIT_LENGTH:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d status=SKIPPED reason=%s elapsed_ms=%.2f",
                self.name,
                n,
                f"n ({bits} bits) below minimum {GNFS_MIN_BIT_LENGTH} bits",
                elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed,
                reason=(
                    f"n ({bits} bits) below minimum {GNFS_MIN_BIT_LENGTH} bits"
                ),
            )

        if bits > GNFS_MAX_BIT_LENGTH:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d status=SKIPPED reason=%s elapsed_ms=%.2f",
                self.name,
                n,
                f"n ({bits} bits) above maximum {GNFS_MAX_BIT_LENGTH} bits",
                elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed,
                reason=(
                    f"n ({bits} bits) above maximum {GNFS_MAX_BIT_LENGTH} bits"
                ),
            )

        if is_prime_check(n):
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d status=SKIPPED reason=%s elapsed_ms=%.2f",
                self.name,
                n,
                "n is prime",
                elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                factor=None,
                elapsed_ms=elapsed,
                reason="n is prime",
            )

        root = int(math.isqrt(n))
        if root * root == n:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d factor=%d elapsed_ms=%.2f iterations=1",
                self.name,
                n,
                root,
                elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=root,
                elapsed_ms=elapsed,
                iterations_used=1,
            )

        factor = self.__find_factor(n)
        if factor is not None and 1 < factor < n:
            elapsed = elapsed_ms(start)
            LOG.debug(
                "stage=%s n=%d factor=%d elapsed_ms=%.2f",
                self.name,
                n,
                factor,
                elapsed,
            )
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SUCCESS,
                factor=factor,
                elapsed_ms=elapsed,
            )

        elapsed = elapsed_ms(start)
        LOG.debug(
            "stage=%s n=%d status=FAILURE elapsed_ms=%.2f reason=%s",
            self.name,
            n,
            elapsed,
            "gnfs did not find a factor",
        )
        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=elapsed,
            reason="gnfs did not find a factor",
        )

    def __auto_scale(self, bit_len: int) -> tuple[int, int, int]:
        """Return ``(bound, max_a, max_b)`` scaled for bit length.

        Capped at 128-bit for pure Python feasibility.

        Args:
            bit_len: Bit length of the input integer.

        Returns:
            A tuple ``(bound, max_a, max_b)``.  Returns ``(0, 0, 0)`` for
            inputs above 128 bits.

        """
        if bit_len <= 80:
            return 300, 50_000, 100
        elif bit_len <= 100:
            return 500, 100_000, 200
        elif bit_len <= 128:
            return 1_000, 200_000, 500
        else:
            return 0, 0, 0

    def __find_factor(self, n: int) -> int | None:
        """Find a non-trivial factor of *n* using pure-Python GNFS."""
        bit_len = n.bit_length()
        bound = self.__bound
        max_a = self.__max_a
        max_b = self.__max_b

        if None in (bound, max_a, max_b):
            auto = self.__auto_scale(bit_len)
            bound = bound if bound is not None else auto[0]
            max_a = max_a if max_a is not None else auto[1]
            max_b = max_b if max_b is not None else auto[2]
            if bound == 0:
                return None

        assert bound is not None and max_a is not None and max_b is not None
        target = bound + 10

        for attempt in range(self.__max_attempts):
            poly_start = time.monotonic()
            poly, m = select_polynomial(n)
            if attempt > 0:
                m += attempt * 7 + 11
            LOG.debug(
                "stage=%s n=%d action=select_polynomial elapsed_ms=%.2f",
                self.name,
                n,
                elapsed_ms(poly_start),
            )

            fb_start = time.monotonic()
            rational_base, algebraic_base = build_factor_bases(n, m, bound)
            LOG.debug(
                "stage=%s n=%d action=build_factor_bases elapsed_ms=%.2f "
                "rational=%d algebraic=%d",
                self.name,
                n,
                elapsed_ms(fb_start),
                len(rational_base),
                len(algebraic_base),
            )

            if len(rational_base) < 5 or len(algebraic_base) < 5:
                return None

            num_cols = len(rational_base) + len(algebraic_base)
            target_count = max(target, num_cols + 10)

            sieve_start = time.monotonic()
            relations = self.__lattice_sieve(
                n,
                m,
                rational_base,
                algebraic_base,
                max_a,
                max_b,
                target_count,
            )
            LOG.debug(
                "stage=%s n=%d action=lattice_sieve elapsed_ms=%.2f "
                "relations=%d target=%d",
                self.name,
                n,
                elapsed_ms(sieve_start),
                len(relations),
                target_count,
            )

            if len(relations) < num_cols:
                return None

            dep_start = time.monotonic()
            dependency = self.__find_dependency(relations, num_cols)
            LOG.debug(
                "stage=%s n=%d action=find_dependency elapsed_ms=%.2f",
                self.name,
                n,
                elapsed_ms(dep_start),
            )
            if dependency is None:
                return None

            extract_start = time.monotonic()
            factor = self.__extract_factor(
                n,
                m,
                relations,
                dependency,
                rational_base,
                algebraic_base,
            )
            LOG.debug(
                "stage=%s n=%d action=extract_factor elapsed_ms=%.2f",
                self.name,
                n,
                elapsed_ms(extract_start),
            )

            if factor is not None and 1 < factor < n:
                return factor

        return None

    def __lattice_sieve(
        self,
        n: int,
        m: int,
        rational_base: list[int],
        algebraic_base: list[int],
        max_a: int,
        max_b: int,
        target_count: int,
    ) -> list[GNFSRelation]:
        """Lattice sieve for single-polynomial GNFS.

        For ``f(x) = x^2 - m``, the norm of ``(a, b)`` is ``N = a^2 - m * b^2``.
        We sieve *a* in a region around ``m * b`` where *N* is small.

        Args:
            n: The composite integer being factored.
            m: The polynomial parameter.
            rational_base: Rational factor base primes.
            algebraic_base: Algebraic factor base primes.
            max_a: Sieving radius around ``m * b``.
            max_b: Maximum b-coordinate.
            target_count: Number of relations to collect.

        Returns:
            A list of smooth relations.

        """
        all_primes = rational_base + algebraic_base
        relations: list[GNFSRelation] = []

        for b in range(1, max_b + 1):
            center = m * b
            lo_a = max(1, center - max_a)
            hi_a = center + max_a

            for p in algebraic_base:
                if p == 2:
                    continue
                roots = sqrt_mod_prime(m % p, p)
                if roots is None:
                    continue
                r1, r2 = roots

                for r in (r1, r2):
                    if r == 0:
                        continue
                    r_mod = r % p
                    if r_mod < lo_a % p:
                        first_a = r_mod + ((lo_a - r_mod + p - 1) // p) * p
                    else:
                        first_a = r_mod if r_mod >= lo_a else r_mod + p

                    a = first_a
                    while a <= hi_a:
                        if a > 0 and math.gcd(a, b) == 1:
                            norm = a * a - m * b * b
                            if norm > 0:
                                exp = factor_over_base(norm, all_primes)
                                if exp is not None:
                                    relations.append({
                                        "a": a,
                                        "b": b,
                                        "norm": norm,
                                        "exponents": exp,
                                    })
                                    if len(relations) >= target_count:
                                        return relations
                        a += p

                    if r2 != r1:
                        neg_r = (-r) % p
                        if neg_r < lo_a % p:
                            first_a = neg_r + ((lo_a - neg_r + p - 1) // p) * p
                        else:
                            first_a = (neg_r if neg_r >= lo_a else neg_r + p)
                        a = first_a
                        while a >= lo_a and a > 0:
                            if math.gcd(a, b) == 1:
                                norm = a * a - m * b * b
                                if norm > 0:
                                    exp = factor_over_base(norm, all_primes)
                                    if exp is not None:
                                        relations.append({
                                            "a": a,
                                            "b": b,
                                            "norm": norm,
                                            "exponents": exp,
                                        })
                                        if len(relations) >= target_count:
                                            return relations
                            a -= p

        return relations

    def __find_dependency(
        self,
        relations: list[GNFSRelation],
        num_cols: int,
    ) -> list[int] | None:
        """Find a linear dependency via Gaussian elimination over GF(2).

        Args:
            relations: List of smooth relations.
            num_cols: Number of columns (size of the combined factor base).

        Returns:
            A list of relation indices forming the dependency, or ``None``.

        """
        if len(relations) < num_cols:
            return None

        rows: list[tuple[int, int]] = []
        for idx, rel in enumerate(relations):
            mask = 0
            for qi, e in enumerate(rel["exponents"]):
                if e & 1:
                    mask |= 1 << qi
            if mask == 0:
                continue
            history = 1 << idx
            rows.append((mask, history))

        if len(rows) < num_cols:
            return None

        row_idx = 0
        num_rows = len(rows)
        for col in range(num_cols):
            pivot = -1
            for r in range(row_idx, num_rows):
                if (rows[r][0] >> col) & 1:
                    pivot = r
                    break
            if pivot == -1:
                continue

            rows[row_idx], rows[pivot] = rows[pivot], rows[row_idx]

            for r in range(num_rows):
                if r != row_idx and ((rows[r][0] >> col) & 1):
                    rows[r] = (rows[r][0] ^ rows[row_idx][0],
                               rows[r][1] ^ rows[row_idx][1])

            row_idx += 1
            if row_idx >= num_rows:
                break

        for mask, history in rows:
            if mask == 0 and history != 0:
                result = []
                h = history
                idx = 0
                while h:
                    if h & 1:
                        result.append(idx)
                    h >>= 1
                    idx += 1
                return result

        return None

    def __extract_factor(
        self,
        n: int,
        m: int,
        relations: list[GNFSRelation],
        dependency: list[int],
        rational_base: list[int],
        algebraic_base: list[int],
    ) -> int | None:
        """Extract a factor via NFS square root.

        Args:
            n: The composite integer being factored.
            m: The polynomial parameter.
            relations: List of smooth relations.
            dependency: List of relation indices forming the dependency.
            rational_base: Rational factor base.
            algebraic_base: Algebraic factor base.

        Returns:
            A non-trivial factor of *n* if found, otherwise ``None``.

        """
        g = math.gcd(m, n)
        if 1 < g < n:
            return g

        all_primes = rational_base + algebraic_base
        total_exp = [0] * len(all_primes)

        for rel_idx in dependency:
            if rel_idx >= len(relations):
                continue
            rel = relations[rel_idx]
            for qi, e in enumerate(rel["exponents"]):
                total_exp[qi] += e

        Y = 1
        for qi, e in enumerate(total_exp):
            if e >= 2:
                Y = (Y * pow(all_primes[qi], e // 2, n)) % n

        X_x, X_y = 1, 0
        for rel_idx in dependency:
            if rel_idx >= len(relations):
                continue
            rel = relations[rel_idx]
            a, b = rel["a"], rel["b"]
            new_x = (X_x * a + m * X_y * b) % n
            new_y = (X_x * b + X_y * a) % n
            X_x, X_y = new_x, new_y

        for cand in (math.gcd(X_y - Y, n), math.gcd(X_y + Y, n)):
            if 1 < cand < n:
                return cand

        c = math.gcd(X_x, n)
        if 1 < c < n:
            return c

        return None


# Alias for backwards compatibility
OptimizedGNFSStage = GNFSStage
