"""Core algorithms and data structures for prime factorisation.

Provides the `factorise` orchestration function, which coordinates deterministic
Miller-Rabin primality testing and Brent's variant of Pollard's Rho algorithm
to find prime factors.

The module exports `FactorisationResult` and `FactoriserConfig` to ensure
type-safe, explicit configuration and results without global state.
"""

import dataclasses
import enum
import math
import os
import random
from collections import Counter
from collections.abc import Generator

from loguru import logger

__all__ = [
    "ensure_integer_input",
    "FactorisationError",
    "FactorisationResult",
    "PerfectPowerResult",
    "FactoriserConfig",
    "is_prime",
    "find_perfect_power",
    "has_carmichael_property",
    "factorise",
]

# Deterministic witnesses for n < 2^64 (12 bases).
DETERMINISTIC_WITNESSES: tuple[int, ...] = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29,
                                            31, 37)
# Reduced witness set for n < 10^12 (6 bases, sufficient per Jaeschke 1993).
SMALL_INPUT_WITNESSES: tuple[int, ...] = (2, 3, 5, 7, 11, 13)
DETERMINISTIC_WITNESSES_SET: frozenset[int] = frozenset(DETERMINISTIC_WITNESSES)
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

logger.disable("factorise")

# ---------------------------------------------------------------------------
# Result type — the single, explicit return value of factorise().
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
# Configuration — no global state; callers own their config.
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class FactoriserConfig:
    """Algorithm parameters for factorisation.

    All values default to a reasonable production setting and can be
    overridden via environment variables or by passing an instance directly.

    Attributes:
        batch_size: GCD operations to batch per iteration (throughput knob).
        max_iterations: Hard cap on inner steps per Pollard-Brent attempt.
        max_retries: How many fresh random seeds to try before giving up.
        seed: Optional deterministic seed base for reproducible retries.
        use_pipeline: If True, use the multi-stage pipeline instead of direct
            Pollard-Brent. Defaults to False for backward compatibility.
    """

    batch_size: int = 128
    max_iterations: int = 10_000_000
    max_retries: int = 20
    seed: int | None = None
    use_pipeline: bool = False

    def __post_init__(self) -> None:
        """Validate fields immediately — fail fast at construction time."""
        if self.batch_size < 1 or self.batch_size > 10_000:
            raise ValueError(
                f"batch_size must be >= 1 and <= 10_000, got {self.batch_size}")
        if self.max_iterations < 1 or self.max_iterations > 100_000_000:
            raise ValueError(
                f"max_iterations must be >= 1 and <= 100_000_000, got {self.max_iterations}"
            )
        if self.max_retries < 1 or self.max_retries > 100:
            raise ValueError(
                f"max_retries must be >= 1 and <= 100, got {self.max_retries}")

    @classmethod
    def from_env(cls) -> "FactoriserConfig":
        """Build a config from FACTORISE_* environment variables.

        Falls back to the dataclass defaults when variables are absent.

        Raises:
            ValueError: If any environment variable holds an invalid value.
        """
        seed = os.getenv("FACTORISE_SEED")
        return cls(
            batch_size=int(os.getenv("FACTORISE_BATCH_SIZE", "128")),
            max_iterations=int(os.getenv("FACTORISE_MAX_ITERATIONS",
                                         "10000000")),
            max_retries=int(os.getenv("FACTORISE_MAX_RETRIES", "20")),
            seed=int(seed) if seed is not None else None,
            use_pipeline=os.getenv("FACTORISE_USE_PIPELINE", "").lower()
            in ("1", "true", "yes"),
        )


# ---------------------------------------------------------------------------
# Input validation — one place, one responsibility.
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
            f"{name} must be a plain int, got {type(value).__name__!r}")


# ---------------------------------------------------------------------------
# Primality testing — stateless, no configuration required.
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

    if n < 2:
        return False
    if n in DETERMINISTIC_WITNESSES_SET:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False

    m = n - 1
    s = (m & -m).bit_length() - 1
    d = m >> s

    witnesses = SMALL_INPUT_WITNESSES if n < 10**12 else DETERMINISTIC_WITNESSES
    for a in witnesses:
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = (x * x) % n
            if x == n - 1:
                break
        else:
            return False
    return True


# ---------------------------------------------------------------------------
# Perfect-power and Carmichael detection.
# ---------------------------------------------------------------------------


def find_perfect_power(n: int) -> PerfectPowerResult | None:
    """Detect whether *n* is a perfect power (base**exp with exp >= 2).

    Checks exponents from log2(n) down to 2, using integer root computation
    with roundoff safety (nearby-base check).

    Args:
        n: A positive integer >= 2.

    Returns:
        PerfectPowerResult(base, exponent) if *n* is a perfect power, else None.
    """
    if n < 2:
        return None
    max_exp = n.bit_length()
    for exp in range(max_exp, 1, -1):
        root = round(n**(1.0 / exp))
        if root < 2:
            continue
        for candidate in (root - 1, root, root + 1):
            if candidate >= 2 and candidate**exp == n:
                return PerfectPowerResult(base=candidate, exponent=exp)
    return None


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
    if n < 2 or n % 2 == 0:
        return False
    temp = n
    p = 2
    found_prime_divisor = False
    while p * p <= temp:
        if temp % p == 0:
            found_prime_divisor = True
            if (temp // p) % p == 0:
                return False
            if (n - 1) % (p - 1) != 0:
                return False
            while temp % p == 0:
                temp //= p
        p += 1 if p == 2 else 2
    if temp > 1:
        found_prime_divisor = True
        if (n - 1) % (temp - 1) != 0:
            return False
    return found_prime_divisor


# ---------------------------------------------------------------------------
# Factorisation — Pollard-Brent, expressed as three focused functions.
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

    __slots__ = ("outcome", "iterations_used", "factor")

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
            f"iterations_used={self.iterations_used!r}, factor={self.factor!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BrentPollardCycleResult):
            return NotImplemented
        return (self.outcome == other.outcome and
                self.iterations_used == other.iterations_used and
                self.factor == other.factor)


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
            f"config must be FactoriserConfig, got {type(config).__name__!r}")

    g, r, q = 1, 1, 1
    x, ys = 0, 0
    iterations = 0

    while g == 1:
        x = y
        for _ in range(r):
            y = (y * y + c) % n

        k = 0
        while k < r and g == 1:
            batch_limit = min(config.batch_size, r - k)
            if iterations + batch_limit > max_iterations:
                batch_limit = max_iterations - iterations

            if batch_limit <= 0:
                logger.warning(
                    "iteration cap n={n} limit={limit}",
                    n=n,
                    limit=max_iterations,
                )
                return BrentPollardCycleResult(
                    PollardBrentOutcome.ITERATION_CAP_HIT, iterations)

            # Cache y-values during batch for O(1) backtrack recovery.
            y_history: list[int] = []
            checkpoint = max(1, batch_limit // 4)
            for i in range(batch_limit):
                y = (y * y + c) % n
                q = (q * (x - y)) % n
                y_history.append(y)
                if (i + 1) % checkpoint == 0:
                    g = math.gcd(q, n)
                    if g > 1:
                        iterations += i + 1
                        return BrentPollardCycleResult(
                            PollardBrentOutcome.SUCCESS, iterations, g)

            iterations += batch_limit
            g = math.gcd(q, n)
            k += config.batch_size
        r *= 2

    # The cycle collapsed into g == n — step back one at a time to recover.
    if g == n:
        backtrack_budget = max_iterations - iterations
        if backtrack_budget <= 0:
            return BrentPollardCycleResult(
                PollardBrentOutcome.ITERATION_CAP_HIT, iterations)
        for y_val in y_history:
            g = math.gcd(abs(x - y_val), n)
            if g > 1:
                break
        else:
            # y_history exhausted without finding factor — continue stepping.
            for _ in range(backtrack_budget - len(y_history)):
                ys = (ys * ys + c) % n
                iterations += 1
                g = math.gcd(abs(x - ys), n)
                if g > 1:
                    break
            else:
                logger.warning("backtrack cap n={n}", n=n)
                return BrentPollardCycleResult(
                    PollardBrentOutcome.ALGORITHM_FAILURE, iterations)

    if 1 < g < n:
        return BrentPollardCycleResult(PollardBrentOutcome.SUCCESS, iterations,
                                       g)
    return BrentPollardCycleResult(PollardBrentOutcome.ALGORITHM_FAILURE,
                                   iterations)


def find_nontrivial_factor_pollard_brent(n: int,
                                         config: FactoriserConfig) -> int:
    """Find a non-trivial factor of n, retrying with fresh seeds as needed.

    Args:
        n: A composite integer >= 4.
        config: Algorithm parameters controlling retry budget.

    Returns:
        A non-trivial factor. Returns n itself when n is prime.

    Raises:
        FactorisationError: If no factor is found within config.max_retries attempts.
    """
    ensure_integer_input(n)
    if not isinstance(config, FactoriserConfig):
        raise TypeError(
            f"config must be FactoriserConfig, got {type(config).__name__!r}")

    # Trial division fast-path for tiny primes
    # (Fixes Pollard's Rho cycle exhaustion on tiny fields like n=15, 35)
    for p in SMALL_PRIMES_FOR_TRIAL_DIVISION:
        if n % p == 0:
            return p
    if is_prime(n):
        return n

    root = math.isqrt(n)
    if root * root == n:
        return root

    remaining_iterations = config.max_iterations

    for attempt in range(1, config.max_retries + 1):
        rng = (random.Random(config.seed +
                             attempt) if config.seed is not None else random)
        y = rng.randint(1, n - 1)
        c = rng.randint(1, n - 1)
        logger.debug(
            "attempt={attempt} n={n} y={y} c={c}",
            attempt=attempt,
            n=n,
            y=y,
            c=c,
        )

        result = execute_brent_pollard_cycle(n, y, c, config,
                                             remaining_iterations)
        remaining_iterations -= result.iterations_used

        if result.outcome == PollardBrentOutcome.SUCCESS:
            if result.factor is None:
                raise FactorisationError(
                    "execute_brent_pollard_cycle returned SUCCESS without a factor; this is a bug."
                )
            logger.debug("factor={factor} n={n}", factor=result.factor, n=n)
            return result.factor

        if (remaining_iterations <= 0 or
                result.outcome == PollardBrentOutcome.ITERATION_CAP_HIT):
            logger.error("global iteration cap hit for n={n}", n=n)
            break

    raise FactorisationError(
        f"find_nontrivial_factor_pollard_brent failed for n={n} after {attempt} attempts. "
        "Increase max_retries or max_iterations in FactoriserConfig.")


def yield_prime_factors_recursive(
        n: int, config: FactoriserConfig) -> Generator[int, None, None]:
    """Iteratively yield prime factors of n using an explicit stack.

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
        logger.debug("split n={n} d={d} r={r}", n=current, d=d, r=current // d)
        stack.append(d)
        stack.append(current // d)


def yield_prime_factors_via_pipeline(
        n: int, config: FactoriserConfig) -> Generator[int, None, None]:
    """Iteratively yield prime factors of n using the multi-stage pipeline.

    This function is used when config.use_pipeline is True. It uses the
    FactorisationPipeline to find non-trivial factors, feeding each composite
    part back into the pipeline until all remaining values are prime.

    Args:
        n: The integer to factorise.
        config: Factorisation configuration (retries, iterations, seed).

    Yields:
        Prime factors of n, possibly repeated.
    """
    from factorise.pipeline import FactorisationPipeline
    from factorise.pipeline import PipelineConfig

    pipeline_config = PipelineConfig(
        max_iterations=config.max_iterations,
        max_retries=config.max_retries,
        batch_size=config.batch_size,
        seed=config.seed,
    )
    pipeline = FactorisationPipeline(pipeline_config)

    stack: list[int] = [n]
    while stack:
        current = stack.pop()
        if current < 2:
            continue
        if is_prime(current):
            yield current
            continue

        # Ask the pipeline for one factor.
        result = pipeline.attempt(current, config=config)
        if result.was_successful() and result.factor is not None:
            d = result.factor
            logger.debug(
                "pipeline split n={n} d={d}",
                n=current,
                d=d,
            )
            stack.append(d)
            stack.append(current // d)
        elif result.was_failed():
            # Pipeline failed for this composite part; fall back to direct Pollard-Brent
            # which may succeed with different parameters than the pipeline uses.
            logger.warning(
                "pipeline failed for n={n}, falling back to find_nontrivial_factor_pollard_brent",
                n=current,
            )
            try:
                d = find_nontrivial_factor_pollard_brent(current, config)
                stack.append(d)
                stack.append(current // d)
            except FactorisationError:  # noqa: B904
                # If even Pollard-Brent fails, re-raise as FactorisationError
                # since the number cannot be factored with the available methods.
                raise FactorisationError(  # noqa: B904
                    f"All stages failed for n={current}; "
                    "input may be prime or require GNFS") from None
        else:
            # SKIPPED — shouldn't happen for composite inputs
            raise FactorisationError(
                f"Pipeline returned unexpected status {result.outcome()} for composite n={current}"
            )


def collect_prime_factors(n: int, config: FactoriserConfig) -> list[int]:
    """Recursively split n until every part is prime.

    Args:
        n: A positive integer.
        config: Algorithm parameters forwarded to pollard_brent or the pipeline.

    Returns:
        A flat list of prime factors (unsorted, with repetition).
        Returns [] for n < 2.
    """
    ensure_integer_input(n)
    if not isinstance(config, FactoriserConfig):
        raise TypeError(
            f"config must be FactoriserConfig, got {type(config).__name__!r}")
    if config.use_pipeline:
        return list(yield_prime_factors_via_pipeline(n, config))
    return list(yield_prime_factors_recursive(n, config))


# ---------------------------------------------------------------------------
# Public API — the single entry point callers interact with.
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
                Set config.use_pipeline = True to use the multi-stage pipeline.

    Returns:
        A FactorisationResult containing the complete decomposition.

    Raises:
        TypeError: If n is not a plain int.
        FactorisationError: If factorisation exhausts its retry budget.
    """
    ensure_integer_input(n)
    if config is not None and not isinstance(config, FactoriserConfig):
        raise TypeError(
            f"config must be FactoriserConfig, got {type(config).__name__!r}")
    cfg = config if config is not None else FactoriserConfig.from_env()
    logger.info("factorise start n={n}", n=n)

    if n == 0:
        return FactorisationResult(original=0,
                                   sign=1,
                                   factors=[],
                                   powers={},
                                   is_prime=False)

    sign = -1 if n < 0 else 1
    abs_n = abs(n)

    if abs_n == 1:
        return FactorisationResult(original=n,
                                   sign=sign,
                                   factors=[],
                                   powers={},
                                   is_prime=False)

    raw_factors = collect_prime_factors(abs_n, cfg)
    counts = Counter(raw_factors)
    factors = sorted(counts.keys())
    powers = {prime: counts[prime] for prime in factors}
    result = FactorisationResult(
        original=n,
        sign=sign,
        factors=factors,
        powers=powers,
        is_prime=(len(factors) == 1 and sum(powers.values()) == 1 and n > 1),
    )

    logger.info("factorise complete n={n} factors={factors}",
                n=n,
                factors=factors)
    return result
