"""
Sentinel DNA Reasoning Intelligence Layer.

Autonomous investigation reasoning components.
"""


from .reasoning_engine import (
    InvestigationReasoningEngine,
)
from .autonomous import AutonomousInvestigationEngine, DecisionRecord
from .routes import reasoning_api


# Backward-compatible public name
InvestigationReasoner = InvestigationReasoningEngine


__all__ = [

    "InvestigationReasoner",

    "InvestigationReasoningEngine",
    "AutonomousInvestigationEngine", "DecisionRecord", "reasoning_api",

]
