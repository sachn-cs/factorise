"""Memory benchmarks for the factorise package using tracemalloc.

Measures peak allocation for is_prime and factorise across input sizes.

Run with:
    pytest benchmarks/memory.py -v
    pytest benchmarks/memory.py -v -s   # see allocation details
"""

import sys
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass
from typing import ParamSpec
from typing import TypeVar

import pytest

from benchmarks.inputs import FACTORISE_LARGE
from benchmarks.inputs import FACTORISE_MEDIUM
from benchmarks.inputs import FACTORISE_SMALL
from benchmarks.inputs import IS_PRIME_LARGE
from benchmarks.inputs import IS_PRIME_MEDIUM
from benchmarks.inputs import IS_PRIME_SMALL
from benchmarks.inputs import SCALABILITY_INPUTS
from factorise.core import FactoriserConfig
from factorise.core import factorise
from factorise.core import is_prime

DEFAULT_CONFIG: FactoriserConfig = FactoriserConfig()

# Threshold: no single call should allocate more than 2 MB.
MAX_ALLOCATION_BYTES: int = 2 * 1024 * 1024
BATCH_MEMORY_LIMIT_BYTES: int = 4 * 1024 * 1024
RESULT_OBJECT_LIMIT_BYTES: int = 1024

BATCH_SIZES_FOR_MEMORY: list[int] = [10, 50, 100]
BATCH_INPUT: int = 123_456_789

ALL_IS_PRIME: tuple[tuple[str, int],
                    ...] = (IS_PRIME_SMALL + IS_PRIME_MEDIUM + IS_PRIME_LARGE)
ALL_FACTORISE: tuple[tuple[str, int],
                     ...] = (FACTORISE_SMALL + FACTORISE_MEDIUM +
                             FACTORISE_LARGE)

_R = TypeVar("_R")
_P = ParamSpec("_P")


@dataclass
class MemorySnapshot:
    """A record of peak memory allocated during a function execution.

    Attributes:
        peak_bytes: The maximum memory allocated in bytes.
        peak_kb: The maximum memory allocated in kilobytes.
    """

    peak_bytes: int
    peak_kb: float

    @classmethod
    def measure(cls, fn: Callable[_P, _R], *args: _P.args,
                **kwargs: _P.kwargs) -> "MemorySnapshot":
        """Execute a function and measure its peak memory allocation.

        Args:
            fn: The target callable to measure.
            *args: Positional arguments to forward to the callable.

        Returns:
            A MemorySnapshot instance mapping the observed peak allocation.
        """
        tracemalloc.start()
        try:
            fn(*args, **kwargs)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        return cls(peak_bytes=peak, peak_kb=peak / 1024)


@pytest.mark.parametrize("test_label,n",
                         ALL_IS_PRIME,
                         ids=[x[0] for x in ALL_IS_PRIME])
def test_memory_is_prime(test_label: str, n: int,
                         capsys: pytest.CaptureFixture[str]) -> None:
    """Verify is_prime operates strictly under the maximum memory threshold.

    Args:
        test_label: Description of the prime input.
        n: The integer to test.
        capsys: Pytest output capture fixture.

    Raises:
        AssertionError: If memory usage triggers the predefined cap.
    """
    snap = MemorySnapshot.measure(is_prime, n)
    with capsys.disabled():
        pass

    error_msg = f"is_prime({n}) exceeds {MAX_ALLOCATION_BYTES // 1024} KB limit"
    assert snap.peak_bytes < MAX_ALLOCATION_BYTES, error_msg


@pytest.mark.parametrize("label,n",
                         ALL_FACTORISE,
                         ids=[x[0] for x in ALL_FACTORISE])
def test_memory_factorise(label: str, n: int,
                          capsys: pytest.CaptureFixture[str]) -> None:
    """Verify factorise operates under the maximum memory threshold across scales.

    Args:
        label: Description of the input complexity.
        n: The integer to decompose.
        capsys: Pytest output capture fixture.

    Raises:
        AssertionError: If memory usage triggers the predefined cap.
    """
    snap = MemorySnapshot.measure(factorise, n, DEFAULT_CONFIG)
    with capsys.disabled():
        pass

    error_msg = (
        f"factorise({n}) exceeds {MAX_ALLOCATION_BYTES // 1024} KB limit")
    assert snap.peak_bytes < MAX_ALLOCATION_BYTES, error_msg


@pytest.mark.parametrize("label,n",
                         SCALABILITY_INPUTS,
                         ids=[x[0] for x in SCALABILITY_INPUTS])
def test_memory_scalability(label: str, n: int,
                            capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure algorithm scalability retains O(1) memory boundaries.

    Args:
        label: Description of the input magnitude.
        n: The mathematically scalable test number.
        capsys: Pytest output capture fixture.

    Raises:
        AssertionError: If memory usage grows boundlessly crossing the cap.
    """
    snap = MemorySnapshot.measure(factorise, n, DEFAULT_CONFIG)
    with capsys.disabled():
        pass
    assert snap.peak_bytes < MAX_ALLOCATION_BYTES


@pytest.mark.parametrize(
    "count",
    BATCH_SIZES_FOR_MEMORY,
    ids=[f"batch_{c}" for c in BATCH_SIZES_FOR_MEMORY],
)
def test_memory_no_growth_in_batch(count: int,
                                   capsys: pytest.CaptureFixture[str]) -> None:
    """Verify peak memory does not grow proportionally with successive iteration.

    Args:
        count: How many iterations to stress within a single evaluation context.
        capsys: Pytest output capture fixture.

    Raises:
        AssertionError: If batching reveals proportional caching or leakage.
    """

    def run_batch() -> None:
        """Evaluate factorise iteratively in isolation."""
        for _ in range(count):
            factorise(BATCH_INPUT, DEFAULT_CONFIG)

    snap = MemorySnapshot.measure(run_batch)
    with capsys.disabled():
        pass

    error_msg = (
        f"Batch of {count} allocated {snap.peak_kb:.1f} KB (potential leak)")
    assert snap.peak_bytes < BATCH_MEMORY_LIMIT_BYTES, error_msg


def test_memory_result_object_size(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify the FactorisationResult dataclass instance remains lightweight.

    Args:
        capsys: Pytest output capture fixture.

    Raises:
        AssertionError: If the result struct violates baseline object expectations.
    """
    result = factorise(BATCH_INPUT, DEFAULT_CONFIG)
    size = sys.getsizeof(result)

    with capsys.disabled():
        pass

    error_msg = f"FactorisationResult is unexpectedly large: {size} bytes"
    assert size < RESULT_OBJECT_LIMIT_BYTES, error_msg
