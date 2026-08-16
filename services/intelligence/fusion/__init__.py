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

from services.intelligence.fusion.provider_neutral import (
    FreshnessPolicy,
    FusionResult as ProviderNeutralFusionResult,
    ProviderNeutralFusionEngine,
)


__all__ = [

    "FusionEngine",

    "ThreatFusionEngine",

    "FusionResult",

    "IntelligencePipeline",

    "FreshnessPolicy",

    "ProviderNeutralFusionResult",

    "ProviderNeutralFusionEngine",

]
