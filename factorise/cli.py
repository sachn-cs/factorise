"""Command-line interface for factorise.

Provides the `factorise` CLI application using only Python standard library.
"""

from __future__ import annotations

__all__ = ["main"]

import argparse
import logging
import signal
import sys
from types import FrameType

from factorise.config import FactoriserConfig
from factorise.core import FactorisationError
from factorise.core import FactorisationResult
from factorise.core import factorise

LOGGER_NAME = "factorise"
DEFAULT_LOG_LEVEL = "WARNING"


def handle_signal(signum: int, _frame: FrameType | None) -> None:
    """Log the received system signal and exit cleanly."""
    logging.getLogger(LOGGER_NAME).info(
        "Received signal %s, shutting down.",
        signal.Signals(signum).name,
    )
    sys.exit(128 + signum)


def register_signal_handlers() -> None:
    """Register SIGINT and SIGTERM handlers for graceful CLI shutdown."""
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


def _ansi_bold(label: str) -> str:
    """Return ANSI escape for bold text."""
    return f"\033[1m{label}\033[0m"


def _ansi_dim(label: str) -> str:
    """Return ANSI escape for dim text."""
    return f"\033[2m{label}\033[0m"


def _ansi_green(label: str) -> str:
    """Return ANSI escape for green text."""
    return f"\033[32m{label}\033[0m"


def _ansi_red(label: str) -> str:
    """Return ANSI escape for red text."""
    return f"\033[31m{label}\033[0m"


def _ansi_cyan(label: str) -> str:
    """Return ANSI escape for cyan text."""
    return f"\033[36m{label}\033[0m"


def _ansi_magenta(label: str) -> str:
    """Return ANSI escape for magenta text."""
    return f"\033[35m{label}\033[0m"


def display_prime(number: int) -> None:
    """Print an announcement that the number is prime."""
    print(f"\n{_ansi_green('✓')} {number} is a prime number!\n")


def display_factors(result: FactorisationResult, *, verbose: bool) -> None:
    """Print the prime decomposition as a formatted table."""
    print(f"\n{_ansi_bold('─' * 40)}")
    print(f"  Factorisation of {result.original}")
    print(f"{_ansi_bold('─' * 40)}")
    print(f"  {'Prime Factor':<20} {'Exponent':>10}")
    print(f"  {_ansi_bold('─' * 20)}  {_ansi_bold('─' * 10)}")
    for prime, exponent in result.powers.items():
        print(f"  {_ansi_cyan(str(prime)):<20} {_ansi_magenta(str(exponent)):>10}")
    print(f"{_ansi_bold('─' * 40)}\n")

    if verbose:
        print(f"  {_ansi_dim('Full expression:')} {result.expression()}\n")


def configure_logging(log_level: str) -> None:
    """Configure the global logger formatting and verbosity."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        valid = ", ".join(sorted(
            name for name in ("DEBUG", "INFO", "WARNING", "ERROR")
            if hasattr(logging, name)
        ))
        raise ValueError(f"log_level must be one of: {valid}")

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger(LOGGER_NAME).setLevel(numeric_level)


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
        "-v", "--verbose",
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


def main(argv: list[str] | None = None) -> None:
    """Factorise a number and display its prime decomposition."""
    args = parse_args(argv)

    try:
        configure_logging(args.log_level)
    except ValueError as exc:
        print(f"{_ansi_red('Configuration Error:')} {exc}", file=sys.stderr)
        sys.exit(1)

    register_signal_handlers()
    logger = logging.getLogger(LOGGER_NAME)
    logger.info("CLI invoked number=%d", args.number)

    try:
        config = FactoriserConfig.from_env()
        result = factorise(args.number, config)
    except TypeError as exc:
        logger.error("Invalid input type: %s", exc)
        print(f"{_ansi_red('Input Error:')} {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        logger.error("Invalid value: %s", exc)
        print(f"{_ansi_red('Value Error:')} {exc}", file=sys.stderr)
        sys.exit(1)
    except FactorisationError as exc:
        logger.error("Factorisation failed: %s", exc)
        print(f"{_ansi_red('Runtime Error:')} {exc}", file=sys.stderr)
        sys.exit(1)

    if result.is_prime:
        display_prime(args.number)
    else:
        display_factors(result, verbose=args.verbose)

    logger.info("CLI complete factors=%s", result.factors)


if __name__ == "__main__":
    main()
