"""
Sentinel DNA Intelligence Factory

Creates investigation intelligence pipelines.
"""

from __future__ import annotations

from .investigation_pipeline import (
    InvestigationPipeline,
)

from services.intelligence.evidence import (
    EvidenceCollector,
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


class IntelligenceFactory:
    """
    Enterprise intelligence dependency factory.
    """


    @staticmethod
    def create_pipeline():

        pipeline = InvestigationPipeline()


        pipeline.register_engine(
            "evidence",
            EvidenceCollector(),
        )


        pipeline.register_engine(
            "mitre",
            MitreEngine(),
        )


        pipeline.register_engine(
            "risk",
            RiskEngine(),
        )


        pipeline.register_engine(
            "recommendation",
            RecommendationEngine(),
        )


        return pipeline



    def build(self):

        return {

            "pipeline":
                self.create_pipeline()

        }