"""
Sentinel DNA Decision Intelligence Package.
"""

from .service import DecisionIntelligenceService


DecisionIntelligenceEngine = DecisionIntelligenceService


__all__ = [
    "DecisionIntelligenceService",
    "DecisionIntelligenceEngine",
]