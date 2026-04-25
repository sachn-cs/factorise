"""Command-line interface for factorise.

Provides the `factorise` Typer application. It handles user input parsing,
FactoriserConfig construction from the environment, graceful signal handling
for shutdown, and formatting the FactorisationResult into Rich tables.
"""

__all__ = ["app"]

import json
import os
import signal
import sys
import traceback
from types import FrameType
from typing import Final

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from factorise.config import FactoriserConfig
from factorise.core import FactorisationError
from factorise.core import FactorisationResult
from factorise.core import factorise

# Configuration Constants
LOGGER_NAME: Final[str] = "factorise"
LOG_FORMAT: Final[str] = "{time} {level} {message}"
DEFAULT_LOG_LEVEL: Final[str] = "WARNING"
DEFAULT_LOG_FORMAT: Final[str] = "human"
SUCCESS_EXIT_CODE: Final[int] = 0
ERROR_EXIT_CODE: Final[int] = 1
VALID_LOG_LEVELS: Final[frozenset[str]] = frozenset(
    {"DEBUG", "INFO", "WARNING", "ERROR"},)
VALID_LOG_FORMATS: Final[frozenset[str]] = frozenset({"human", "json"})
TRACE_CONTEXT_ENV_NAMES: Final[dict[str, str]] = {
    "request_id": "FACTORISE_REQUEST_ID",
    "correlation_id": "FACTORISE_CORRELATION_ID",
    "trace_id": "FACTORISE_TRACE_ID",
    "span_id": "FACTORISE_SPAN_ID",
    "session_id": "FACTORISE_SESSION_ID",
}

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
        frame: The current stack frame (unused).

    """
    logger.info(
        "Received signal {sig}, shutting down.",
        sig=signal.Signals(signum).name,
    )
    code = 128 + signum
    sys.exit(code)


def register_signal_handlers() -> None:
    """Register SIGINT and SIGTERM handlers for graceful CLI shutdown."""
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
        Panel(
            f"[bold green]{number}[/bold green] is a prime number!",
            title="Result",
        ),)


def display_factors(result: FactorisationResult, *, verbose: bool) -> None:
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


def normalize_log_level(log_level: str) -> str:
    """Normalize and validate logging level."""
    normalized_level = log_level.upper()
    if normalized_level not in VALID_LOG_LEVELS:
        allowed = ", ".join(sorted(VALID_LOG_LEVELS))
        raise ValueError(f"log_level must be one of: {allowed}")
    return normalized_level


def normalize_log_format(log_format: str) -> str:
    """Normalize and validate logging format."""
    normalized_format = log_format.lower()
    if normalized_format not in VALID_LOG_FORMATS:
        allowed = ", ".join(sorted(VALID_LOG_FORMATS))
        raise ValueError(f"log_format must be one of: {allowed}")
    return normalized_format


def resolve_trace_context(record: dict[str, object]) -> dict[str, str]:
    """Resolve trace context fields from bound logger extras or environment."""
    context: dict[str, str] = {}
    extras = record.get("extra")
    extra_values = extras if isinstance(extras, dict) else {}
    for field, env_name in TRACE_CONTEXT_ENV_NAMES.items():
        value = (extra_values.get(field)
                 if isinstance(extra_values, dict) else None)
        if value in (None, ""):
            value = os.getenv(env_name)
        if value not in (None, ""):
            context[field] = str(value)
    return context


def json_log_sink(message: object) -> None:
    """Emit one structured JSON log object per line to stderr."""
    record = message.record  # type: ignore[attr-defined]
    payload: dict[str, object] = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "logger": str(record["name"]),
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line_number": record["line"],
        "process_id": record["process"].id,
        "thread_id": record["thread"].id,
    }

    payload.update(resolve_trace_context(record))

    exception = record.get("exception")
    if exception is not None:
        payload["exception"] = {
            "type":
                exception.type.__name__ if exception.type is not None else None,
            "message":
                str(exception.value) if exception.value is not None else None,
            "stacktrace":
                "".join(
                    traceback.format_exception(
                        exception.type,
                        exception.value,
                        exception.traceback,
                    ),),
        }

    sys.stderr.write(json.dumps(payload, ensure_ascii=True) + "\n")


def configure_logging(
    log_level: str,
    log_format: str = DEFAULT_LOG_FORMAT,
) -> None:
    """Configure the global Loguru logger formatting and verbosity.

    Args:
        log_level: The verbosity configuration to pass into loguru (e.g. DEBUG).
        log_format: The output format to use (human or json).

    Raises:
        ValueError: If log_level or log_format is unsupported.

    """
    normalized_level = normalize_log_level(log_level)
    normalized_format = normalize_log_format(log_format)
    logger.enable(LOGGER_NAME)
    logger.remove()
    if normalized_format == "json":
        logger.add(
            json_log_sink,
            level=normalized_level,
            backtrace=False,
            diagnose=False,
        )
        return
    logger.add(sys.stderr, level=normalized_level, format=LOG_FORMAT)


@app.command()
def main(
    number: int = typer.Argument(..., help="The integer to factorise."),
    *,
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Print the full prime product expression.",
    ),
    log_level: str = typer.Option(
        DEFAULT_LOG_LEVEL,
        "--log-level",
        envvar="FACTORISE_LOG_LEVEL",
        help="Logging level (DEBUG, INFO, WARNING, ERROR).",
    ),
    log_format: str = typer.Option(
        DEFAULT_LOG_FORMAT,
        "--log-format",
        envvar="FACTORISE_LOG_FORMAT",
        help="Logging format (human, json).",
    ),
) -> None:
    """Factorise a number and display its prime decomposition.

    Args:
        number: The target integer to be factorised via the mathematical engine.
        verbose: A boolean flag triggering the display of the multiplication string.
        log_level: The verbosity configuration to pass into loguru (e.g. DEBUG).
        log_format: The output format for logs, either human or json.

    Raises:
        typer.Exit: Raised on invalid input, invalid config, or factorisation failure.

    """
    try:
        configure_logging(log_level, log_format)
    except ValueError as exc:
        console.print(f"[bold red]Configuration Error:[/bold red] {exc}")
        raise typer.Exit(code=ERROR_EXIT_CODE) from exc

    register_signal_handlers()

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
    except FactorisationError as exc:
        logger.error("Factorisation failed: {exc}", exc=exc)
        console.print(f"[bold red]Runtime Error:[/bold red] {exc}")
        raise typer.Exit(code=ERROR_EXIT_CODE) from exc

    if result.is_prime:
        display_prime(number)
    else:
        display_factors(result, verbose=verbose)

    logger.info("CLI complete factors={factors}", factors=result.factors)


if __name__ == "__main__":  # pragma: no cover
    app()
