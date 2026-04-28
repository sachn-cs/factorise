"""Command-line interface for factorise.

Provides the `factorise` CLI application using only Python standard library.
"""

from __future__ import annotations

__all__ = ["main"]

import argparse
import logging
import signal
import sys
import time
from types import FrameType

from factorise.config import FactoriserConfig
from factorise.core import FactorisationError
from factorise.core import FactorisationResult
from factorise.core import factorise

LOGGER = logging.getLogger("factorise")
DEFAULT_LOG_LEVEL = "WARNING"


def elapsed_ms(start: float) -> float:
    """Return elapsed milliseconds since *start* (from time.monotonic())."""
    return (time.monotonic() - start) * 1000


def ansi(code: str, text: str) -> str:
    """Return *text* wrapped in ANSI escape *code*."""
    return f"\033[{code}m{text}\033[0m"


def display_prime(number: int) -> None:
    """Print an announcement that the number is prime."""
    print(f"\n{ansi('32', '[PRIME]')} {number} is a prime number!\n")


def display_factors(result: FactorisationResult, *, verbose: bool) -> None:
    """Print the prime decomposition as a formatted table."""
    print(f"\n{ansi('1', '─' * 40)}")
    print(f"  Factorisation of {result.original}")
    print(f"{ansi('1', '─' * 40)}")
    print(f"  {'Prime Factor':<20} {'Exponent':>10}")
    print(f"  {ansi('1', '─' * 20)}  {ansi('1', '─' * 10)}")
    for prime, exponent in result.powers.items():
        print(f"  {ansi('36', str(prime)):<20} {ansi('35', str(exponent)):>10}")
    print(f"{ansi('1', '─' * 40)}\n")

    if verbose:
        print(f"  {ansi('2', 'Full expression:')} {result.expression()}\n")


def configure_logging(log_level: str) -> None:
    """Configure the global logger formatting and verbosity."""
    level = getattr(logging, log_level.upper(), None)
    if not isinstance(level, int):
        valid = ", ".join(sorted(("DEBUG", "INFO", "WARNING", "ERROR")))
        raise ValueError(f"log_level must be one of: {valid}")

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    LOGGER.setLevel(level)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="factorise",
        description="Fast prime factorisation CLI.",
    )
    parser.add_argument(
        "number",
        type=int,
        help="The integer to factorise.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print the full prime product expression.",
    )
    parser.add_argument(
        "--log-level",
        default=DEFAULT_LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: WARNING).",
    )
    return parser.parse_args(argv)


def handle_signal(signum: int, _frame: FrameType | None) -> None:
    """Log the received system signal and exit cleanly."""
    LOGGER.info(
        "signal=%s action=shutdown",
        signal.Signals(signum).name,
    )
    sys.exit(128 + signum)


def register_signal_handlers() -> None:
    """Register SIGINT and SIGTERM handlers for graceful CLI shutdown."""
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


def main(argv: list[str] | None = None) -> None:
    """Factorise a number and display its prime decomposition."""
    args = parse_args(argv)

    try:
        configure_logging(args.log_level)
    except ValueError as exc:
        print(f"{ansi('31', 'Configuration Error:')} {exc}", file=sys.stderr)
        sys.exit(1)

    register_signal_handlers()
    LOGGER.info("cli_start number=%d", args.number)
    start = time.monotonic()

    try:
        config = FactoriserConfig.from_env()
        result = factorise(args.number, config)
    except TypeError as exc:
        LOGGER.error("cli_error type=input_error detail=%s", exc)
        print(f"{ansi('31', 'Input Error:')} {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        LOGGER.error("cli_error type=value_error detail=%s", exc)
        print(f"{ansi('31', 'Value Error:')} {exc}", file=sys.stderr)
        sys.exit(1)
    except FactorisationError as exc:
        LOGGER.error("cli_error type=runtime_error detail=%s", exc)
        print(f"{ansi('31', 'Runtime Error:')} {exc}", file=sys.stderr)
        sys.exit(1)

    elapsed = elapsed_ms(start)

    if result.is_prime:
        display_prime(args.number)
    else:
        display_factors(result, verbose=args.verbose)

    LOGGER.info(
        "cli_complete number=%d factors=%s elapsed_ms=%.2f",
        args.number,
        result.factors,
        elapsed,
    )


if __name__ == "__main__":
    main()
