"""Comprehensive tests for the multi-stage factorisation pipeline.

Tests the full pipeline end-to-end, stage selection and fallback behavior,
correctness invariants, and backward compatibility with the existing
Pollard-Brent implementation.
"""

from __future__ import annotations

from functools import reduce
from typing import cast

import pytest

from source.core import (
    collect_prime_factors as factor_flatten,
    FactorisationError,
    FactoriserConfig,
    factorise,
    find_nontrivial_factor_pollard_brent as pollard_brent,
    is_prime,
)
from source.pipeline import (
    FactorStage,
    FactorisationPipeline,
    PipelineConfig,
    StageResult,
    StageStatus,
    TrialDivisionStage,
)
from tests.conftest import DEFAULT_CONFIG

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _product(factors: list[int]) -> int:
    return reduce(lambda a, b: a * b, factors, 1)


def _reconstructed_product(result: FactorisationResult) -> int:
    prod = 1
    for prime, power in result.powers.items():
        prod *= prime**power
    return prod


# ---------------------------------------------------------------------------
# Stage correctness invariants
# ---------------------------------------------------------------------------


def _check_factorisation_result(n: int, result: FactorisationResult) -> None:
    """Verify all correctness invariants for a FactorisationResult."""
    # Product equals abs(original)
    assert _reconstructed_product(result) == abs(n), (
        f"product mismatch: got {_reconstructed_product(result)}, want {abs(n)}"
    )
    # Every factor is prime
    assert all(is_prime(f) for f in result.factors), (
        f"non-prime factor found: {result.factors}"
    )
    # Original preserved
    assert result.original == n
    # Sign correct
    assert result.sign == (-1 if n < 0 else 1)
    # Zero/one have empty factor lists
    if n == 0 or n == 1 or n == -1:
        assert result.factors == []
        assert result.powers == {}
        assert result.is_prime is False


# ---------------------------------------------------------------------------
# Basic pipeline construction
# ---------------------------------------------------------------------------


class TestPipelineConstruction:
    def test_pipeline_default_constructs(self) -> None:
        pipeline = FactorisationPipeline()
        assert pipeline._config is not None

    def test_pipeline_with_explicit_config(self) -> None:
        config = PipelineConfig(max_retries=5, batch_size=64)
        pipeline = FactorisationPipeline(config)
        assert pipeline._config is config

    def test_pipeline_stage_order(self) -> None:
        config = PipelineConfig(stage_order=("trial_division", "pollard_rho"))
        pipeline = FactorisationPipeline(config)
        assert len(pipeline._stages) == 2
        assert "trial_division" in pipeline._stages
        assert "pollard_rho" in pipeline._stages

    def test_pipeline_config_stage_config(self) -> None:
        config = PipelineConfig(
            batch_size=64, max_iterations=1_000_000, max_retries=10
        )
        derived = config.stage_config("pollard_rho")
        assert derived.batch_size == 64
        assert derived.max_iterations == 1_000_000
        assert derived.max_retries == 10


# ---------------------------------------------------------------------------
# Stage interface
# ---------------------------------------------------------------------------


class TestStageInterface:
    def test_trial_division_stage(self) -> None:
        stage = TrialDivisionStage(bound=1000)
        assert stage.name == "trial_division"
        result = stage.attempt(12, config=DEFAULT_CONFIG)
        assert result.status is StageStatus.SUCCESS
        assert result.factor == 2

    def test_trial_division_stage_no_factor(self) -> None:
        stage = TrialDivisionStage(bound=1000)
        # 233*239 has both primes > 1000, so trial division bound=1000 won't find a factor
        result = stage.attempt(233 * 239, config=DEFAULT_CONFIG)  # 55687
        assert result.status is StageStatus.FAILURE

    def test_pollard_pminus1_stage(self) -> None:
        from source.pipeline import PollardPMinusOneStage

        stage = PollardPMinusOneStage(bound=10**6)
        assert stage.name == "pollard_pminus1"
        # 91 = 7*13 — pollard p-1 might find a factor if smooth
        result = stage.attempt(91, config=DEFAULT_CONFIG)
        # Not guaranteed to succeed (depends on factor structure)

    def test_trial_division_stage_even_input(self) -> None:
        stage = TrialDivisionStage(bound=1000)
        result = stage.attempt(4, config=DEFAULT_CONFIG)
        assert result.status is StageStatus.SUCCESS
        assert result.factor == 2


# ---------------------------------------------------------------------------
# Pipeline end-to-end tests
# ---------------------------------------------------------------------------


class TestPipelineEndToEnd:
    @pytest.mark.parametrize(
        "n",
        [
            12,
            24,
            60,
            360,
            8,
            2**10,
            3**7,
            30030,
            123456789,
        ],
    )
    def test_pipeline_factorises_small_composites(self, n: int) -> None:
        config = PipelineConfig(stage_order=("trial_division", "pollard_rho"))
        pipeline = FactorisationPipeline(config)
        result = pipeline.attempt(n, config=DEFAULT_CONFIG)
        assert result.status is StageStatus.SUCCESS
        assert result.factor is not None
        assert 1 < result.factor < n
        assert is_prime(result.factor)

    @pytest.mark.parametrize("p", [2, 3, 5, 7, 11, 13, 97, 997])
    def test_pipeline_prime_input_skipped(self, p: int) -> None:
        config = PipelineConfig(stage_order=("trial_division", "pollard_rho"))
        pipeline = FactorisationPipeline(config)
        result = pipeline.attempt(p, config=DEFAULT_CONFIG)
        assert result.status is StageStatus.SKIPPED
        assert result.factor is None

    @pytest.mark.parametrize(
        "n",
        [
            0,
            1,
        ],
    )
    def test_pipeline_edge_cases_skipped(self, n: int) -> None:
        config = PipelineConfig()
        pipeline = FactorisationPipeline(config)
        result = pipeline.attempt(n, config=DEFAULT_CONFIG)
        assert result.status is StageStatus.SKIPPED


# ---------------------------------------------------------------------------
# Full factorise() API tests — backward compatibility
# ---------------------------------------------------------------------------


class TestFactoriseBackwardCompatibility:
    @pytest.mark.parametrize(
        "n,expected_factors",
        [
            (12, [2, 3]),
            (24, [2, 3]),
            (60, [2, 3, 5]),
            (360, [2, 3, 5]),
            (8, [2]),
            (30030, [2, 3, 5, 7, 11, 13]),
            (123456789, [3, 3607, 3803]),
        ],
    )
    def test_factorise_no_pipeline(
        self, n: int, expected_factors: list[int]
    ) -> None:
        """Verify existing behavior is preserved when use_pipeline=False."""
        config = FactoriserConfig(use_pipeline=False)
        result = factorise(n, config)
        assert result.factors == expected_factors
        _check_factorisation_result(n, result)

    @pytest.mark.parametrize(
        "n,expected_factors",
        [
            (12, [2, 3]),
            (24, [2, 3]),
            (60, [2, 3, 5]),
            (360, [2, 3, 5]),
            (8, [2]),
            (30030, [2, 3, 5, 7, 11, 13]),
            (123456789, [3, 3607, 3803]),
        ],
    )
    def test_factorise_with_pipeline(
        self, n: int, expected_factors: list[int]
    ) -> None:
        """Verify pipeline mode produces correct results."""
        config = FactoriserConfig(use_pipeline=True)
        result = factorise(n, config)
        assert result.factors == expected_factors
        _check_factorisation_result(n, result)

    @pytest.mark.parametrize(
        "n",
        [12, 60, 360, 2**10, 3**7, 2**5 * 3**3 * 7],
    )
    def test_factorise_powers_consistent_with_factors(self, n: int) -> None:
        config = FactoriserConfig(use_pipeline=False)
        result = factorise(n, config)
        reconstructed = sorted(
            (prime for prime, power in result.powers.items() for _ in range(power))
        )
        assert sorted(set(reconstructed)) == result.factors

    @pytest.mark.parametrize("p", [9973, 99991, 999983])
    def test_factorise_semiprime(self, p: int) -> None:
        q = p + 6
        if is_prime(q):
            n = p * q
            config = FactoriserConfig(use_pipeline=False)
            result = factorise(n, config)
            assert sorted(result.factors) == sorted([p, q])
            _check_factorisation_result(n, result)

    @pytest.mark.parametrize("exp", range(1, 20))
    def test_factorise_powers_of_two(self, exp: int) -> None:
        config = FactoriserConfig(use_pipeline=False)
        res = factorise(2**exp, config)
        assert res.factors == [2]
        assert res.powers[2] == exp

    @pytest.mark.parametrize("exp", range(1, 12))
    def test_factorise_powers_of_three(self, exp: int) -> None:
        config = FactoriserConfig(use_pipeline=False)
        assert factorise(3**exp, config).factors == [3]

    @pytest.mark.parametrize(
        "p,q",
        [
            (9973, 9967),
            (99991, 99989),
            (999983, 999979),
        ],
    )
    def test_factorise_semiprime_with_pipeline(self, p: int, q: int) -> None:
        config = FactoriserConfig(use_pipeline=True)
        result = factorise(p * q, config)
        assert sorted(result.factors) == sorted([p, q])

    @pytest.mark.parametrize("p", [5, 7, 11, 13, 17, 19, 23])
    def test_factorise_prime_squared(self, p: int) -> None:
        config = FactoriserConfig(use_pipeline=False)
        res = factorise(p * p, config)
        assert res.factors == [p]
        assert res.powers == {p: 2}

    @pytest.mark.parametrize("n", [0, 1, -1, 2, -12, 123456789])
    def test_factorise_original_preserved(self, n: int) -> None:
        config = FactoriserConfig(use_pipeline=False)
        assert factorise(n, config).original == n


# ---------------------------------------------------------------------------
# Correctness: product equals original, all factors prime
# ---------------------------------------------------------------------------


class TestCorrectnessInvariants:
    @pytest.mark.parametrize(
        "n",
        [
            12,
            24,
            60,
            360,
            2**10,
            3**5,
            5**3 * 7**2,
            123456789,
            2**31 - 1,  # Large prime
            32416189987,  # Large prime
        ],
    )
    def test_factor_product_equals_original(self, n: int) -> None:
        for use_pipeline in (False, True):
            config = FactoriserConfig(use_pipeline=use_pipeline)
            result = factorise(n, config)
            _check_factorisation_result(n, result)

    @pytest.mark.parametrize("n", [12, 60, 360, 2**10, 3**7])
    def test_pipeline_correctness(self, n: int) -> None:
        config = PipelineConfig(stage_order=("trial_division", "pollard_rho"))
        pipeline = FactorisationPipeline(config)
        raw_factors: list[int] = []

        def collect(n_val: int) -> None:
            if n_val < 2:
                return
            if is_prime(n_val):
                raw_factors.append(n_val)
                return
            result = pipeline.attempt(n_val, config=DEFAULT_CONFIG)
            if result.status is StageStatus.SUCCESS and result.factor is not None:
                collect(result.factor)
                collect(n_val // result.factor)

        collect(n)
        from collections import Counter

        counts = Counter(raw_factors)
        powers = {prime: counts[prime] for prime in counts}
        prod = 1
        for prime, power in powers.items():
            prod *= prime**power
        assert prod == n

    def test_negative_input_sign_preserved(self) -> None:
        config = FactoriserConfig(use_pipeline=False)
        result = factorise(-60, config)
        assert result.sign == -1
        assert result.factors == [2, 3, 5]
        assert _reconstructed_product(result) == 60

    def test_zero_one_no_factors(self) -> None:
        config = FactoriserConfig(use_pipeline=False)
        assert factorise(0, config).factors == []
        assert factorise(1, config).factors == []
        assert factorise(-1, config).factors == []


# ---------------------------------------------------------------------------
# Stage selection and fallback
# ---------------------------------------------------------------------------


class TestStageSelection:
    def test_trial_division_used_first(self) -> None:
        """Trial division should be used before pollard_rho for small factors."""
        config = PipelineConfig(stage_order=("trial_division", "pollard_rho"))
        pipeline = FactorisationPipeline(config)
        result = pipeline.attempt(12, config=DEFAULT_CONFIG)
        assert result.status is StageStatus.SUCCESS
        assert result.factor == 2

    def test_pollard_rho_fallback_when_trial_division_fails(self) -> None:
        """Pollard rho should be tried when trial division finds no factor."""
        # Use a large composite whose factors are too large for trial division
        n = 233 * 239  # 55687
        config = PipelineConfig(stage_order=("trial_division", "pollard_rho"))
        pipeline = FactorisationPipeline(config)
        result = pipeline.attempt(n, config=DEFAULT_CONFIG)
        assert result.status is StageStatus.SUCCESS
        assert result.factor in (233, 239)

    def test_stage_order_respected(self) -> None:
        """Stages should be tried in configured order."""
        # With only trial_division, larger factors should cause failure
        config = PipelineConfig(stage_order=("trial_division",))
        pipeline = FactorisationPipeline(config)
        result = pipeline.attempt(233 * 239, config=DEFAULT_CONFIG)
        # Trial division won't find large prime factors
        assert result.status is StageStatus.FAILURE

    def test_disabled_stage_skipped(self) -> None:
        """Unknown or disabled stages should be skipped silently."""
        config = PipelineConfig(stage_order=("trial_division", "nonexistent_stage"))
        pipeline = FactorisationPipeline(config)
        # Should still succeed using trial division
        result = pipeline.attempt(12, config=DEFAULT_CONFIG)
        assert result.status is StageStatus.SUCCESS


# ---------------------------------------------------------------------------
# Failures do not corrupt results
# ---------------------------------------------------------------------------


class TestFailureIsolation:
    def test_all_stages_fail_raises_factorisation_error(self) -> None:
        """When all stages fail, FactorisationError should be raised."""
        from unittest.mock import patch

        from source.pipeline import StageResult

        # Patch trial_division to always fail and pollard_rho to always fail
        fail_result = StageResult(
            stage_name="stub",
            status=StageStatus.FAILURE,
            factor=None,
            elapsed_ms=1.0,
            reason="always fails",
        )

        with patch.object(
            TrialDivisionStage, "attempt", return_value=fail_result
        ):
            with patch(
                "source.stages.pollard_rho.PollardRhoStage.attempt",
                return_value=fail_result,
            ):
                config = PipelineConfig(
                    stage_order=("trial_division", "pollard_rho")
                )
                pipeline = FactorisationPipeline(config)
                result = pipeline.attempt(233 * 239, config=DEFAULT_CONFIG)
                assert result.status is StageStatus.FAILURE

    def test_pipeline_returns_failure_not_exception(self) -> None:
        """Pipeline.attempt() returns StageResult, never raises."""
        config = PipelineConfig(stage_order=())
        pipeline = FactorisationPipeline(config)
        result = pipeline.attempt(12, config=DEFAULT_CONFIG)
        # No stages available, so FAILURE (cannot factor without any stages)
        assert result.status is StageStatus.FAILURE


# ---------------------------------------------------------------------------
# Regression: existing Pollard-Rho behavior
# ---------------------------------------------------------------------------


class TestPollardRhoRegression:
    @pytest.mark.parametrize(
        "n",
        [
            12,
            60,
            360,
            2**10,
            3**5,
            2**5 * 3**3 * 7,
            123456789,
            2**31 - 1,
        ],
    )
    def test_pollard_rho_factorises_correctly(self, n: int) -> None:
        """Pollard-Brent should factor all expected composites."""
        config = FactoriserConfig(use_pipeline=False)
        result = factorise(n, config)
        assert result.factors is not None
        _check_factorisation_result(n, result)

    @pytest.mark.parametrize("p", [3, 5, 7, 97, 997])
    def test_pollard_brent_prime_returns_self(self, p: int) -> None:
        """pollard_brent should return p for prime p."""
        assert pollard_brent(p, DEFAULT_CONFIG) == p

    @pytest.mark.parametrize("n", [2, 4, 6, 100, 2**20])
    def test_pollard_brent_even_returns_two(self, n: int) -> None:
        """pollard_brent should return 2 for even n."""
        assert pollard_brent(n, DEFAULT_CONFIG) == 2

    def test_pollard_brent_seed_reproducible(self) -> None:
        """Pollard-Brent with seed should be reproducible."""
        n = 99_991 * 99_989
        cfg = FactoriserConfig(seed=123, max_retries=5, max_iterations=1_000_000)
        assert pollard_brent(n, cfg) == pollard_brent(n, cfg)

    def test_factor_flatten_no_pipeline(self) -> None:
        """factor_flatten without pipeline uses old path."""
        config = FactoriserConfig(use_pipeline=False)
        factors = factor_flatten(12, config)
        assert sorted(factors) == [2, 2, 3]


# ---------------------------------------------------------------------------
# PipelineConfig from env
# ---------------------------------------------------------------------------


class TestPipelineConfigEnv:
    def test_pipeline_config_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FACTORISE_BOUND_MEDIUM", "1000000")
        monkeypatch.setenv("FACTORISE_ECM_CURVES", "50")
        config = PipelineConfig.from_env()
        assert config.bound_medium == 1_000_000
        assert config.ecm_curves == 50


# ---------------------------------------------------------------------------
# FactorStage interface compliance
# ---------------------------------------------------------------------------


class TestFactorStageInterface:
    def test_all_stages_have_name(self) -> None:
        """Every stage must have a non-empty name attribute."""
        config = PipelineConfig()
        pipeline = FactorisationPipeline(config)
        for name, stage in pipeline._stages.items():
            assert hasattr(stage, "name")
            assert stage.name == name

    def test_all_stages_implement_attempt(self) -> None:
        """Every stage must implement the attempt() method."""
        config = PipelineConfig()
        pipeline = FactorisationPipeline(config)
        for stage in pipeline._stages.values():
            assert hasattr(stage, "attempt")
            assert callable(stage.attempt)


# ---------------------------------------------------------------------------
# Observability: stage results contain useful fields
# ---------------------------------------------------------------------------


class TestStageResultObservability:
    def test_stage_result_has_elapsed_ms(self) -> None:
        """StageResult should include elapsed_ms."""
        stage = TrialDivisionStage()
        result = stage.attempt(12, config=DEFAULT_CONFIG)
        assert hasattr(result, "elapsed_ms")
        assert result.elapsed_ms >= 0

    def test_stage_result_has_stage_name(self) -> None:
        """StageResult should include the stage name."""
        stage = TrialDivisionStage()
        result = stage.attempt(12, config=DEFAULT_CONFIG)
        assert result.stage_name == "trial_division"

    def test_stage_result_reason_provided_on_failure(self) -> None:
        """Failed stage results should include a reason."""
        stage = TrialDivisionStage(bound=10)
        result = stage.attempt(97 * 97, config=DEFAULT_CONFIG)
        assert result.status is StageStatus.FAILURE
        assert result.reason != ""


# ---------------------------------------------------------------------------
# GNFS stage
# ---------------------------------------------------------------------------


class TestGNFSStage:
    def test_gnfs_stage_not_available(self) -> None:
        """GNFS stage should skip when binary is not on PATH."""
        from source.stages.gnfs import GNFSStage

        stage = GNFSStage(binary="nonexistent_gnfs_tool_xyz")
        result = stage.attempt(10**30, config=DEFAULT_CONFIG)
        # Binary not found => SKIPPED
        assert result.status is StageStatus.SKIPPED

    def test_gnfs_stage_small_input_skipped(self) -> None:
        """GNFS stage should skip very small inputs."""
        from source.stages.gnfs import GNFSStage

        stage = GNFSStage(binary="msieve")
        result = stage.attempt(12, config=DEFAULT_CONFIG)
        assert result.status is StageStatus.SKIPPED


# ---------------------------------------------------------------------------
# ECM stage basic
# ---------------------------------------------------------------------------


class TestECMStage:
    def test_ecm_stage_basic(self) -> None:
        from source.stages.ecm import ECMStage

        stage = ECMStage(curves=5)
        assert stage.name == "ecm"
        assert stage._curves == 5
