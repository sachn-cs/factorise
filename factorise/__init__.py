"""Public API for deterministic prime factorisation."""

from factorise.config import HybridConfig
from factorise.core import FactorisationError
from factorise.core import FactorisationResult
from factorise.core import FactoriserConfig
from factorise.core import PerfectPowerResult
from factorise.core import ensure_integer_input
from factorise.core import factorise
from factorise.core import find_perfect_power
from factorise.core import has_carmichael_property
from factorise.core import is_prime
from factorise.hybrid import HybridFactorisationEngine
from factorise.hybrid import hybrid_factorise
from factorise.pipeline import FactorisationPipeline
from factorise.pipeline import FactorStage
from factorise.pipeline import PipelineConfig
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus

__version__ = "0.3.4"
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
