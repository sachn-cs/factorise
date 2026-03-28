"""Core algorithms and data structures for prime factorisation.

Provides the `factorise` orchestration function, which coordinates deterministic
Miller-Rabin primality testing and Brent's variant of Pollard's Rho algorithm
to find prime factors.

The module exports `FactorisationResult` and `FactoriserConfig` to ensure
type-safe, explicit configuration and results without global state.
"""

import dataclasses
import math
import os
import random
from collections import Counter

from loguru import logger

# The set of witnesses that makes Miller-Rabin deterministic for n < 2^64.
WITNESSES: tuple[int, ...] = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
WITNESSES_SET: frozenset[int] = frozenset(WITNESSES)

logger.disable("factorise")

# ---------------------------------------------------------------------------
# Result type — the single, explicit return value of factorise().
# ---------------------------------------------------------------------------


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
            f"{p}^{e}" if e > 1 else str(p) for p, e in self.powers.items()
        ]
        prefix = "-1 * " if self.sign == -1 else ""
        return prefix + " * ".join(terms)


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
    """

    batch_size: int = 128
    max_iterations: int = 10_000_000
    max_retries: int = 20

    def __post_init__(self) -> None:
        """Validate fields immediately — fail fast at construction time."""
        if self.batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {self.batch_size}")
        if self.max_iterations < 1:
            raise ValueError(
                f"max_iterations must be >= 1, got {self.max_iterations}")
        if self.max_retries < 1:
            raise ValueError(
                f"max_retries must be >= 1, got {self.max_retries}")

    @classmethod
    def from_env(cls) -> "FactoriserConfig":
        """Build a config from FACTORISE_* environment variables.

        Falls back to the dataclass defaults when variables are absent.

        Raises:
            ValueError: If any environment variable holds an invalid value.
        """
        return cls(
            batch_size=int(os.getenv("FACTORISE_BATCH_SIZE", "128")),
            max_iterations=int(os.getenv("FACTORISE_MAX_ITERATIONS",
                                         "10000000")),
            max_retries=int(os.getenv("FACTORISE_MAX_RETRIES", "20")),
        )


# ---------------------------------------------------------------------------
# Input validation — one place, one responsibility.
# ---------------------------------------------------------------------------


def validate_int(value: object, name: str = "n") -> None:
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

    Uses the fixed witness set WITNESSES, which is provably sufficient
    for all integers below 2^64.

    Args:
        n: The integer to test.

    Returns:
        True if n is prime, False otherwise.

    Raises:
        TypeError: If n is not a plain int.
    """
    validate_int(n)

    if n < 2:
        return False
    if n in WITNESSES_SET:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False

    m = n - 1
    s = (m & -m).bit_length() - 1
    d = m >> s

    for a in WITNESSES:
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
# Factorisation — Pollard-Brent, expressed as three focused functions.
# ---------------------------------------------------------------------------


def pollard_brent_attempt(
    n: int,
    y: int,
    c: int,
    config: FactoriserConfig,
) -> int | None:
    """One cycle-detection run of Brent's Pollard Rho variant.

    Batches GCD computations for throughput, backtracks when necessary,
    and returns None if the iteration budget is exceeded.

    Args:
        n: The composite integer to split (must be odd and non-prime).
        y: Starting point in [1, n-1].
        c: Polynomial shift constant in [1, n-1].
        config: Algorithm parameters.

    Returns:
        A factor g with 1 < g < n, or None if this attempt failed.
    """
    g, r, q = 1, 1, 1
    x, ys = 0, 0
    iterations = 0

    while g == 1:
        x = y
        for _ in range(r):
            y = (y * y + c) % n

        k = 0
        while k < r and g == 1:
            ys = y
            batch_limit = min(config.batch_size, r - k)
            if iterations + batch_limit > config.max_iterations:
                batch_limit = config.max_iterations - iterations

            if batch_limit <= 0:
                logger.warning("iteration cap n={n} limit={limit}",
                               n=n,
                               limit=config.max_iterations)
                return None

            for _ in range(batch_limit):
                y = (y * y + c) % n
                q = (q * (x - y)) % n

            iterations += batch_limit
            g = math.gcd(q, n)
            k += config.batch_size
        r *= 2

    # The cycle collapsed into g == n — step back one at a time to recover.
    if g == n:
        for _ in range(config.max_iterations):
            ys = (ys * ys + c) % n
            g = math.gcd(abs(x - ys), n)
            if g > 1:
                break
        else:
            logger.warning("backtrack cap n={n}", n=n)
            return None

    return g if 1 < g < n else None


def pollard_brent(n: int, config: FactoriserConfig) -> int:
    """Find a non-trivial factor of n, retrying with fresh seeds as needed.

    Args:
        n: A composite integer >= 4.
        config: Algorithm parameters controlling retry budget.

    Returns:
        A non-trivial factor. Returns n itself when n is prime.

    Raises:
        RuntimeError: If no factor is found within config.max_retries attempts.
    """
    # Trial division fast-path for tiny primes
    # (Fixes Pollard's Rho cycle exhaustion on tiny fields like n=15, 35)
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59,
              61, 67, 71, 73):
        if n % p == 0:
            return p
    if is_prime(n):
        return n

    root = math.isqrt(n)
    if root * root == n:
        return root

    for attempt in range(1, config.max_retries + 1):
        y = random.randint(1, n - 1)
        c = random.randint(1, n - 1)
        logger.debug("attempt={attempt} n={n} y={y} c={c}",
                     attempt=attempt,
                     n=n,
                     y=y,
                     c=c)

        factor = pollard_brent_attempt(n, y, c, config)
        if factor is not None:
            logger.debug("factor={factor} n={n}", factor=factor, n=n)
            return factor

    raise RuntimeError(
        f"pollard_brent failed for n={n} after {config.max_retries} attempts. "
        "Increase max_retries or max_iterations in FactoriserConfig.")


def _factor_yield(n: int, config: FactoriserConfig):
    """Recursively yield prime factors of n."""
    if n < 2:
        return
    if is_prime(n):
        yield n
        return

    d = pollard_brent(n, config)
    logger.debug("split n={n} d={d} r={r}", n=n, d=d, r=n // d)
    yield from _factor_yield(d, config)
    yield from _factor_yield(n // d, config)


def factor_flatten(n: int, config: FactoriserConfig) -> list[int]:
    """Recursively split n until every part is prime.

    Args:
        n: A positive integer.
        config: Algorithm parameters forwarded to pollard_brent.

    Returns:
        A flat list of prime factors (unsorted, with repetition).
        Returns [] for n < 2.
    """
    return list(_factor_yield(n, config))


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

    Returns:
        A FactorisationResult containing the complete decomposition.

    Raises:
        TypeError: If n is not a plain int.
        RuntimeError: If factorisation exhausts its retry budget.
    """
    validate_int(n)
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

    raw_factors = factor_flatten(abs_n, cfg)
    powers = dict(Counter(raw_factors))
    factors = sorted(powers.keys())
    result = FactorisationResult(
        original=n,
        sign=sign,
        factors=factors,
        powers=powers,
        is_prime=(len(factors) == 1 and sum(powers.values()) == 1) and
        abs_n > 1,
    )

    logger.info("factorise complete n={n} factors={factors}",
                n=n,
                factors=factors)
    return result
