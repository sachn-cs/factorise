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

# Deterministic witnesses for n < 2^64 (12 bases).
WITNESSES: tuple[int, ...] = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
# Reduced witness set for n < 10^12 (6 bases, sufficient per Jaeschke 1993).
WITNESSES_SMALL: tuple[int, ...] = (2, 3, 5, 7, 11, 13)
WITNESSES_SET: frozenset[int] = frozenset(WITNESSES)
TRIAL_DIVISION_PRIMES: tuple[int, ...] = (
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
    """

    batch_size: int = 128
    max_iterations: int = 10_000_000
    max_retries: int = 20
    seed: int | None = None

    def __post_init__(self) -> None:
        """Validate fields immediately — fail fast at construction time."""
        if self.batch_size < 1 or self.batch_size > 10_000:
            raise ValueError(
                f"batch_size must be >= 1 and <= 10_000, got {self.batch_size}"
            )
        if self.max_iterations < 1 or self.max_iterations > 100_000_000:
            raise ValueError(
                f"max_iterations must be >= 1 and <= 100_000_000, got {self.max_iterations}"
            )
        if self.max_retries < 1 or self.max_retries > 100:
            raise ValueError(
                f"max_retries must be >= 1 and <= 100, got {self.max_retries}"
            )

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
            max_iterations=int(
                os.getenv("FACTORISE_MAX_ITERATIONS", "10000000")
            ),
            max_retries=int(os.getenv("FACTORISE_MAX_RETRIES", "20")),
            seed=int(seed) if seed is not None else None,
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
            f"{name} must be a plain int, got {type(value).__name__!r}"
        )


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

    witnesses = WITNESSES_SMALL if n < 10**12 else WITNESSES
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
# Factorisation — Pollard-Brent, expressed as three focused functions.
# ---------------------------------------------------------------------------


class AttemptStatus(enum.Enum):
    """Failure modes for a single Pollard-Brent attempt."""

    SUCCESS = enum.auto()
    ALGORITHM_FAILURE = enum.auto()
    ITERATION_CAP_HIT = enum.auto()


@dataclasses.dataclass(frozen=True)
class AttemptResult:
    """Result of a single Pollard-Brent attempt."""

    status: AttemptStatus
    iterations_used: int
    factor: int | None = None


def pollard_brent_attempt(
    n: int,
    y: int,
    c: int,
    config: FactoriserConfig,
    max_iterations: int,
) -> AttemptResult:
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
        An AttemptResult containing the outcome and iterations used.
    """
    validate_int(n)
    if not isinstance(config, FactoriserConfig):
        raise TypeError(
            f"config must be FactoriserConfig, got {type(config).__name__!r}"
        )

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
            if iterations + batch_limit > max_iterations:
                batch_limit = max_iterations - iterations

            if batch_limit <= 0:
                logger.warning(
                    "iteration cap n={n} limit={limit}",
                    n=n,
                    limit=max_iterations,
                )
                return AttemptResult(
                    AttemptStatus.ITERATION_CAP_HIT, iterations
                )

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
                        return AttemptResult(AttemptStatus.SUCCESS, iterations, g)

            iterations += batch_limit
            g = math.gcd(q, n)
            k += config.batch_size
        r *= 2

    # The cycle collapsed into g == n — step back one at a time to recover.
    if g == n:
        backtrack_budget = max_iterations - iterations
        if backtrack_budget <= 0:
            return AttemptResult(AttemptStatus.ITERATION_CAP_HIT, iterations)
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
                return AttemptResult(AttemptStatus.ALGORITHM_FAILURE, iterations)

    if 1 < g < n:
        return AttemptResult(AttemptStatus.SUCCESS, iterations, g)
    return AttemptResult(AttemptStatus.ALGORITHM_FAILURE, iterations)


def pollard_brent(n: int, config: FactoriserConfig) -> int:
    """Find a non-trivial factor of n, retrying with fresh seeds as needed.

    Args:
        n: A composite integer >= 4.
        config: Algorithm parameters controlling retry budget.

    Returns:
        A non-trivial factor. Returns n itself when n is prime.

    Raises:
        FactorisationError: If no factor is found within config.max_retries attempts.
    """
    validate_int(n)
    if not isinstance(config, FactoriserConfig):
        raise TypeError(
            f"config must be FactoriserConfig, got {type(config).__name__!r}"
        )

    # Trial division fast-path for tiny primes
    # (Fixes Pollard's Rho cycle exhaustion on tiny fields like n=15, 35)
    for p in TRIAL_DIVISION_PRIMES:
        if n % p == 0:
            return p
    if is_prime(n):
        return n

    root = math.isqrt(n)
    if root * root == n:
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
        logger.debug(
            "attempt={attempt} n={n} y={y} c={c}",
            attempt=attempt,
            n=n,
            y=y,
            c=c,
        )

        result = pollard_brent_attempt(n, y, c, config, remaining_iterations)
        remaining_iterations -= result.iterations_used

        if result.status == AttemptStatus.SUCCESS:
            if result.factor is None:
                raise FactorisationError(
                    "pollard_brent returned SUCCESS without a factor; this is a bug."
                )
            logger.debug("factor={factor} n={n}", factor=result.factor, n=n)
            return result.factor

        if (
            remaining_iterations <= 0
            or result.status == AttemptStatus.ITERATION_CAP_HIT
        ):
            logger.error("global iteration cap hit for n={n}", n=n)
            break

    raise FactorisationError(
        f"pollard_brent failed for n={n} after {attempt} attempts. "
        "Increase max_retries or max_iterations in FactoriserConfig."
    )


def _factor_yield(
    n: int, config: FactoriserConfig
) -> Generator[int, None, None]:
    """Iteratively yield prime factors of n using an explicit stack.

    Uses O(log n) stack space (worst case) but avoids call-stack overhead.
    """
    stack: list[int] = [n]
    while stack:
        current = stack.pop()
        if current < 2:
            continue
        if is_prime(current):
            yield current
            continue

        d = pollard_brent(current, config)
        logger.debug("split n={n} d={d} r={r}", n=current, d=d, r=current // d)
        stack.append(d)
        stack.append(current // d)


# Note: _factor_yield is a generator for memory efficiency on deeply nested factorisations.
def factor_flatten(n: int, config: FactoriserConfig) -> list[int]:
    """Recursively split n until every part is prime.

    Args:
        n: A positive integer.
        config: Algorithm parameters forwarded to pollard_brent.

    Returns:
        A flat list of prime factors (unsorted, with repetition).
        Returns [] for n < 2.
    """
    validate_int(n)
    if not isinstance(config, FactoriserConfig):
        raise TypeError(
            f"config must be FactoriserConfig, got {type(config).__name__!r}"
        )
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
        FactorisationError: If factorisation exhausts its retry budget.
    """
    validate_int(n)
    if config is not None and not isinstance(config, FactoriserConfig):
        raise TypeError(
            f"config must be FactoriserConfig, got {type(config).__name__!r}"
        )
    cfg = config if config is not None else FactoriserConfig.from_env()
    logger.info("factorise start n={n}", n=n)

    if n == 0:
        return FactorisationResult(
            original=0, sign=1, factors=[], powers={}, is_prime=False
        )

    sign = -1 if n < 0 else 1
    abs_n = abs(n)

    if abs_n == 1:
        return FactorisationResult(
            original=n, sign=sign, factors=[], powers={}, is_prime=False
        )

    raw_factors = factor_flatten(abs_n, cfg)
    counts = Counter(raw_factors)
    factors = sorted(counts.keys())
    powers = {prime: counts[prime] for prime in factors}
    result = FactorisationResult(
        original=n,
        sign=sign,
        factors=factors,
        powers=powers,
        is_prime=(len(factors) == 1 and sum(powers.values()) == 1)
        and abs_n > 1,
    )

    logger.info(
        "factorise complete n={n} factors={factors}", n=n, factors=factors
    )
    return result
