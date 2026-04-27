"""Shared routines for quadratic sieve-based stages.

Provides prime testing, smoothness checking, linear algebra over GF(2),
and factor extraction used by SIQSStage.
"""

from __future__ import annotations

import math
from typing import Any

from factorise._utils import sieve_primes
from factorise.core import is_prime


def is_small_prime(candidate: int) -> bool:
    """Test whether a small integer is prime by trial division.

    Args:
        candidate: The integer to test.

    Returns:
        True if candidate is prime, False otherwise.

    """
    if candidate < 2:
        return False
    if candidate % 2 == 0:
        return candidate == 2
    if candidate % 3 == 0:
        return candidate == 3
    if candidate % 5 == 0:
        return candidate == 5
    if candidate % 7 == 0:
        return candidate == 7
    # Check divisibility up to sqrt(candidate) / 2 since we already tested 2,3,5,7
    limit = int(candidate**0.5) + 1
    divisor = 11
    step = 2  # 11, 13, 17, 19, 23, 25(=5), ...
    while divisor < limit:
        if candidate % divisor == 0:
            return False
        divisor += step
        step = 4 if step == 2 else 2  # alternate between +2 and +4
    return True


def factor_over_base(value: int, prime_base: list[int]) -> list[int] | None:
    """Decompose value completely over the given prime base.

    The first element of the prime base is treated as -1 (sign handling).
    Returns a list of exponents, one per prime in the base, if the value
    factors completely; otherwise returns None.

    Args:
        value: The integer to factor.
        prime_base: A list of primes where the first element is -1.

    Returns:
        A list of exponents indexed parallel to prime_base, or None if
        value has a prime factor outside the base.

    """
    exponents = [0] * len(prime_base)
    remaining = value

    if remaining < 0:
        exponents[0] = 1
        remaining = -remaining

    for index, prime in enumerate(prime_base):
        if prime == -1:
            continue
        if prime * prime > remaining:
            break
        if remaining % prime != 0:
            continue
        count = 0
        while remaining % prime == 0:
            remaining //= prime
            count += 1
        exponents[index] = count

    if remaining == 1:
        return exponents

    # Check if remaining is in prime_base using index lookup
    for idx, p in enumerate(prime_base):
        if p == remaining:
            exponents[idx] += 1
            return exponents

    return None


def find_dependency(
    relations: list[dict[str, Any]],
    num_primes: int,
) -> list[int] | None:
    """Find a linear dependency via Gaussian elimination over GF(2).

    Returns a list of relation indices that form the dependency, or None.

    Args:
        relations: List of relation dicts with "exponents" key.
        num_primes: Size of the prime base.

    Returns:
        List of relation indices in the dependency, or None.

    """
    # Filter to non-trivial relations (have at least one odd exponent)
    non_trivial: list[tuple[int, list[int]]] = []
    for idx, rel in enumerate(relations):
        if any(exp % 2 == 1 for exp in rel["exponents"]):
            non_trivial.append((idx, rel["exponents"]))

    if len(non_trivial) < num_primes:
        return None

    # Build rows: (mask, history_bitmask, original_index)
    rows: list[tuple[int, int, int]] = []
    for orig_idx, rel_exp in non_trivial:
        mask = 0
        for j, exp in enumerate(rel_exp):
            if exp & 1:
                mask |= 1 << j
        if mask == 0:
            continue
        history = 1 << len(rows)
        rows.append((mask, history, orig_idx))

    if len(rows) < num_primes:
        return None

    # Forward elimination
    row_idx = 0
    num_rows = len(rows)
    for col in range(num_primes):
        # Find pivot
        pivot = -1
        for r in range(row_idx, num_rows):
            if (rows[r][0] >> col) & 1:
                pivot = r
                break
        if pivot == -1:
            continue

        # Swap
        rows[row_idx], rows[pivot] = rows[pivot], rows[row_idx]

        # Eliminate
        for r in range(num_rows):
            if r != row_idx and ((rows[r][0] >> col) & 1):
                rows[r] = (rows[r][0] ^ rows[row_idx][0],
                           rows[r][1] ^ rows[row_idx][1],
                           rows[r][2])

        row_idx += 1
        if row_idx >= num_rows:
            break

    # Back-substitution: find zero-mask row with non-zero history
    for mask, history, orig_idx in rows:
        if mask == 0 and history != 0:
            # Extract which non-trivial relations combine to zero
            result: list[int] = []
            h = history
            bit = 0
            while h:
                if h & 1:
                    result.append(non_trivial[bit][0])
                h >>= 1
                bit += 1
            return result

    return None


def extract_factor(
    n: int,
    relations: list[dict[str, Any]],
    dependency: list[int],
    prime_base: list[int],
) -> int | None:
    """Extract a non-trivial factor from a dependency.

    Args:
        n: The composite integer being factored.
        relations: List of relation dicts containing "a" and "exponents".
        dependency: List of relation indices forming the dependency.
        prime_base: The prime base used for factorization.

    Returns:
        A non-trivial factor of n if one is found, otherwise None.

    """
    if not dependency:
        return None

    # Build set of dependency indices for O(1) lookup
    dep_set = set(dependency)

    product_x = 1
    product_y = 1
    for idx, rel in enumerate(relations):
        if idx not in dep_set:
            continue
        product_x = (product_x * rel["a"]) % n
        for prime_idx, exp in enumerate(rel["exponents"]):
            if exp <= 0:
                continue
            prime = prime_base[prime_idx]
            if prime == -1:
                continue
            product_y = (product_y * pow(prime, exp // 2, n)) % n

    candidate = math.gcd(product_x - product_y, n)
    if 1 < candidate < n:
        return candidate

    candidate = math.gcd(product_x + product_y, n)
    if 1 < candidate < n:
        return candidate

    return None
