"""
Sentinel DNA Intelligence Correlation
"""

from .entity_graph import (
    Entity,
    Relationship,
    EntityGraph,
    KnowledgeGraph,
)


from .correlation_engine import (
    CorrelationEngine,
)


from .models import (
    CorrelationResult,
    CorrelationAnalysisResult,
    SecuritySignal, CorrelationRule, InvestigationTrigger,
)
from .engine import DeterministicCorrelationEngine
from .service import CorrelationService
from .repository import CorrelationRepository



class ThreatCorrelator:


    def __init__(
        self,
        graph,
    ):

        self.engine = CorrelationEngine(
            graph
        )



    def correlate(
        self,
        events=None,
        entities=None,
    ):


        if isinstance(events, str):

            signal = {

                "value": events,

                "type": entities,

            }


            return self.engine.correlate(
                [
                    signal
                ]
            )



        return self.engine.correlate(
            events or []
        )



__all__ = [

    "Entity",
    "Relationship",
    "EntityGraph",
    "KnowledgeGraph",

    "CorrelationEngine",

    "CorrelationResult",

    "ThreatCorrelator",
    "CorrelationAnalysisResult", "SecuritySignal", "CorrelationRule", "InvestigationTrigger", "DeterministicCorrelationEngine", "CorrelationService", "CorrelationRepository",

]
