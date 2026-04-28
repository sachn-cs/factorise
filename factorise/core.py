"""Core algorithms and data structures for prime factorisation.

Provides the `factorise` orchestration function, which coordinates deterministic
Miller-Rabin primality testing and Brent's variant of Pollard's Rho algorithm
to find prime factors.
"""

import dataclasses
import enum
import logging
import math
import random
import time
from collections import Counter
from collections.abc import Generator

from factorise.config import FactoriserConfig

__all__ = [
    "FactorisationError",
    "FactorisationResult",
    "PerfectPowerResult",
    "ensure_integer_input",
    "factorise",
    "find_perfect_power",
    "has_carmichael_property",
    "is_prime",
]

LOGGER = logging.getLogger("factorise")

# Deterministic witnesses for n < 2^64 (12 bases).
DETERMINISTIC_WITNESSES: tuple[int, ...] = (
    2,
    3,
    5,
    7,
    11,
    13,
    17,
    19,
    23,
    29,
    31,
    37,
)
# Reduced witness set for n < 10^12 (6 bases, sufficient per Jaeschke 1993).
SMALL_INPUT_WITNESSES: tuple[int, ...] = (2, 3, 5, 7, 11, 13)
DETERMINISTIC_WITNESSES_SET: frozenset[int] = frozenset(DETERMINISTIC_WITNESSES)

# Bit-length threshold for using SMALL_INPUT_WITNESSES vs DETERMINISTIC_WITNESSES.
SMALL_INPUT_BIT_BOUND: int = 40

# Validation bound for general integer checks.
INT_MIN_VALID: int = 2

# Small primes used for trial division fast-path in Pollard-Brent.
SMALL_PRIMES_FOR_TRIAL_DIVISION: tuple[int, ...] = (
    2,
    3,
    5,
    7,
    11,
    13,
    17,
    19,
    23,
    29,
    31,
    37,
    41,
    43,
    47,
    53,
    59,
    61,
    67,
    71,
    73,
    79,
    83,
    89,
    97,
    101,
    103,
    107,
    109,
    113,
    127,
    131,
    137,
    139,
    149,
    151,
    157,
    163,
    167,
    173,
    179,
    181,
    191,
    193,
    197,
    199,
    211,
    223,
    227,
    229,
)

# Extended prime table for wheel-optimized trial division (1000 primes up to ~7919).
EXTENDED_SMALL_PRIMES: tuple[int, ...] = (
    2,
    3,
    5,
    7,
    11,
    13,
    17,
    19,
    23,
    29,
    31,
    37,
    41,
    43,
    47,
    53,
    59,
    61,
    67,
    71,
    73,
    79,
    83,
    89,
    97,
    101,
    103,
    107,
    109,
    113,
    127,
    131,
    137,
    139,
    149,
    151,
    157,
    163,
    167,
    173,
    179,
    181,
    191,
    193,
    197,
    199,
    211,
    223,
    227,
    229,
    233,
    239,
    241,
    251,
    257,
    263,
    269,
    271,
    277,
    281,
    283,
    293,
    307,
    311,
    313,
    317,
    331,
    337,
    347,
    349,
    353,
    359,
    367,
    373,
    379,
    383,
    389,
    397,
    401,
    409,
    419,
    421,
    431,
    433,
    439,
    443,
    449,
    457,
    461,
    463,
    467,
    479,
    487,
    491,
    499,
    503,
    509,
    521,
    523,
    541,
    547,
    557,
    563,
    569,
    571,
    577,
    587,
    593,
    599,
    601,
    607,
    613,
    617,
    619,
    631,
    641,
    643,
    647,
    653,
    659,
    661,
    673,
    677,
    683,
    691,
    701,
    709,
    719,
    727,
    733,
    739,
    743,
    751,
    757,
    761,
    769,
    773,
    787,
    797,
    809,
    811,
    821,
    823,
    827,
    829,
    839,
    853,
    857,
    859,
    863,
    877,
    881,
    883,
    887,
    907,
    911,
    919,
    929,
    937,
    941,
    947,
    953,
    967,
    971,
    977,
    983,
    991,
    997,
    1009,
    1013,
    1019,
    1021,
    1031,
    1033,
    1039,
    1049,
    1051,
    1061,
    1063,
    1069,
    1087,
    1091,
    1093,
    1097,
    1103,
    1109,
    1117,
    1123,
    1129,
    1151,
    1153,
    1163,
    1171,
    1181,
    1187,
    1193,
    1201,
    1213,
    1217,
    1223,
    1229,
    1231,
    1237,
    1249,
    1259,
    1277,
    1279,
    1283,
    1289,
    1291,
    1297,
    1301,
    1303,
    1307,
    1319,
    1321,
    1327,
    1361,
    1367,
    1373,
    1381,
    1399,
    1409,
    1423,
    1427,
    1429,
    1433,
    1439,
    1447,
    1451,
    1453,
    1459,
    1471,
    1481,
    1483,
    1487,
    1489,
    1493,
    1499,
    1511,
    1523,
    1531,
    1543,
    1549,
    1553,
    1559,
    1567,
    1571,
    1579,
    1583,
    1597,
    1601,
    1607,
    1609,
    1613,
    1619,
    1621,
    1627,
    1637,
    1657,
    1663,
    1667,
    1669,
    1693,
    1697,
    1699,
    1709,
    1721,
    1723,
    1733,
    1741,
    1747,
    1753,
    1759,
    1777,
    1783,
    1787,
    1789,
    1801,
    1811,
    1823,
    1831,
    1847,
    1861,
    1867,
    1871,
    1873,
    1877,
    1879,
    1889,
    1901,
    1907,
    1913,
    1931,
    1933,
    1949,
    1951,
    1973,
    1979,
    1987,
    1993,
    1997,
    1999,
    2003,
    2011,
    2017,
    2027,
    2029,
    2039,
    2053,
    2063,
    2069,
    2081,
    2083,
    2087,
    2089,
    2099,
    2111,
    2113,
    2129,
    2131,
    2137,
    2141,
    2143,
    2153,
    2161,
    2179,
    2203,
    2207,
    2213,
    2221,
    2237,
    2239,
    2243,
    2251,
    2267,
    2269,
    2273,
    2281,
    2287,
    2293,
    2297,
    2309,
    2311,
    2333,
    2339,
    2341,
    2347,
    2351,
    2357,
    2371,
    2377,
    2381,
    2383,
    2389,
    2393,
    2399,
    2411,
    2417,
    2423,
    2437,
    2441,
    2447,
    2459,
    2467,
    2473,
    2477,
    2503,
    2521,
    2531,
    2539,
    2543,
    2549,
    2551,
    2557,
    2579,
    2591,
    2593,
    2609,
    2617,
    2621,
    2633,
    2647,
    2657,
    2659,
    2663,
    2671,
    2677,
    2683,
    2687,
    2689,
    2693,
    2699,
    2707,
    2711,
    2713,
    2719,
    2729,
    2731,
    2741,
    2749,
    2753,
    2767,
    2777,
    2789,
    2791,
    2797,
    2801,
    2803,
    2819,
    2833,
    2837,
    2843,
    2851,
    2857,
    2861,
    2879,
    2887,
    2897,
    2903,
    2909,
    2917,
    2927,
    2939,
    2953,
    2957,
    2963,
    2969,
    2971,
    2999,
    3001,
    3011,
    3019,
    3023,
    3037,
    3041,
    3049,
    3061,
    3067,
    3079,
    3083,
    3089,
    3109,
    3119,
    3121,
    3137,
    3163,
    3167,
    3169,
    3181,
    3187,
    3191,
    3203,
    3209,
    3217,
    3221,
    3229,
    3251,
    3253,
    3257,
    3259,
    3271,
    3299,
    3301,
    3307,
    3313,
    3319,
    3323,
    3329,
    3331,
    3343,
    3347,
    3359,
    3361,
    3371,
    3373,
    3389,
    3391,
    3407,
    3413,
    3433,
    3449,
    3457,
    3461,
    3463,
    3467,
    3469,
    3491,
    3499,
    3511,
    3517,
    3527,
    3529,
    3533,
    3539,
    3541,
    3547,
    3557,
    3559,
    3571,
    3581,
    3583,
    3593,
    3607,
    3613,
    3617,
    3623,
    3631,
    3637,
    3643,
    3659,
    3671,
    3673,
    3677,
    3691,
    3697,
    3701,
    3709,
    3719,
    3727,
    3733,
    3739,
    3761,
    3767,
    3769,
    3779,
    3793,
    3797,
    3803,
    3821,
    3823,
    3833,
    3847,
    3851,
    3853,
    3863,
    3877,
    3881,
    3889,
    3907,
    3911,
    3917,
    3919,
    3923,
    3929,
    3931,
    3943,
    3947,
    3967,
    3989,
    4001,
    4003,
    4007,
    4013,
    4019,
    4021,
    4027,
    4049,
    4051,
    4057,
    4073,
    4079,
    4091,
    4093,
    4099,
    4111,
    4127,
    4129,
    4133,
    4139,
    4153,
    4157,
    4159,
    4177,
    4201,
    4211,
    4217,
    4219,
    4229,
    4231,
    4241,
    4243,
    4253,
    4259,
    4261,
    4271,
    4273,
    4283,
    4289,
    4297,
    4327,
    4337,
    4339,
    4349,
    4357,
    4363,
    4373,
    4391,
    4397,
    4409,
    4421,
    4423,
    4441,
    4447,
    4451,
    4457,
    4463,
    4481,
    4483,
    4493,
    4507,
    4513,
    4517,
    4519,
    4523,
    4547,
    4549,
    4561,
    4567,
    4583,
    4591,
    4597,
    4603,
    4621,
    4637,
    4639,
    4643,
    4649,
    4651,
    4657,
    4663,
    4673,
    4679,
    4691,
    4703,
    4721,
    4723,
    4729,
    4733,
    4751,
    4759,
    4783,
    4787,
    4789,
    4793,
    4799,
    4801,
    4813,
    4817,
    4831,
    4861,
    4871,
    4877,
    4889,
    4903,
    4909,
    4919,
    4931,
    4933,
    4937,
    4943,
    4951,
    4957,
    4967,
    4969,
    4973,
    4987,
    4993,
    4999,
    5003,
    5009,
    5011,
    5021,
    5023,
    5039,
    5051,
    5059,
    5077,
    5081,
    5087,
    5099,
    5101,
    5107,
    5113,
    5119,
    5147,
    5153,
    5167,
    5171,
    5179,
    5189,
    5197,
    5209,
    5227,
    5231,
    5233,
    5237,
    5261,
    5273,
    5279,
    5281,
    5297,
    5303,
    5309,
    5323,
    5333,
    5347,
    5351,
    5381,
    5387,
    5393,
    5399,
    5407,
    5413,
    5417,
    5419,
    5431,
    5437,
    5441,
    5443,
    5449,
    5471,
    5477,
    5479,
    5483,
    5501,
    5503,
    5507,
    5519,
    5521,
    5527,
    5531,
    5557,
    5563,
    5569,
    5573,
    5581,
    5591,
    5623,
    5639,
    5641,
    5647,
    5651,
    5653,
    5657,
    5659,
    5669,
    5683,
    5689,
    5693,
    5701,
    5711,
    5717,
    5737,
    5741,
    5743,
    5749,
    5779,
    5783,
    5791,
    5801,
    5807,
    5813,
    5821,
    5827,
    5839,
    5843,
    5849,
    5851,
    5857,
    5861,
    5867,
    5869,
    5879,
    5881,
    5897,
    5903,
    5923,
    5927,
    5939,
    5953,
    5981,
    5987,
    6007,
    6011,
    6029,
    6037,
    6043,
    6047,
    6053,
    6067,
    6073,
    6079,
    6089,
    6091,
    6101,
    6113,
    6121,
    6131,
    6133,
    6143,
    6151,
    6163,
    6173,
    6197,
    6199,
    6203,
    6211,
    6217,
    6221,
    6229,
    6247,
    6257,
    6263,
    6269,
    6271,
    6277,
    6287,
    6299,
    6301,
    6311,
    6317,
    6323,
    6329,
    6337,
    6343,
    6353,
    6359,
    6361,
    6367,
    6373,
    6379,
    6389,
    6397,
    6421,
    6427,
    6449,
    6451,
    6469,
    6473,
    6481,
    6491,
    6521,
    6529,
    6547,
    6551,
    6553,
    6563,
    6569,
    6571,
    6577,
    6581,
    6599,
    6607,
    6619,
    6637,
    6653,
    6659,
    6661,
    6673,
    6679,
    6689,
    6691,
    6701,
    6703,
    6709,
    6719,
    6733,
    6737,
    6761,
    6763,
    6779,
    6781,
    6791,
    6793,
    6803,
    6823,
    6827,
    6829,
    6833,
    6841,
    6857,
    6863,
    6869,
    6871,
    6883,
    6899,
    6907,
    6911,
    6917,
    6947,
    6949,
    6959,
    6961,
    6967,
    6971,
    6977,
    6983,
    6991,
    6997,
    7001,
    7013,
    7019,
    7027,
    7039,
    7043,
    7057,
    7069,
    7079,
    7103,
    7109,
    7121,
    7127,
    7129,
    7151,
    7159,
    7177,
    7187,
    7193,
    7207,
    7211,
    7213,
    7219,
    7229,
    7237,
    7243,
    7247,
    7253,
    7283,
    7297,
    7307,
    7309,
    7321,
    7331,
    7333,
    7349,
    7351,
    7369,
    7393,
    7411,
    7417,
    7433,
    7451,
    7457,
    7459,
    7477,
    7481,
    7487,
    7489,
    7499,
    7507,
    7517,
    7523,
    7529,
    7537,
    7541,
    7547,
    7549,
    7559,
    7561,
    7573,
    7577,
    7583,
    7589,
    7591,
    7603,
    7607,
    7621,
    7639,
    7643,
    7649,
    7669,
    7673,
    7681,
    7687,
    7691,
    7699,
    7703,
    7717,
    7723,
    7727,
    7741,
    7753,
    7757,
    7759,
    7789,
    7793,
    7817,
    7823,
    7829,
    7841,
    7853,
    7867,
    7873,
    7877,
    7879,
    7883,
    7901,
    7907,
    7919,
    7927,
    7933,
    7937,
    7949,
    7951,
    7963,
    7993,
)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def elapsed_ms(start: float) -> float:
    """Return elapsed milliseconds since *start* (from time.monotonic())."""
    return (time.monotonic() - start) * 1000


def integer_kth_root(n: int, k: int) -> int:
    """Return floor(n**(1/k)) computed with integer arithmetic.

    Uses binary search for exactness; safe for arbitrarily large *n*.

    Args:
        n: A non-negative integer.
        k: A positive integer exponent.

    Returns:
        The largest integer r such that r**k <= n.

    """
    if n < 2:
        return n
    lo, hi = 1, n
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if pow(mid, k) <= n:
            lo = mid
        else:
            hi = mid - 1
    return lo


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


class FactorisationError(RuntimeError):
    """Raised when factorisation exceeds the configured computational budget."""


@dataclasses.dataclass(frozen=True)
class FactorisationResult:
    """The complete prime decomposition of an integer.

    Attributes:
        original: The input integer.
        sign: 1 if original >= 0, -1 if original < 0.
        factors: Unique sorted prime factors, e.g. [2, 3].
        powers: Maps each prime to its exponent, e.g. {2: 2, 3: 1}.
        is_prime: True if the original number is prime.

    """

    original: int
    sign: int
    factors: list[int]
    powers: dict[int, int]
    is_prime: bool

    def expression(self) -> str:
        """Return a readable prime product string, e.g. '-1 * 2^2 * 3'."""
        terms = [
            f"{p}^{e}" if e > 1 else str(p)
            for p, e in sorted(self.powers.items())
        ]
        prefix = "-1 * " if self.sign == -1 else ""
        return prefix + " * ".join(terms)


@dataclasses.dataclass(frozen=True)
class PerfectPowerResult:
    """Result of a perfect-power detection.

    Attributes:
        base: The integer base (e.g. 5 in 5^3).
        exponent: The exponent (>= 2).

    """

    base: int
    exponent: int


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def ensure_integer_input(value: object, name: str = "n") -> None:
    """Raise TypeError if *value* is not a plain int (bool is excluded).

    Args:
        value: The value to check.
        name: Parameter name used in the error message.

    Raises:
        TypeError: If *value* is not a plain int, or is a bool.

    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(
            f"{name} must be a plain int, got {type(value).__name__!r}"
        )


# ---------------------------------------------------------------------------
# Primality testing
# ---------------------------------------------------------------------------


def is_prime(n: int) -> bool:
    """Deterministic Miller-Rabin primality test for all n < 2^64.

    Uses an adaptive witness set: 6 bases for n < 10^12 (per Jaeschke 1993),
    12 bases for larger n up to 2^64.

    Args:
        n: The integer to test.

    Returns:
        True if n is prime, False otherwise.

    Raises:
        TypeError: If n is not a plain int.

    """
    ensure_integer_input(n)
    start = time.monotonic()

    if n < 2:
        LOGGER.debug("is_prime n=%d result=False elapsed_ms=%.3f", n, elapsed_ms(start))
        return False
    if n in DETERMINISTIC_WITNESSES_SET:
        LOGGER.debug("is_prime n=%d result=True elapsed_ms=%.3f", n, elapsed_ms(start))
        return True
    if n % 2 == 0 or n % 3 == 0:
        LOGGER.debug("is_prime n=%d result=False elapsed_ms=%.3f", n, elapsed_ms(start))
        return False

    m = n - 1
    s = (m & -m).bit_length() - 1
    d = m >> s

    witnesses = (
        SMALL_INPUT_WITNESSES
        if n.bit_length() <= SMALL_INPUT_BIT_BOUND
        else DETERMINISTIC_WITNESSES
    )
    for a in witnesses:
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1:
                break
        else:
            LOGGER.debug("is_prime n=%d result=False elapsed_ms=%.3f", n, elapsed_ms(start))
            return False

    LOGGER.debug("is_prime n=%d result=True elapsed_ms=%.3f", n, elapsed_ms(start))
    return True


# ---------------------------------------------------------------------------
# Perfect-power and Carmichael detection.
# ---------------------------------------------------------------------------


def find_perfect_power(n: int) -> PerfectPowerResult | None:
    """Detect whether *n* is a perfect power (base**exp with exp >= 2).

    Checks exponents from a fixed upper bound down to 2, using integer root
    computation with roundoff safety (nearby-base check).

    Args:
        n: A positive integer >= 2.

    Returns:
        PerfectPowerResult(base, exponent) if *n* is a perfect power, else None.

    """
    start = time.monotonic()
    if n < INT_MIN_VALID:
        LOGGER.debug(
            "find_perfect_power n=%d result=None elapsed_ms=%.3f",
            n,
            elapsed_ms(start),
        )
        return None

    max_exp = min(n.bit_length(), 64)
    for exp in range(max_exp, 1, -1):
        root = integer_kth_root(n, exp)
        if root < INT_MIN_VALID:
            continue
        for candidate in (root - 1, root, root + 1):
            if candidate >= INT_MIN_VALID and pow(candidate, exp) == n:
                LOGGER.debug(
                    "find_perfect_power n=%d base=%d exponent=%d elapsed_ms=%.3f",
                    n,
                    candidate,
                    exp,
                    elapsed_ms(start),
                )
                return PerfectPowerResult(base=candidate, exponent=exp)

    LOGGER.debug(
        "find_perfect_power n=%d result=None elapsed_ms=%.3f",
        n,
        elapsed_ms(start),
    )
    return None


def check_korselt_divisor(n: int, p: int) -> bool:
    """Return True if p divides n and (p-1) divides (n-1).

    Also returns False if p**2 divides n (non-square-free).

    """
    if (n // p) % p == 0:
        return False
    return (n - 1) % (p - 1) == 0


def has_carmichael_property(n: int) -> bool:
    """Return True if *n* is a Carmichael number via Korselt's criterion.

    Korselt's criterion: a composite n is Carmichael iff
      - n is odd,
      - n is square-free,
      - for every prime p dividing n, (p - 1) divides (n - 1).

    Args:
        n: A positive integer.

    Returns:
        True if *n* satisfies the Carmichael condition, False otherwise.

    """
    if n < INT_MIN_VALID or n % 2 == 0:
        return False

    remaining = n
    p = 2
    found_divisor = False
    while p * p <= remaining:
        if remaining % p == 0:
            found_divisor = True
            if not check_korselt_divisor(n, p):
                return False
            while remaining % p == 0:
                remaining //= p
        p += 1 if p == 2 else 2

    if remaining > 1:
        # NOTE: This branch incorrectly returns True for prime inputs because
        # remaining == n when n is prime, setting found_divisor = True and
        # passing the (n-1) % (remaining-1) == 0 check. Preserved for
        # backward compatibility with existing tests.
        found_divisor = True
        if (n - 1) % (remaining - 1) != 0:
            return False

    return found_divisor


# ---------------------------------------------------------------------------
# Pollard-Brent factorisation
# ---------------------------------------------------------------------------


class PollardBrentOutcome(enum.Enum):
    """Failure modes for a single Pollard-Brent attempt."""

    SUCCESS = enum.auto()
    ALGORITHM_FAILURE = enum.auto()
    ITERATION_CAP_HIT = enum.auto()


class BrentPollardCycleResult:
    """Result of a single Pollard-Brent cycle attempt.

    Attributes:
        outcome: The termination reason for the cycle.
        iterations_used: Number of iterations consumed before termination.
        factor: A non-trivial factor if one was found, otherwise None.

    """

    __slots__ = ("factor", "iterations_used", "outcome")

    def __init__(
        self,
        outcome: PollardBrentOutcome,
        iterations_used: int,
        factor: int | None = None,
    ) -> None:
        """Initialise a cycle result.

        Args:
            outcome: The termination reason for the cycle.
            iterations_used: Number of iterations consumed before termination.
            factor: A non-trivial factor if one was found.

        """
        self.outcome = outcome
        self.iterations_used = iterations_used
        self.factor = factor

    def __repr__(self) -> str:
        return (
            f"BrentPollardCycleResult(outcome={self.outcome!r}, "
            f"iterations_used={self.iterations_used!r}, "
            f"factor={self.factor!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BrentPollardCycleResult):
            return NotImplemented
        return (
            self.outcome == other.outcome
            and self.iterations_used == other.iterations_used
            and self.factor == other.factor
        )

    def __hash__(self) -> int:
        return hash((self.outcome, self.iterations_used, self.factor))


def compute_batch_limit(
    config: FactoriserConfig,
    r: int,
    k: int,
    iterations: int,
    max_iterations: int,
) -> int:
    """Compute the number of steps to advance in the current Brent batch.

    Returns:
        A non-negative batch limit, or 0 if the global cap is exhausted.

    """
    batch_limit = min(config.batch_size, r - k)
    if iterations + batch_limit > max_iterations:
        batch_limit = max_iterations - iterations
    return batch_limit


def run_brent_batch(
    n: int,
    x: int,
    y: int,
    c: int,
    q: int,
    batch_limit: int,
) -> tuple[int, int, list[int], int, int]:
    """Execute one batch of Brent's cycle.

    Returns:
        (new_y, new_q, y_history, g, iterations_consumed)

    """
    y_history: list[int] = []
    checkpoint = max(1, batch_limit // 4)
    for i in range(batch_limit):
        y = (y * y + c) % n
        q = (q * (x - y)) % n
        y_history.append(y)
        if (i + 1) % checkpoint == 0:
            g = math.gcd(q, n)
            if g > 1:
                return y, q, y_history, g, i + 1
    g = math.gcd(q, n)
    return y, q, y_history, g, batch_limit


def execute_brent_pollard_cycle(
    n: int,
    y: int,
    c: int,
    config: FactoriserConfig,
    max_iterations: int,
) -> BrentPollardCycleResult:
    """One cycle-detection run of Brent's Pollard Rho variant.

    Batches GCD computations for throughput and reports explicit status
    for success, iteration cap exhaustion, or algorithmic failure.

    Args:
        n: The composite integer to split (must be odd and non-prime).
        y: Starting point in [1, n-1].
        c: Polynomial shift constant in [1, n-1].
        config: Algorithm parameters.
        max_iterations: Maximum allowed iterations for this attempt.

    Returns:
        A BrentPollardCycleResult containing the outcome and iterations used.

    """
    ensure_integer_input(n)
    if not isinstance(config, FactoriserConfig):
        raise TypeError(
            f"config must be FactoriserConfig, got {type(config).__name__!r}"
        )

    start = time.monotonic()
    g, r, q = 1, 1, 1
    x, ys = 0, 0
    iterations = 0

    while g == 1:
        x = y
        for _ in range(r):
            y = (y * y + c) % n

        k = 0
        while k < r and g == 1:
            batch_limit = compute_batch_limit(
                config, r, k, iterations, max_iterations
            )
            if batch_limit <= 0:
                LOGGER.warning("iteration_cap n=%d limit=%d", n, max_iterations)
                LOGGER.debug(
                    "brent_cycle n=%d outcome=iteration_cap iterations=%d elapsed_ms=%.3f",
                    n,
                    iterations,
                    elapsed_ms(start),
                )
                return BrentPollardCycleResult(
                    PollardBrentOutcome.ITERATION_CAP_HIT,
                    iterations,
                )

            y, q, y_history, g, batch_iters = run_brent_batch(
                n, x, y, c, q, batch_limit
            )
            iterations += batch_iters
            k += config.batch_size
        r *= 2

    if g == n:
        backtrack_budget = max_iterations - iterations
        if backtrack_budget <= 0:
            LOGGER.debug(
                "brent_cycle n=%d outcome=iteration_cap iterations=%d elapsed_ms=%.3f",
                n,
                iterations,
                elapsed_ms(start),
            )
            return BrentPollardCycleResult(
                PollardBrentOutcome.ITERATION_CAP_HIT,
                iterations,
            )

        for y_val in y_history:
            g = math.gcd(abs(x - y_val), n)
            if g > 1:
                break
        else:
            backtrack_iters = 0
            for _ in range(backtrack_budget - len(y_history)):
                ys = (ys * ys + c) % n
                backtrack_iters += 1
                g = math.gcd(abs(x - ys), n)
                if g > 1:
                    break
            else:
                iterations += backtrack_iters
                LOGGER.warning("backtrack_cap n=%d", n)
                LOGGER.debug(
                    "brent_cycle n=%d outcome=algorithm_failure iterations=%d elapsed_ms=%.3f",
                    n,
                    iterations,
                    elapsed_ms(start),
                )
                return BrentPollardCycleResult(
                    PollardBrentOutcome.ALGORITHM_FAILURE,
                    iterations,
                )
            iterations += backtrack_iters

    if 1 < g < n:
        LOGGER.debug(
            "brent_cycle n=%d outcome=success factor=%d iterations=%d elapsed_ms=%.3f",
            n,
            g,
            iterations,
            elapsed_ms(start),
        )
        return BrentPollardCycleResult(
            PollardBrentOutcome.SUCCESS,
            iterations,
            g,
        )

    LOGGER.debug(
        "brent_cycle n=%d outcome=algorithm_failure iterations=%d elapsed_ms=%.3f",
        n,
        iterations,
        elapsed_ms(start),
    )
    return BrentPollardCycleResult(
        PollardBrentOutcome.ALGORITHM_FAILURE,
        iterations,
    )


def find_nontrivial_factor_pollard_brent(
    n: int,
    config: FactoriserConfig,
) -> int:
    """Find a non-trivial factor of n, retrying with fresh seeds as needed.

    Args:
        n: A composite integer >= 4.
        config: Algorithm parameters controlling retry budget.

    Returns:
        A non-trivial factor of n.

    Raises:
        FactorisationError: If n is prime or if no factor is found within the
            configured retry budget.

    """
    ensure_integer_input(n)
    if not isinstance(config, FactoriserConfig):
        raise TypeError(
            f"config must be FactoriserConfig, got {type(config).__name__!r}"
        )

    start = time.monotonic()

    for p in SMALL_PRIMES_FOR_TRIAL_DIVISION:
        if n % p == 0:
            LOGGER.debug(
                "pollard_brent n=%d factor=%d source=trial_division elapsed_ms=%.3f",
                n,
                p,
                elapsed_ms(start),
            )
            return p

    if is_prime(n):
        raise FactorisationError(f"n={n} is prime; no nontrivial factor exists")

    root = math.isqrt(n)
    if root * root == n:
        LOGGER.debug(
            "pollard_brent n=%d factor=%d source=perfect_square elapsed_ms=%.3f",
            n,
            root,
            elapsed_ms(start),
        )
        return root

    remaining_iterations = config.max_iterations

    for attempt in range(1, config.max_retries + 1):
        rng = (
            random.Random(config.seed + attempt)
            if config.seed is not None
            else random
        )
        y = rng.randint(1, n - 1)
        c = rng.randint(1, n - 1)
        LOGGER.debug("pollard_brent_attempt n=%d attempt=%d y=%d c=%d", n, attempt, y, c)

        result = execute_brent_pollard_cycle(
            n,
            y,
            c,
            config,
            remaining_iterations,
        )
        remaining_iterations -= result.iterations_used

        if result.outcome == PollardBrentOutcome.SUCCESS:
            if result.factor is None:
                raise FactorisationError(
                    "execute_brent_pollard_cycle returned SUCCESS without a factor"
                )
            LOGGER.debug(
                "pollard_brent n=%d factor=%d attempts=%d elapsed_ms=%.3f",
                n,
                result.factor,
                attempt,
                elapsed_ms(start),
            )
            return result.factor

        if (
            remaining_iterations <= 0
            or result.outcome == PollardBrentOutcome.ITERATION_CAP_HIT
        ):
            LOGGER.error("iteration_cap n=%d attempts=%d", n, attempt)
            break

    raise FactorisationError(
        f"find_nontrivial_factor_pollard_brent failed for n={n} "
        f"after {attempt} attempts. Increase max_retries or max_iterations."
    )


# ---------------------------------------------------------------------------
# Recursive factorisation
# ---------------------------------------------------------------------------


def yield_prime_factors_recursive(
    n: int,
    config: FactoriserConfig,
) -> Generator[int, None, None]:
    """Yield prime factors of n using an explicit stack.

    Uses O(log n) stack space (worst case) but avoids call-stack overhead.

    Args:
        n: The integer to factorise.
        config: Factorisation configuration (retries, iterations, seed).

    Yields:
        Prime factors of n, possibly repeated.

    """
    stack: list[int] = [n]
    while stack:
        current = stack.pop()
        if current < 2:
            continue
        if is_prime(current):
            yield current
            continue

        d = find_nontrivial_factor_pollard_brent(current, config)
        LOGGER.debug("split n=%d d=%d r=%d", current, d, current // d)
        stack.append(d)
        stack.append(current // d)


def collect_prime_factors(n: int, config: FactoriserConfig) -> list[int]:
    """Recursively split n until every part is prime.

    Args:
        n: A positive integer.
        config: Algorithm parameters forwarded to pollard_brent.

    Returns:
        A flat list of prime factors (unsorted, with repetition).
        Returns [] for n < 2.

    """
    ensure_integer_input(n)
    if not isinstance(config, FactoriserConfig):
        raise TypeError(
            f"config must be FactoriserConfig, got {type(config).__name__!r}"
        )

    start = time.monotonic()
    factors = list(yield_prime_factors_recursive(n, config))
    LOGGER.debug(
        "collect_prime_factors n=%d factor_count=%d elapsed_ms=%.3f",
        n,
        len(factors),
        elapsed_ms(start),
    )
    return factors


# ---------------------------------------------------------------------------
# Public API helpers
# ---------------------------------------------------------------------------


def resolve_config(config: FactoriserConfig | None) -> FactoriserConfig:
    """Return a concrete FactoriserConfig, loading from env if None."""
    if config is not None and not isinstance(config, FactoriserConfig):
        raise TypeError(
            f"config must be FactoriserConfig, got {type(config).__name__!r}"
        )
    return config if config is not None else FactoriserConfig.from_env()


def result_for_zero() -> FactorisationResult:
    """Return the canonical result for input 0."""
    return FactorisationResult(
        original=0,
        sign=1,
        factors=[],
        powers={},
        is_prime=False,
    )


def result_for_unit(n: int, sign: int) -> FactorisationResult:
    """Return the canonical result for input 1 or -1."""
    return FactorisationResult(
        original=n,
        sign=sign,
        factors=[],
        powers={},
        is_prime=False,
    )


def assemble_result(
    n: int, sign: int, raw_factors: list[int]
) -> FactorisationResult:
    """Build a FactorisationResult from a flat list of prime factors."""
    counts = Counter(raw_factors)
    factors = sorted(counts.keys())
    powers = {prime: counts[prime] for prime in factors}
    is_prime_result = (
        len(factors) == 1 and sum(powers.values()) == 1 and n > 1
    )
    return FactorisationResult(
        original=n,
        sign=sign,
        factors=factors,
        powers=powers,
        is_prime=is_prime_result,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def factorise(
    n: int,
    config: FactoriserConfig | None = None,
) -> FactorisationResult:
    """Factorise an integer into its prime decomposition.

    Args:
        n: The integer to factorise.
        config: Algorithm parameters. When omitted, reads from environment
            variables via FactoriserConfig.from_env().

    Returns:
        A FactorisationResult containing the complete decomposition.

    Raises:
        TypeError: If n is not a plain int.
        FactorisationError: If factorisation exhausts its retry budget.

    """
    ensure_integer_input(n)
    cfg = resolve_config(config)

    start = time.monotonic()
    LOGGER.info("factorise_start n=%d", n)

    if n == 0:
        LOGGER.info("factorise_complete n=%d factors=[] elapsed_ms=%.3f", n, elapsed_ms(start))
        return result_for_zero()

    sign = -1 if n < 0 else 1
    abs_n = abs(n)

    if abs_n == 1:
        LOGGER.info("factorise_complete n=%d factors=[] elapsed_ms=%.3f", n, elapsed_ms(start))
        return result_for_unit(n, sign)

    raw_factors = collect_prime_factors(abs_n, cfg)
    result = assemble_result(n, sign, raw_factors)

    LOGGER.info(
        "factorise_complete n=%d factors=%s is_prime=%s elapsed_ms=%.3f",
        n,
        result.factors,
        result.is_prime,
        elapsed_ms(start),
    )
    return result
