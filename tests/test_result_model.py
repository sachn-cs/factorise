"""Tests for result-model edge behavior."""

from factorise.core import FactorisationResult


def test_result_expression_complex() -> None:
    res = FactorisationResult(
        original=-30,
        sign=-1,
        factors=[2, 3, 5],
        powers={
            2: 1,
            3: 1,
            5: 1
        },
        is_prime=False,
    )
    assert res.expression() == "-1 * 2 * 3 * 5"

    res2 = FactorisationResult(original=1,
                               sign=1,
                               factors=[],
                               powers={},
                               is_prime=False)
    assert res2.expression() == ""
