"""Shared routines for quadratic sieve-based stages."""

from __future__ import annotations

from typing import Any


def is_small_prime(candidate: int) -> bool:
    """Test whether a small integer is prime."""
    if candidate < 2:
        return False
    if candidate % 2 == 0:
        return candidate == 2
    limit = int(candidate**0.5) + 1
    for divisor in range(3, limit, 2):
        if candidate % divisor == 0:
            return False
    return True


def factor_over_base(
    value: int,
    prime_base: list[int],
) -> list[int] | None:
    """Factor a value over the given prime base.

    Returns a list of exponents (one per prime in the base), or None if the
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

    if remaining in prime_base:
        index = prime_base.index(remaining)
        exponents[index] += 1
        return exponents

    return None


def find_dependency(
    relations: list[dict[str, Any]],
    num_primes: int,
) -> list[int] | None:
    """Find a linear dependency among relations using Gaussian elimination.

    Filters out trivial relations (all even exponents) before elimination,
    since they produce x ≡ y (mod n) and never yield a non-trivial factor.
    """
    non_trivial = [
        rel for rel in relations
        if any(exp % 2 == 1 for exp in rel["exponents"])
    ]
    if len(non_trivial) < num_primes:
        return None

    rows: list[list[int]] = []
    for index, rel in enumerate(non_trivial):
        mask = 0
        for j, exp in enumerate(rel["exponents"]):
            if exp % 2 == 1:
                mask |= 1 << j
        history = 1 << index
        rows.append([mask, history])

    row_index = 0
    for col in range(num_primes):
        pivot = -1
        for r in range(row_index, len(rows)):
            if (rows[r][0] >> col) & 1:
                pivot = r
                break
        if pivot == -1:
            continue

        rows[row_index], rows[pivot] = rows[pivot], rows[row_index]

        for r in range(len(rows)):
            if r != row_index and ((rows[r][0] >> col) & 1):
                rows[r][0] ^= rows[row_index][0]
                rows[r][1] ^= rows[row_index][1]

        row_index += 1
        if row_index >= len(rows):
            break

    for row in rows:
        mask, history = row
        if mask == 0 and history != 0:
            vector = [0] * len(non_trivial)
            for bit in range(len(non_trivial)):
                if (history >> bit) & 1:
                    vector[bit] = 1
            return vector

    return None


def extract_factor(
    n: int,
    relations: list[dict[str, Any]],
    dependency: list[int],
    prime_base: list[int],
) -> int | None:
    """Extract a non-trivial factor from a dependency.

    Computes x = product of a_i and y = product of p_j^(e_j/2),
    then returns gcd(x ± y, n) if it yields a non-trivial factor.
    """
    product_x = 1
    product_y = 1
    for index, rel in enumerate(relations):
        if not dependency[index]:
            continue
        product_x = (product_x * rel["a"]) % n
        for prime_index, exp in enumerate(rel["exponents"]):
            if exp <= 0:
                continue
            prime = prime_base[prime_index]
            if prime == -1:
                continue
            product_y = (product_y * pow(prime, exp // 2, n)) % n

    import math
    candidate = math.gcd(product_x - product_y, n)
    if 1 < candidate < n:
        return candidate

    candidate = math.gcd(product_x + product_y, n)
    if 1 < candidate < n:
        return candidate

    return None
