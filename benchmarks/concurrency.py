"""Lightweight concurrency benchmark for the factorise package."""

import concurrent.futures
import time
from collections.abc import Callable

from factorise.core import FactoriserConfig
from factorise.core import factorise

# Test numbers: semiprimes that require Pollard-Brent but are quick
NUMBERS = [
    8051,
    8633,
    10601,
    11501,
    15151,
    16381,
    17501,
    19151,
    21501,
    25151,
] * 2  # Total 20 iterations
CONFIG = FactoriserConfig(seed=42)


def factorise_wrapper(n: int) -> None:
    """Top-level wrapper to ensure picklability for multiprocessing."""
    factorise(n, CONFIG)


def run_sequential() -> float:
    start = time.perf_counter()
    for n in NUMBERS:
        factorise_wrapper(n)
    return time.perf_counter() - start


def run_threads() -> float:
    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        list(executor.map(factorise_wrapper, NUMBERS))
    return time.perf_counter() - start


def run_processes() -> float:
    start = time.perf_counter()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        list(executor.map(factorise_wrapper, NUMBERS))
    return time.perf_counter() - start


def main() -> None:
    print("-" * 50)
    print("Factorise Concurrency Benchmark")
    print(f"Workload: {len(NUMBERS)} semiprimes (Pollard-Brent path)")
    print("-" * 50)

    # Run once to warm up (pre-jitter)
    factorise(NUMBERS[0], CONFIG)

    results = [
        ("Sequential", run_sequential()),
        ("Multithreaded", run_threads()),
        ("Multiprocessed", run_processes()),
    ]

    # Sort by time
    results.sort(key=lambda x: x[1])

    for mode, duration in results:
        print(f"{mode:<15}: {duration:>8.4f} seconds")

    print("-" * 50)
    best_mode, best_time = results[0]
    worst_mode, worst_time = results[-1]
    speedup = worst_time / best_time
    print(f"Best: {best_mode} ({speedup:.2f}x faster than {worst_mode})")
    print("-" * 50)


if __name__ == "__main__":
    main()
