"""
Sentinel DNA Investigation Intelligence Layer.

Provides shared investigation state
and workflow context.
"""

from .context import InvestigationContext


__all__ = [
    "InvestigationContext",
]