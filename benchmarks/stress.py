"""Stress test: Factorise all integers from 1 to 1 Million on all cores.

This script divides the range into chunks and processes them in parallel using a
ProcessPoolExecutor. For every number, it verifies that the product of the
generated prime factors equals the original number.

Run with:
    python -m benchmarks.stress
"""

import math
import os
import time
from concurrent.futures import as_completed
from concurrent.futures.process import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Final

from loguru import logger
from rich.console import Console
from rich.progress import BarColumn
from rich.progress import MofNCompleteColumn
from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TaskProgressColumn
from rich.progress import TimeElapsedColumn
from rich.progress import TimeRemainingColumn

from source import FactoriserConfig
from source import factorise


@dataclass(frozen=True)
class ChunkResult:
    """Result of processing a chunk of integers."""

    processed: int
    errors: int
    elapsed: float


MAX_NUMBER: Final[int] = 1_000_000
STRESS_CI_MAX: Final[int] = (
    10_000  # Reduced range used by the pytest entrypoint.
)
CORES_AVAILABLE: Final[int] = os.cpu_count() or 4
CHUNK_SIZE: Final[int] = max(10_000, MAX_NUMBER // (CORES_AVAILABLE * 8))
CONFIG: Final[FactoriserConfig] = FactoriserConfig(
    batch_size=256, max_retries=10
)


def _is_factorisation_valid(number: int, result_powers: dict[int, int]) -> bool:
    """Return True when reconstructed prime powers equal the input integer."""
    if number <= 1:
        return True
    product = 1
    for prime, power in result_powers.items():
        product *= prime**power
    return product == number


def process_chunk(start: int, end: int) -> ChunkResult:
    """Process a range of integers [start, end), verifying factorisation correctness."""
    start_time = time.perf_counter()
    errors = 0
    processed = 0

    for number in range(start, end):
        result = factorise(number, CONFIG)
        if not _is_factorisation_valid(number, result.powers):
            errors += 1
            logger.error(
                "Validation failed! n={n}, factors={factors}",
                n=number,
                factors=result.factors,
            )

        processed += 1

    return ChunkResult(
        processed=processed,
        errors=errors,
        elapsed=time.perf_counter() - start_time,
    )


def main() -> None:
    """Execute the multicore 1 Million integer factorisation validation suite."""
    console = Console()
    console.print(
        "[bold cyan]Starting 1 Million Multicore Stress Test[/bold cyan]"
    )
    console.print(f"Target: [bold]1 to {MAX_NUMBER:,}[/bold]")
    console.print(f"Cores:  [bold]{CORES_AVAILABLE}[/bold]")

    chunk_count = MAX_NUMBER // CHUNK_SIZE
    console.print(
        f"Chunks: [bold]{chunk_count:,}[/bold] (Size: {CHUNK_SIZE:,})\n"
    )

    chunks = [
        (i, min(i + CHUNK_SIZE, MAX_NUMBER + 1))
        for i in range(1, MAX_NUMBER + 1, CHUNK_SIZE)
    ]

    total_processed = 0
    total_errors = 0
    global_start = time.perf_counter()

    progress = Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    with progress:
        task = progress.add_task("[cyan]Factorising...", total=MAX_NUMBER)

        with ProcessPoolExecutor(max_workers=CORES_AVAILABLE) as executor:
            futures = [
                executor.submit(process_chunk, block_start, block_end)
                for block_start, block_end in chunks
            ]

            for future in as_completed(futures):
                try:
                    result: ChunkResult = future.result()
                    total_processed += result.processed
                    total_errors += result.errors
                    progress.advance(task, advance=result.processed)
                except OSError as err:
                    logger.error("Chunk failed with OS error: {e}", e=err)
                    total_errors += 1
                except Exception as err:
                    logger.error(
                        "Chunk failed with unexpected error: {e}", e=err
                    )
                    total_errors += 1

    elapsed = time.perf_counter() - global_start
    ops_per_second = total_processed / elapsed

    console.print("\n[bold green]Stress Test Complete![/bold green]")
    console.print(
        f"Time Elapsed:   {elapsed:.2f} seconds ({elapsed / 3600:.2f} hours)"
    )
    console.print(
        f"Throughput:     {ops_per_second:,.0f} factorisations / second"
    )
    console.print(f"Total Processed:{total_processed:,}")

    if total_errors == 0:
        console.print(
            "[bold green]Verification:   PASSED (0 errors)[/bold green]"
        )
    else:
        console.print(
            f"[bold red]Verification:   FAILED ({total_errors} errors)[/bold red]"
        )


def test_stress_correctness() -> None:
    """Pytest-compatible stress test: verify factorisation correctness for 1..STRESS_CI_MAX.

    Uses a single process to keep CI runtime predictable. Every composite
    number's prime factors are multiplied back together and compared against
    the original value — any mismatch is a hard failure.
    """
    errors: list[str] = []
    ci_config = FactoriserConfig(batch_size=256, max_retries=10)

    for number in range(1, STRESS_CI_MAX + 1):
        result = factorise(number, ci_config)
        if not _is_factorisation_valid(number, result.powers):
            product = math.prod(
                prime**power for prime, power in result.powers.items()
            )
            errors.append(
                f"n={number}: factors={result.factors}, product={product}"
            )

    assert not errors, f"{len(errors)} factorisation errors:\n" + "\n".join(
        errors[:10]
    )


if __name__ == "__main__":
    main()
