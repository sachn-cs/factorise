"""Stress test: Factorise all integers from 1 to 1 Million on all cores.

This script divides the range into chunks and processes them in parallel using a
ProcessPoolExecutor. For every number, it verifies that the product of the
generated prime factors equals the original number.

Run with:
    python -m benchmarks.stress_test
"""

import math
import os
import time
from concurrent.futures.process import ProcessPoolExecutor
from dataclasses import dataclass
from functools import partial
from typing import Final

from loguru import logger
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from factorise import FactoriserConfig, factorise


@dataclass(frozen=True)
class ChunkResult:
    """Result of processing a chunk of integers."""

    processed: int
    errors: int
    elapsed: float


MAX_NUMBER: Final[int] = 1_000_000
CORES_AVAILABLE: Final[int] = os.cpu_count() or 4
CHUNK_SIZE: Final[int] = max(10_000, MAX_NUMBER // (CORES_AVAILABLE * 8))
CONFIG: Final[FactoriserConfig] = FactoriserConfig(batch_size=256, max_retries=10)


def process_chunk(start: int, end: int) -> ChunkResult:
    """Process a range of integers [start, end), verifying factorisation correctness."""
    start_time = time.time()
    errors = 0
    processed = 0

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

    return ChunkResult(processed=processed, errors=errors, elapsed=time.time() - start_time)


def main() -> None:
    """Execute the multicore 1 Million integer factorisation validation suite."""
    console = Console()
    console.print("[bold cyan]Starting 1 Million Multicore Stress Test[/bold cyan]")
    console.print(f"Target: [bold]1 to {MAX_NUMBER:,}[/bold]")
    console.print(f"Cores:  [bold]{CORES_AVAILABLE}[/bold]")

    chunk_count = MAX_NUMBER // CHUNK_SIZE
    console.print(f"Chunks: [bold]{chunk_count:,}[/bold] (Size: {CHUNK_SIZE:,})\n")

    chunks = [
        (i, min(i + CHUNK_SIZE, MAX_NUMBER + 1)) for i in range(1, MAX_NUMBER + 1, CHUNK_SIZE)
    ]

    total_processed = 0
    total_errors = 0
    global_start = time.time()

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
                executor.submit(partial(process_chunk), block_start, block_end): (
                    block_start,
                    block_end,
                )
                for block_start, block_end in chunks
            }

            for future in futures:
                try:
                    result: ChunkResult = future.result()
                    total_processed += result.processed
                    total_errors += result.errors
                    progress.advance(task, advance=result.processed)
                except OSError as err:
                    logger.error("Chunk failed with OS error: {e}", e=err)
                    total_errors += 1
                except Exception as err:
                    logger.error("Chunk failed with unexpected error: {e}", e=err)
                    total_errors += 1

    elapsed = time.time() - global_start
    ops_per_second = total_processed / elapsed

    console.print("\n[bold green]Stress Test Complete![/bold green]")
    console.print(f"Time Elapsed:   {elapsed:.2f} seconds ({elapsed / 3600:.2f} hours)")
    console.print(f"Throughput:     {ops_per_second:,.0f} factorisations / second")
    console.print(f"Total Processed:{total_processed:,}")

    if total_errors == 0:
        console.print("[bold green]Verification:   PASSED (0 errors)[/bold green]")
    else:
        console.print(f"[bold red]Verification:   FAILED ({total_errors} errors)[/bold red]")


if __name__ == "__main__":
    main()
