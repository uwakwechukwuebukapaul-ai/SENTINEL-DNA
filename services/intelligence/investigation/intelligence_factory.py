"""
Sentinel DNA Intelligence Factory

Builds and registers investigation
intelligence engines.

Central dependency composition layer.
"""

from __future__ import annotations

from typing import Any

from .investigation_pipeline import (
    InvestigationPipeline,
)

from services.intelligence.mitre import (
    MitreEngine,
)

from services.intelligence.risk import (
    RiskEngine,
)

from services.intelligence.recommendation import (
    RecommendationEngine,
)

from services.intelligence.evidence import (
    EvidenceCollector,
)


class IntelligenceFactory:
    """
    Creates production investigation pipelines.
    """

    @staticmethod
    def create_pipeline() -> InvestigationPipeline:
        """
        Build configured investigation pipeline.
        """

        engines: dict[str, Any] = {
            "evidence": EvidenceCollector(),
            "mitre": MitreEngine(),
            "risk": RiskEngine(),
            "recommendation": RecommendationEngine(),
        }

        return InvestigationPipeline(
            engines=engines
        )