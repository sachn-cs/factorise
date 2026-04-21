"""Public API for deterministic prime factorisation."""

from source.core import FactorisationError
from source.core import FactorisationResult
from source.core import FactoriserConfig
from source.core import factorise
from source.core import is_prime
from source.pipeline import FactorisationPipeline
from source.pipeline import FactorStage
from source.pipeline import PipelineConfig
from source.pipeline import StageResult
from source.pipeline import StageStatus

__version__ = "0.3.3"
__all__ = [
    "FactorisationError",
    "FactorisationResult",
    "FactoriserConfig",
    "factorise",
    "is_prime",
    "FactorisationPipeline",
    "FactorStage",
    "PipelineConfig",
    "StageResult",
    "StageStatus",
]
