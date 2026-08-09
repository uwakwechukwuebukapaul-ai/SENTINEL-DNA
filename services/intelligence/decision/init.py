"""
Sentinel DNA Decision Intelligence Layer

Transforms intelligence outputs into
SOC analyst decisions.
"""

from importlib import import_module


def __getattr__(name: str):
    """Load decision implementations lazily."""
    if name == "RiskDecision":
        return getattr(import_module(f"{__name__}.risk_decision"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "RiskDecision",
]