"""
Sentinel DNA Reasoning Intelligence Layer.

Autonomous investigation reasoning components.
"""


from .reasoning_engine import (
    InvestigationReasoningEngine,
)


# Backward-compatible public name
InvestigationReasoner = InvestigationReasoningEngine


__all__ = [

    "InvestigationReasoner",

    "InvestigationReasoningEngine",

]