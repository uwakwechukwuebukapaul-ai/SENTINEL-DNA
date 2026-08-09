"""
Sentinel DNA IOC Enrichment Service
"""


from .ioc_classifier import IOCClassifier
from .reputation_engine import ReputationEngine
from .models import IOCResult



class IOCService:
    """
    IOC enrichment orchestration layer.
    """


    def __init__(
        self,
        classifier=None,
        reputation=None,
    ):


        self.classifier = (
            classifier
            or IOCClassifier()
        )


        self.reputation = (
            reputation
            or ReputationEngine()
        )



    def enrich(
        self,
        indicator: str,
    ) -> IOCResult:


        indicator_type = (
            self.classifier.classify(
                indicator
            )
        )


        reputation = (
            self.reputation.analyze(
                indicator,
                indicator_type,
            )
        )


        return IOCResult(

            indicator=indicator,

            indicator_type=indicator_type,

            risk=reputation["risk"],

            confidence=reputation["confidence"],

            metadata=reputation,

        )