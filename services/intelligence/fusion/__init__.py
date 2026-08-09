"""
Sentinel DNA Intelligence Fusion Layer

Public exports.
"""

from services.intelligence.fusion.threat_fusion_engine import (
    ThreatFusionEngine,
)


# Compatibility alias
FusionEngine = ThreatFusionEngine


from services.intelligence.fusion.fusion_result import (
    FusionResult,
)


from services.intelligence.fusion.intelligence_pipeline import (
    IntelligencePipeline,
)


__all__ = [

    "FusionEngine",

    "ThreatFusionEngine",

    "FusionResult",

    "IntelligencePipeline",

]