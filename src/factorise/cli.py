"""Command-line interface for factorise.

Provides the `factorise` Typer application. It handles user input mapping,
FactoriserConfig construction from the environment, graceful signal handling
for shutdown, and formatting the FactorisationResult into Rich tables.
"""

import signal
import sys
from types import FrameType
from typing import Final

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from factorise.core import FactorisationResult, FactoriserConfig, factorise

# Configuration Constants
LOGGER_NAME: Final[str] = "factorise"
LOG_FORMAT: Final[str] = "{time} {level} {message}"
DEFAULT_LOG_LEVEL: Final[str] = "WARNING"
SUCCESS_EXIT_CODE: Final[int] = 0
ERROR_EXIT_CODE: Final[int] = 1

app = typer.Typer(
    help="Fast prime factorisation CLI.",
    add_completion=False,
)
console = Console()

# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------


def handle_signal(signum: int, _frame: FrameType | None) -> None:
    """Log the received system signal and exit the sequence cleanly.

    Args:
        signum: The integer identifier of the caught signal.
        _frame: The current stack frame (unused).
    """
    logger.info("Received signal {sig}, shutting down.",
                sig=signal.Signals(signum).name)
    sys.exit(SUCCESS_EXIT_CODE)


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def display_prime(number: int) -> None:
    """Print a Rich panel announcing that the evaluated number is prime.

    Args:
        number: The evaluated prime integer.
    """
    console.print(
        Panel(f"[bold green]{number}[/bold green] is a prime number!",
              title="Result"))


def display_factors(result: FactorisationResult, verbose: bool) -> None:
    """Print the prime decomposition as a formatted Rich table.

    Args:
        result: The fully computed structured factorisation result.
        verbose: True to append the mathematical factorisation expression string.
    """
    table = Table(title=f"Factorisation of {result.original}")
    table.add_column("Prime Factor", justify="right", style="cyan")
    table.add_column("Exponent", justify="right", style="magenta")

    for prime, exponent in result.powers.items():
        table.add_row(str(prime), str(exponent))

    console.print(table)

    if not verbose:
        return

    console.print(f"\n[dim]Full expression: {result.expression()}[/dim]")


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------


def configure_logging(log_level: str) -> None:
    """Configure the global Loguru logger formatting and verbosity.

    Args:
        log_level: The verbosity configuration to pass into loguru (e.g. DEBUG).
    """
    logger.enable(LOGGER_NAME)
    logger.remove()
    logger.add(sys.stderr, level=log_level.upper(), format=LOG_FORMAT)


@app.command()
def main(
    number: int = typer.Argument(..., help="The integer to factorise."),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Print the full prime product expression."),
    log_level: str = typer.Option(
        DEFAULT_LOG_LEVEL,
        "--log-level",
        envvar="FACTORISE_LOG_LEVEL",
        help="Logging level (DEBUG, INFO, WARNING, ERROR).",
    ),
) -> None:
    """Factorise a number and display its prime decomposition.

    Args:
        number: The target integer to be factorised via the mathematical engine.
        verbose: A boolean flag triggering the display of the multiplication string.
        log_level: The verbosity configuration to pass into loguru (e.g. DEBUG).

    Raises:
        typer.Exit: Raised on invalid input (TypeError) or solver failure (RuntimeError).
    """
    configure_logging(log_level)
    logger.info("CLI invoked number={number}", number=number)

    try:
        config = FactoriserConfig.from_env()
        result = factorise(number, config)
    except TypeError as exc:
        logger.error("Invalid input type: {exc}", exc=exc)
        console.print(f"[bold red]Input Error:[/bold red] {exc}")
        raise typer.Exit(code=ERROR_EXIT_CODE) from exc
    except ValueError as exc:
        logger.error("Invalid input value: {exc}", exc=exc)
        console.print(f"[bold red]Value Error:[/bold red] {exc}")
        raise typer.Exit(code=ERROR_EXIT_CODE) from exc
    except RuntimeError as exc:
        logger.error("Factorisation failed: {exc}", exc=exc)
        console.print(f"[bold red]Runtime Error:[/bold red] {exc}")
        raise typer.Exit(code=ERROR_EXIT_CODE) from exc

    if result.is_prime:
        display_prime(number)
    else:
        display_factors(result, verbose)

    logger.info("CLI complete factors={factors}", factors=result.factors)


if __name__ == "__main__":
    app()
