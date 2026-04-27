"""Shared utility functions for the factorise package."""

from __future__ import annotations

__all__ = ["sieve_primes"]


def sieve_primes(bound: int) -> list[int]:
    """Return all primes up to bound using the Sieve of Eratosthenes.

    Args:
        bound: The inclusive upper bound for prime generation.

    Returns:
        A sorted list of primes p where 2 <= p <= bound.
        Returns an empty list if bound < 2.

    """
    if bound < 2:
        return []
    is_prime_arr = bytearray(b'\x01') * (bound + 1)
    is_prime_arr[0:2] = b'\x00\x00'
    for i in range(2, int(bound**0.5) + 1):
        if is_prime_arr[i]:
            step = i
            start = i * i
            is_prime_arr[start:bound + 1:step] = b'\x00' * ((bound - start) // step + 1)
    return [i for i in range(2, bound + 1) if is_prime_arr[i]]
