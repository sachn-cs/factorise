"""Timing benchmarks for the factorise package using pytest-benchmark.

Run with:
    pytest benchmarks/timing.py --benchmark-only -v
"""

from collections.abc import Callable
from typing import Any

import pytest

from benchmarks.inputs import FACTORISE_LARGE
from benchmarks.inputs import FACTORISE_MEDIUM
from benchmarks.inputs import FACTORISE_SMALL
from benchmarks.inputs import FIXED_SIZE_INPUTS
from benchmarks.inputs import IS_PRIME_LARGE
from benchmarks.inputs import IS_PRIME_MEDIUM
from benchmarks.inputs import IS_PRIME_SMALL
from benchmarks.inputs import SCALABILITY_INPUTS
from factorise.config import FactoriserConfig
from factorise.core import factorise
from factorise.core import find_nontrivial_factor_pollard_brent as pollard_brent
from factorise.core import is_prime

DEFAULT_CONFIG: FactoriserConfig = FactoriserConfig()

POLLARD_INPUTS: list[tuple[str, int]] = [
    ("pq_5digit", 99_991 * 99_989),
    ("pq_7digit", 9_999_991 * 9_999_973),
    ("pq_large", 32_416_189_987 * 15_485_863),
]

WORKLOAD_MIX: list[int] = [
    12,
    97,
    360,
    123_456_789,
    10**9 + 7,
    99_991 * 99_989,
    2**20,
    30_030,
    32_416_189_987,
    (2**10) * (3**5) * (5**2) * 7,
]

BATCH_SIZES: list[int] = [32, 64, 128, 256, 512]
SEMIPRIME_LARGE: int = 32_416_189_987 * 15_485_863

PERFECT_SQUARES: list[tuple[str, int]] = [
    ("sq_small", 11**2),
    ("sq_medium", 9_973**2),
    ("sq_large", 99_991**2),
]

REPEATED_CALLS: int = 10
CACHING_TEST_NUMBER: int = 123_456_789


@pytest.mark.parametrize("_label,n",
                         IS_PRIME_SMALL,
                         ids=[x[0] for x in IS_PRIME_SMALL])
def test_bench_is_prime_small(benchmark: Callable[..., Any], _label: str,
                              n: int) -> None:
    """Benchmark is_prime on small inputs.

    Args:
        benchmark: Pytest benchmark fixture.
        label: Description of the input.
        n: The integer to test.
    """
    benchmark(is_prime, n)


@pytest.mark.parametrize("_label,n",
                         IS_PRIME_MEDIUM,
                         ids=[x[0] for x in IS_PRIME_MEDIUM])
def test_bench_is_prime_medium(benchmark: Callable[..., Any], _label: str,
                               n: int) -> None:
    """Benchmark is_prime on medium inputs.

    Args:
        benchmark: Pytest benchmark fixture.
        label: Description of the input.
        n: The integer to test.
    """
    benchmark(is_prime, n)


@pytest.mark.parametrize("_label,n",
                         IS_PRIME_LARGE,
                         ids=[x[0] for x in IS_PRIME_LARGE])
def test_bench_is_prime_large(benchmark: Callable[..., Any], _label: str,
                              n: int) -> None:
    """Benchmark is_prime on large inputs.

    Args:
        benchmark: Pytest benchmark fixture.
        label: Description of the input.
        n: The integer to test.
    """
    benchmark(is_prime, n)


@pytest.mark.parametrize("_label,n",
                         FACTORISE_SMALL,
                         ids=[x[0] for x in FACTORISE_SMALL])
def test_bench_factorise_small(benchmark: Callable[..., Any], _label: str,
                               n: int) -> None:
    """Benchmark factorise on small inputs.

    Args:
        benchmark: Pytest benchmark fixture.
        label: Description of the input.
        n: The integer to factorise.
    """
    benchmark(factorise, n, DEFAULT_CONFIG)


@pytest.mark.parametrize("_label,n",
                         FACTORISE_MEDIUM,
                         ids=[x[0] for x in FACTORISE_MEDIUM])
def test_bench_factorise_medium(benchmark: Callable[..., Any], _label: str,
                                n: int) -> None:
    """Benchmark factorise on medium inputs.

    Args:
        benchmark: Pytest benchmark fixture.
        label: Description of the input.
        n: The integer to factorise.
    """
    benchmark(factorise, n, DEFAULT_CONFIG)


@pytest.mark.parametrize("_label,n",
                         FACTORISE_LARGE,
                         ids=[x[0] for x in FACTORISE_LARGE])
def test_bench_factorise_large(benchmark: Callable[..., Any], _label: str,
                               n: int) -> None:
    """Benchmark factorise on large inputs.

    Args:
        benchmark: Pytest benchmark fixture.
        label: Description of the input.
        n: The integer to factorise.
    """
    benchmark(factorise, n, DEFAULT_CONFIG)


@pytest.mark.parametrize("_label,n",
                         POLLARD_INPUTS,
                         ids=[x[0] for x in POLLARD_INPUTS])
def test_bench_pollard_brent(benchmark: Callable[..., Any], _label: str,
                             n: int) -> None:
    """Benchmark isolated pollard_brent cycle detection.

    Args:
        benchmark: Pytest benchmark fixture.
        label: Description of the input.
        n: The composite integer to attempt.
    """
    benchmark(pollard_brent, n, DEFAULT_CONFIG)


def _run_batch(numbers: list[int], config: FactoriserConfig) -> list[Any]:
    """Execute factorise sequentially over a list of numbers.

    Args:
        numbers: Target integers to factorise.
        config: The algorithm parameter config.

    Returns:
        List of factorisation results.
    """
    return [factorise(n, config) for n in numbers]


def test_bench_batch_throughput(benchmark: Callable[..., Any]) -> None:
    """Measure end-to-end throughput on a realistic mixed workload.

    Args:
        benchmark: Pytest benchmark fixture.
    """
    benchmark(_run_batch, WORKLOAD_MIX, DEFAULT_CONFIG)


@pytest.mark.parametrize("_label,n",
                         SCALABILITY_INPUTS,
                         ids=[x[0] for x in SCALABILITY_INPUTS])
def test_bench_scalability(benchmark: Callable[..., Any], _label: str,
                           n: int) -> None:
    """Benchmark logarithmically spaced inputs to show O(n^1/4) growth.

    Args:
        benchmark: Pytest benchmark fixture.
        label: Description of the scalability tier.
        n: The integer to factorise.
    """
    benchmark(factorise, n, DEFAULT_CONFIG)


@pytest.mark.parametrize("batch_size",
                         BATCH_SIZES,
                         ids=[f"batch_{b}" for b in BATCH_SIZES])
def test_bench_batch_size_sensitivity(benchmark: Callable[..., Any],
                                      batch_size: int) -> None:
    """Display how different FACTORISE_BATCH_SIZE values affect throughput.

    Args:
        benchmark: Pytest benchmark fixture.
        batch_size: The experimental batch limit configuration.
    """
    config = FactoriserConfig(batch_size=batch_size)
    benchmark(factorise, SEMIPRIME_LARGE, config)


@pytest.mark.parametrize("_label,n",
                         PERFECT_SQUARES,
                         ids=[x[0] for x in PERFECT_SQUARES])
def test_bench_perfect_squares(benchmark: Callable[..., Any], _label: str,
                               n: int) -> None:
    """Benchmark perfect squares hitting the isqrt fast path directly.

    Args:
        benchmark: Pytest benchmark fixture.
        label: Description of the perfect square input.
        n: The perfect square integer.
    """
    benchmark(factorise, n, DEFAULT_CONFIG)


def test_bench_no_caching(benchmark: Callable[..., Any]) -> None:
    """Verify repeated factorisation attempts take the identical time (no memoisation).

    Args:
        benchmark: Pytest benchmark fixture.
    """

    def repeated() -> None:
        """Call factorise multiple times uniformly."""
        for _ in range(REPEATED_CALLS):
            factorise(CACHING_TEST_NUMBER, DEFAULT_CONFIG)

    benchmark(repeated)


@pytest.mark.parametrize("_label,n",
                         FIXED_SIZE_INPUTS,
                         ids=[x[0] for x in FIXED_SIZE_INPUTS])
def test_bench_fixed_bit_depths(benchmark: Callable[..., Any], _label: str,
                                n: int) -> None:
    """Benchmark performance across standard bit-depths (64, 96, 128).

    Args:
        benchmark: Pytest benchmark fixture.
        label: Bit-depth description.
        n: The semiprime to factorise.
    """
    # Use standard config with enough iterations for the 104-bit case
    config = FactoriserConfig(seed=42, max_iterations=5_000_000)
    benchmark(factorise, n, config)
