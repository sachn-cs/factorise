"""Public API for deterministic prime factorisation."""

from source.config import HybridConfig
from source.core import ensure_integer_input
from source.core import FactorisationError
from source.core import FactorisationResult
from source.core import FactoriserConfig
from source.core import PerfectPowerResult
from source.core import find_perfect_power
from source.core import factorise
from source.core import has_carmichael_property
from source.core import is_prime
from source.hybrid import HybridFactorisationEngine
from source.hybrid import hybrid_factorise
from source.pipeline import FactorisationPipeline
from source.pipeline import FactorStage
from source.pipeline import PipelineConfig
from source.pipeline import StageResult
from source.pipeline import StageStatus

__version__ = "0.3.3"
__all__ = [
    "ensure_integer_input",
    "FactorisationError",
    "FactorisationResult",
    "FactoriserConfig",
    "PerfectPowerResult",
    "find_perfect_power",
    "factorise",
    "has_carmichael_property",
    "is_prime",
    "HybridConfig",
    "HybridFactorisationEngine",
    "hybrid_factorise",
    "FactorisationPipeline",
    "FactorStage",
    "PipelineConfig",
    "StageResult",
    "StageStatus",
]
