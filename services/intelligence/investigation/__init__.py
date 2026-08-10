"""
Sentinel DNA Investigation Intelligence Layer.

Provides investigation context,
memory management and lifecycle state.
"""

from importlib import import_module


def __getattr__(name: str):

    if name == "InvestigationContext":

        return import_module(
            ".context",
            __name__,
        ).InvestigationContext


    if name == "InvestigationMemory":

        return import_module(
            ".memory",
            __name__,
        ).InvestigationMemory


    if name == "InvestigationStateManager":

        return import_module(
            ".state_manager",
            __name__,
        ).InvestigationStateManager


    raise AttributeError(
        name
    )



__all__ = [

    "InvestigationContext",

    "InvestigationMemory",

    "InvestigationStateManager",

]