"""Fast prime factorisation library using Miller-Rabin and Pollard's Rho."""

from .core import FactorisationResult, FactoriserConfig, factorise, is_prime

__version__ = "0.1.0"
__all__ = ["FactorisationResult", "FactoriserConfig", "factorise", "is_prime"]
