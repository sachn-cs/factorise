"""Public API for deterministic prime factorisation.

This module re-exports the principal classes, functions, and exceptions
needed to factorise integers using the library. Consumers should import
from this top-level package rather than from submodules directly.

Example:
    >>> from factorise import factorise, FactorisationResult
    >>> result = factorise(12345)
    >>> result.factors
    [3, 5, 823]

"""

from factorise.config import AlgorithmConfig
from factorise.config import FactoriserConfig
from factorise.config import HybridConfig
from factorise.config import HybridFactorisationState
from factorise.core import FactorisationError
from factorise.core import FactorisationResult
from factorise.core import PerfectPowerResult
from factorise.core import ensure_integer_input
from factorise.core import factorise
from factorise.core import find_perfect_power
from factorise.core import has_carmichael_property
from factorise.core import is_prime
from factorise.hybrid import HybridFactorisationEngine
from factorise.hybrid import hybrid_factorise
from factorise.pipeline import FactorStage
from factorise.pipeline import StageResult
from factorise.pipeline import StageStatus

__version__ = "0.5.2"
__all__ = [
    "AlgorithmConfig",
    "FactorStage",
    "FactorisationError",
    "FactorisationResult",
    "FactoriserConfig",
    "HybridConfig",
    "HybridFactorisationEngine",
    "HybridFactorisationState",
    "PerfectPowerResult",
    "StageResult",
    "StageStatus",
    "ensure_integer_input",
    "factorise",
    "find_perfect_power",
    "has_carmichael_property",
    "hybrid_factorise",
    "is_prime",
]
