"""
Sentinel DNA Unified Investigation Service.

Enterprise orchestration layer connecting
investigation execution, decisions, and copilot.
"""

from ...models import (
    InvestigationServiceResult,
)


def __getattr__(name):
    """Load the implementation only when it is requested."""
    if name == "UnifiedInvestigationService":
        from importlib import import_module

        service = import_module(f"{__name__}.service")
        return service.UnifiedInvestigationService
    raise AttributeError(name)


__all__ = [
    "UnifiedInvestigationService",
    "InvestigationServiceResult",
]