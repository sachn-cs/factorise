"""Public API for deterministic prime factorisation."""

from source.core import FactorisationError
from source.core import FactorisationResult
from source.core import FactoriserConfig
from source.core import factorise
from source.core import is_prime

__version__ = "0.3.3"
__all__ = [
    "FactorisationError",
    "FactorisationResult",
    "FactoriserConfig",
    "factorise",
    "is_prime",
]
