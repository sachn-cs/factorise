"""Input fixtures shared across all benchmark modules.

Organised by category so individual benchmark files can import
only the datasets they specifically need.
"""

from typing import Final

# ---------------------------------------------------------------------------
# is_prime inputs
# ---------------------------------------------------------------------------

# Small: fits in the fast-path (small prime check / simple divisibility)
IS_PRIME_SMALL: Final[tuple[tuple[str, int], ...]] = (
    ("two", 2),
    ("small_prime", 97),
    ("small_composite", 100),
    ("prime_37", 37),
)

# Medium: fully exercises the Miller-Rabin main loop
IS_PRIME_MEDIUM: Final[tuple[tuple[str, int], ...]] = (
    ("prime_1e9", 10**9 + 7),
    ("composite_1e9", 10**9 + 8),
    ("mersenne_31", 2**31 - 1),  # prime
    ("mersenne_31_plus", 2**31),  # composite
)

# Large: stresses modular exponentiation on big integers
IS_PRIME_LARGE: Final[tuple[tuple[str, int], ...]] = (
    ("prime_32b", 32_416_189_987),  # verified prime
    ("semiprime_large", 9_973 * 9_967),  # composite ~1e8
    ("prime_64bit", 2**61 - 1),  # Mersenne M61, prime
    ("composite_64bit", 2**62 - 57),  # composite near 2^62
)

# ---------------------------------------------------------------------------
# factorise inputs
# ---------------------------------------------------------------------------

# Small composites: Pollard-Brent not needed; factors found trivially
FACTORISE_SMALL: Final[tuple[tuple[str, int], ...]] = (
    ("n12", 12),  # 2^2 * 3
    ("n24", 24),  # 2^3 * 3
    ("n360", 360),  # 2^3 * 3^2 * 5
    ("n_power2_20", 2**20),  # single prime power
)

# Medium: requires Pollard-Brent one or two levels deep
FACTORISE_MEDIUM: Final[tuple[tuple[str, int], ...]] = (
    ("n_123456789", 123_456_789),  # 3^2 * 3607 * 3803
    ("primorial_30030", 30_030),  # 2*3*5*7*11*13
    ("large_prime", 10**9 + 7),  # prime — triggers is_prime fast path
    ("n_semiprime_medium", 99_991 * 99_989),  # two 5-digit primes
)

# Large: stresses full Pollard-Brent cycle with large semiprimes
FACTORISE_LARGE: Final[tuple[tuple[str, int], ...]] = (
    ("semiprime_10d", 9_999_991 * 9_999_973),  # two 7-digit primes
    ("semiprime_32b", 32_416_189_987 * 15_485_863),  # two large primes
    ("highly_composite", (2**10) * (3**5) * (5**2) * 7),  # many small factors
    ("prime_32bit", 32_416_189_987),  # pure prime
)

# Scalability sweep: logarithmically spaced inputs for trend analysis
SCALABILITY_INPUTS: Final[tuple[tuple[str, int], ...]] = (
    ("n_1e2", 100),
    ("n_1e4", 10_000),
    ("n_1e6", 1_000_003),  # prime near 1e6
    ("n_1e8", 100_000_007),  # prime near 1e8
    ("n_1e10", 10_000_000_019),  # prime near 1e10
    ("n_1e12", 1_000_000_000_039),  # prime near 1e12
)
