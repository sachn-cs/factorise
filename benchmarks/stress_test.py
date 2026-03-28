"""Stress test: Factorise all integers from 1 to 1 Million on all cores.

This script divides the 10-Million range into chunks and processes them
in parallel using a ProcessPoolExecutor. For every number, it verifies
that the product of the generated prime factors equals the original number.

Run with:
    python3 benchmarks/stress_test.py
"""
# isort: skip_file

import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Final

# Ensure the 'src' directory is in the import path so 'factorise' resolves cleanly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loguru import logger  # pylint: disable=wrong-import-position # noqa: E402
from rich.console import Console  # pylint: disable=wrong-import-position # noqa: E402
from rich.progress import (  # pylint: disable=wrong-import-position # noqa: E402
    BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TaskProgressColumn,
    TimeElapsedColumn, TimeRemainingColumn,
)

from factorise import (  # pylint: disable=wrong-import-position # noqa: E402
    FactoriserConfig,
    factorise,
)

# Configuration
MAX_NUMBER: Final[int] = 1_000_000
CORES_AVAILABLE: Final[int] = os.cpu_count() or 4
CHUNK_SIZE: Final[int] = max(10_000, MAX_NUMBER // (CORES_AVAILABLE * 8))

# Use an optimized config for bulk processing
CONFIG: Final[FactoriserConfig] = FactoriserConfig(batch_size=256,
                                                   max_retries=10)


def process_chunk(start: int, end: int) -> tuple[int, int, float]:
    """Process a range of integers [start, end), verifying factorisation correctness.

    Args:
        start: Inclusive start sequence of the integer range.
        end: Exclusive end barrier of the integer range.

    Returns:
        A tuple structured as (numbers_processed, validation_errors, elapsed_time).
    """
    start_time: float = time.time()
    errors: int = 0
    processed: int = 0

    for number in range(start, end):
        result = factorise(number, CONFIG)

        if number > 1:
            product = math.prod(p**e for p, e in result.powers.items())
            if product != number:
                errors += 1
                logger.error(
                    "Validation failed! n={n}, factors={factors}",
                    n=number,
                    factors=result.factors,
                )

        processed += 1

    return processed, errors, time.time() - start_time


def main() -> None:
    """Execute the multicore 1 Million integer factorisation validation suite."""
    # pylint: disable=too-many-locals
    console = Console()
    console.print(
        "[bold cyan]Starting 1 Million Multicore Stress Test[/bold cyan]")
    console.print(f"Target: [bold]1 to {MAX_NUMBER:,}[/bold]")
    console.print(f"Cores:  [bold]{CORES_AVAILABLE}[/bold]")

    chunk_count: int = MAX_NUMBER // CHUNK_SIZE
    console.print(
        f"Chunks: [bold]{chunk_count:,}[/bold] (Size: {CHUNK_SIZE:,})\n")

    chunks: list[tuple[int,
                       int]] = [(i, min(i + CHUNK_SIZE, MAX_NUMBER + 1))
                                for i in range(1, MAX_NUMBER + 1, CHUNK_SIZE)]

    total_processed: int = 0
    total_errors: int = 0
    global_start: float = time.time()

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
            futures = {
                executor.submit(process_chunk, block_start, block_end):
                    (block_start, block_end) for block_start, block_end in chunks
            }

            for future in as_completed(futures):
                try:
                    processed, errors, _ = future.result()
                    total_processed += processed
                    total_errors += errors
                    progress.advance(task, advance=processed)
                except Exception as err:  # pylint: disable=broad-exception-caught
                    logger.error("Chunk failed executing validation suite: {e}",
                                 e=err)
                    total_errors += 1

    elapsed: float = time.time() - global_start
    ops_per_second: float = total_processed / elapsed

    console.print("\n[bold green]Stress Test Complete![/bold green]")
    console.print(
        f"Time Elapsed:   {elapsed:.2f} seconds ({elapsed / 3600:.2f} hours)")
    console.print(
        f"Throughput:     {ops_per_second:,.0f} factorisations / second")
    console.print(f"Total Processed:{total_processed:,}")

    if total_errors == 0:
        console.print(
            "[bold green]Verification:   PASSED (0 errors)[/bold green]")
    else:
        console.print(
            f"[bold red]Verification:   FAILED ({total_errors} errors)[/bold red]"
        )


if __name__ == "__main__":
    main()
