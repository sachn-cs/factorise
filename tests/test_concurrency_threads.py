"""Deterministic thread-safety validation for the factorise package."""

import concurrent.futures

from factorise.config import FactoriserConfig
from factorise.core import factorise

# Use a large 92-bit semiprime to stress-test parallel logic (P61 * P31)
SEMIPRIME = 2305843009213693951 * 2147483647
EXPECTED_FACTORS = [2147483647, 2305843009213693951]
NUM_THREADS = 8
REPETITIONS = 5


def test_multithreaded_factorisation_consistency() -> None:
    """Verify that concurrent factorisation of the same input is deterministic.

    This ensures that global state (like random if unseeded, or shared objects)
    does not cause race conditions or data corruption in the result models.
    """
    # Use deterministic config to ensure bit-identical results
    config = FactoriserConfig(seed=42)

    # Pre-compute baseline
    baseline = factorise(SEMIPRIME, config)
    assert baseline.factors == EXPECTED_FACTORS

    def worker(_: int) -> bool:
        result = factorise(SEMIPRIME, config)
        # Verify full object equality, not just factors
        return result == baseline

    with concurrent.futures.ThreadPoolExecutor(
            max_workers=NUM_THREADS) as executor:
        # Run many repetitions to increase contention probability
        futures = [
            executor.submit(worker, i) for i in range(NUM_THREADS * REPETITIONS)
        ]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert all(results), (
        "At least one thread produced an inconsistent result under contention.")


def test_mixed_threaded_workload() -> None:
    """Verify thread-safety when different inputs are processed concurrently."""
    inputs = list(range(1001, 1001 + NUM_THREADS))

    def worker(n: int) -> int:
        res = factorise(n)
        return res.original

    with concurrent.futures.ThreadPoolExecutor(
            max_workers=NUM_THREADS) as executor:
        results = list(executor.map(worker, inputs))

    assert results == inputs, (
        "Data corruption or input leakage detected in concurrent execution.")
