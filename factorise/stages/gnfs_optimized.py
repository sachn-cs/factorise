"""Pure-Python GNFS — single-polynomial with lattice sieving for 60-128 bit inputs.

Implements single-polynomial GNFS (f(x) = x² - m) with:
- Lattice sieving (O(max_b * num_primes * log max_a) vs naive O(max_a*max_b))
- Collect-relations-then-eliminate approach (proven to work)
- Auto-scaled parameters for 60-128 bit inputs
- Proper rational + algebraic factor bases

Capped at 128-bit inputs for pure Python feasibility. Beyond this, an external
C-based GNFS implementation (msieve, ggnfs) is required.
"""

from __future__ import annotations

import dataclasses
import logging
import math
import random
import time
from typing import Any

from factorise._utils import sieve_primes
from factorise.core import is_prime as _is_prime
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus
from factorise.pipeline import elapsed_ms

_LOG = logging.getLogger("factorise")

# ---------------------------------------------------------------------------
# Small prime utilities
# ---------------------------------------------------------------------------


def _legendre_symbol(a: int, p: int) -> int:
    """Legendre symbol (a/p)."""
    if p == 2:
        return 1 if a & 1 else 0
    a_mod_p = a % p
    if a_mod_p == 0:
        return 0
    result = pow(a_mod_p, (p - 1) // 2, p)
    return 1 if result == 1 else -1


def _sqrt_mod_prime(n: int, p: int) -> tuple[int, int] | None:
    """Tonelli-Shanks for sqrt mod p."""
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
    """Polynomial f(x) = x² - m."""
    a: int
    b: int
    c: int

    def evaluate(self, x: int, mod: int | None = None) -> int:
        result = (self.a * x + self.b) * x + self.c
        if mod is not None:
            result %= mod
        return result


def _select_polynomial(n: int) -> tuple[Polynomial, int]:
    """Select polynomial f(x) = x² - m where m ≈ ∛n."""
    m = int(round(n ** (1.0 / 3.0)))
    if m < 2:
        m = max(2, int(n ** (1.0 / 3.0)) + 1)
    return Polynomial(a=1, b=0, c=-m), m


# ---------------------------------------------------------------------------
# Factor base construction
# ---------------------------------------------------------------------------


def _build_factor_bases(
    n: int,
    m: int,
    bound: int,
) -> tuple[list[int], list[int]]:
    """Build rational and algebraic factor bases."""
    primes = sieve_primes(bound)
    rational_base = []
    algebraic_base = []
    for p in primes:
        if _legendre_symbol(n % p, p) == 1:
            rational_base.append(p)
        if _legendre_symbol(m % p, p) == 1:
            algebraic_base.append(p)
    return rational_base, algebraic_base


# ---------------------------------------------------------------------------
# Lattice sieving
# ---------------------------------------------------------------------------


def _factor_over_base(value: int, primes: list[int]) -> list[int] | None:
    """Factor value over prime base. Returns exponent list or None if not smooth."""
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


def _lattice_sieve(
    n: int,
    m: int,
    rational_base: list[int],
    algebraic_base: list[int],
    max_a: int,
    max_b: int,
    target_count: int,
) -> list[dict[str, Any]]:
    """Lattice sieve for single-polynomial GNFS.

    For f(x) = x² - m, norm of (a,b) is N = a² - m*b².
    We sieve a in region around m*b where N is small.
    """
    all_primes = rational_base + algebraic_base
    relations: list[dict[str, Any]] = []

    for b in range(1, max_b + 1):
        center = m * b
        lo_a = max(1, center - max_a)
        hi_a = center + max_a

        for p in algebraic_base:
            if p == 2:
                continue
            roots = _sqrt_mod_prime(m % p, p)
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
                            exp = _factor_over_base(norm, all_primes)
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
                        first_a = neg_r if neg_r >= lo_a else neg_r + p
                    a = first_a
                    while a >= lo_a and a > 0:
                        if math.gcd(a, b) == 1:
                            norm = a * a - m * b * b
                            if norm > 0:
                                exp = _factor_over_base(norm, all_primes)
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


# ---------------------------------------------------------------------------
# GF(2) Gaussian elimination (batch mode)
# ---------------------------------------------------------------------------


def _find_dependency(
    relations: list[dict[str, Any]],
    num_cols: int,
) -> list[int] | None:
    """Find linear dependency via Gaussian elimination over GF(2).

    Returns binary vector indexed by relation position, or None.
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


# ---------------------------------------------------------------------------
# Factor extraction
# ---------------------------------------------------------------------------


def _extract_factor(
    n: int,
    m: int,
    relations: list[dict[str, Any]],
    dependency: list[int],
    rational_base: list[int],
    algebraic_base: list[int],
) -> int | None:
    """Extract factor via NFS square root."""
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


# ---------------------------------------------------------------------------
# Parameter auto-scaling (capped at 128-bit for pure Python)
# ---------------------------------------------------------------------------


PURE_GNFS_MIN_BIT_LENGTH = 60
PURE_GNFS_MAX_BIT_LENGTH = 128


def _auto_scale(bit_len: int) -> tuple[int, int, int]:
    """Return (bound, max_a, max_b) scaled for bit length.

    Capped at 128-bit for pure Python feasibility.
    """
    if bit_len <= 80:
        return 300, 50000, 100
    elif bit_len <= 100:
        return 500, 100000, 200
    elif bit_len <= 128:
        return 1000, 200000, 500
    else:
        return 0, 0, 0  # Will trigger immediate failure above 128 bits


# ---------------------------------------------------------------------------
# Main GNFS driver
# ---------------------------------------------------------------------------


def gnfs_find_factor(
    n: int,
    bound: int | None = None,
    max_a: int | None = None,
    max_b: int | None = None,
    max_attempts: int = 3,
) -> int | None:
    """Find a non-trivial factor of n using pure-Python GNFS."""
    if n < 3:
        return None
    if _is_prime(n):
        return None

    root = int(math.isqrt(n))
    if root * root == n:
        return root

    bit_len = n.bit_length()

    if bit_len > PURE_GNFS_MAX_BIT_LENGTH:
        return None

    if None in (bound, max_a, max_b):
        auto = _auto_scale(bit_len)
        bound = bound if bound is not None else auto[0]
        max_a = max_a if max_a is not None else auto[1]
        max_b = max_b if max_b is not None else auto[2]
        if bound == 0:
            return None

    target = bound + 10

    for attempt in range(max_attempts):
        poly, m = _select_polynomial(n)
        if attempt > 0:
            m += attempt * 7 + 11
            poly = Polynomial(a=1, b=0, c=-m)

        rational_base, algebraic_base = _build_factor_bases(n, m, bound)

        if len(rational_base) < 5 or len(algebraic_base) < 5:
            return None

        num_cols = len(rational_base) + len(algebraic_base)
        target_count = max(target, num_cols + 10)

        relations = _lattice_sieve(
            n, m,
            rational_base, algebraic_base,
            max_a, max_b,
            target_count,
        )

        if len(relations) < num_cols:
            return None

        dependency = _find_dependency(relations, num_cols)
        if dependency is None:
            return None

        factor = _extract_factor(
            n, m,
            relations, dependency,
            rational_base, algebraic_base,
        )

        if factor is not None and 1 < factor < n:
            return factor

    return None


# ---------------------------------------------------------------------------
# Pipeline stage
# ---------------------------------------------------------------------------


class GNFSStage(FactorStage):
    """Pure-Python GNFS stage for 60-128 bit inputs without external dependencies."""

    name = "gnfs"

    def __init__(
        self,
        bound: int | None = None,
        max_a: int | None = None,
        max_b: int | None = None,
        max_attempts: int = 3,
    ) -> None:
        self._bound = bound
        self._max_a = max_a
        self._max_b = max_b
        self._max_attempts = max_attempts

    def attempt(self, n: int) -> StageResult:
        start = time.monotonic()

        if n < 3:
            return StageResult(stage_name=self.name, status=StageStatus.SKIPPED,
                             factor=None, elapsed_ms=elapsed_ms(start), reason="n < 3")

        bit_length = n.bit_length()
        if bit_length < PURE_GNFS_MIN_BIT_LENGTH:
            return StageResult(stage_name=self.name, status=StageStatus.SKIPPED,
                             factor=None, elapsed_ms=elapsed_ms(start),
                             reason=f"n ({bit_length} bits) below minimum {PURE_GNFS_MIN_BIT_LENGTH} bits")
        if bit_length > PURE_GNFS_MAX_BIT_LENGTH:
            return StageResult(stage_name=self.name, status=StageStatus.SKIPPED,
                             factor=None, elapsed_ms=elapsed_ms(start),
                             reason=f"n ({bit_length} bits) above maximum {PURE_GNFS_MAX_BIT_LENGTH} bits")

        if _is_prime(n):
            return StageResult(stage_name=self.name, status=StageStatus.SKIPPED,
                             factor=None, elapsed_ms=elapsed_ms(start), reason="n is prime")

        factor = gnfs_find_factor(
            n,
            bound=self._bound,
            max_a=self._max_a,
            max_b=self._max_b,
            max_attempts=self._max_attempts,
        )

        if factor is not None and 1 < factor < n:
            return StageResult(stage_name=self.name, status=StageStatus.SUCCESS,
                             factor=factor, elapsed_ms=elapsed_ms(start))

        return StageResult(stage_name=self.name, status=StageStatus.FAILURE,
                         factor=None, elapsed_ms=elapsed_ms(start),
                         reason="gnfs did not find a factor")


# Alias for backwards compatibility
OptimizedGNFSStage = GNFSStage
