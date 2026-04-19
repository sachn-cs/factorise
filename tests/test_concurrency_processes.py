"""Deterministic process-safety validation for the factorise package."""

import multiprocessing

from source.core import FactoriserConfig
from source.core import factorise

# Use a known semiprime (83 * 97)
SEMIPRIME = 8051
EXPECTED_FACTORS = [83, 97]


def worker(n: int, config: FactoriserConfig) -> bool:
    """Independent worker function for process pool."""
    result = factorise(n, config)
    return result.factors == EXPECTED_FACTORS


def test_multiprocessing_factorisation_consistency() -> None:
    """Verify that the package logic is safe and correct across process boundaries.

    This ensures all domain objects (Config, Result) are correctly pickleable
    and that no process-specific artifacts break the algorithm logic.
    """
    config = FactoriserConfig(seed=123)
    num_processes = min(multiprocessing.cpu_count(), 4)
    tasks = [(SEMIPRIME, config)] * 10

    # Using 'with' handles pool cleanup and prevents resource leaks in tests
    with multiprocessing.Pool(processes=num_processes) as pool:
        results = [pool.apply(worker, t) for t in tasks]

    assert all(results), (
        "Multiprocessing produced inconsistent or incorrect results."
    )


def test_pickleability() -> None:
    """Explicitly verify that core objects are correctly pickleable.

    Required for any use case involving distributed task queues or process pools.
    """
    import pickle

    config = FactoriserConfig(seed=99)
    result = factorise(15, config)

    pickled_res = pickle.dumps(result)
    unpickled_res = pickle.loads(pickled_res)

    assert unpickled_res == result
    assert unpickled_res.expression() == result.expression()
