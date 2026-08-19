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

    if name == "AnalystDecision":
        return import_module(".analyst_feedback", __name__).AnalystDecision

    if name == "AnalystFeedback":
        return import_module(".analyst_feedback", __name__).AnalystFeedback


    raise AttributeError(
        name
    )



__all__ = [

    "InvestigationContext",

    "InvestigationMemory",

    "InvestigationStateManager",

    "AnalystDecision",

    "AnalystFeedback",

]
