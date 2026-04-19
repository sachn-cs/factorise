"""Property-based tests for algorithmic invariants using Hypothesis."""

import pytest

from source.core import factorise
from source.core import is_prime

hypothesis = pytest.importorskip("hypothesis")
st = pytest.importorskip("hypothesis.strategies")
given = hypothesis.given


@given(st.integers(min_value=-(10**16), max_value=10**16))
def test_factorisation_invariants(n: int) -> None:
    """Property-based tests to ensure factorisation invariants hold for all integers.

    Invariants tested:
      1. product(factors**powers) == abs(n)
      2. All factors must be prime
      3. is_prime(n) and factorise(n).is_prime agree (for n > 1)
    """
    res = factorise(n)

    # Note: absolute value comparison is needed since factorisation deals with magnitudes.
    # The result has a .sign attribute to represent the absolute negation.
    abs_n = abs(n)

    # Edge cases 0 and 1
    if abs_n in (0, 1):
        assert not res.is_prime
        assert not res.factors
        assert not res.powers
        return

    # Invariant 1: product(factors**powers) == abs_n
    product = 1
    for factor, power in res.powers.items():
        product *= factor**power
    assert product == abs_n, f"Product {product} != {abs_n}"

    # Invariant 2: All generated factors must be prime
    for factor in res.factors:
        assert is_prime(factor), f"Factor {factor} is not prime"

    # Invariant 3: is_prime(abs_n) and res.is_prime agree.
    assert is_prime(abs_n) == res.is_prime, f"is_prime mismatch for {abs_n}"
