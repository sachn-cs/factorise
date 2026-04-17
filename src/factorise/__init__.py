"""Public API for deterministic prime factorisation."""

from factorise.core import FactorisationError
from factorise.core import FactorisationResult
from factorise.core import FactoriserConfig
from factorise.core import factorise
from factorise.core import is_prime

__version__ = "0.1.0"
__all__ = [
    "FactorisationError", "FactorisationResult", "FactoriserConfig",
    "factorise", "is_prime"
]
