"""
Threat Intelligence Correlation Engine.

Connects IOC evidence with knowledge graph
relationships and produces intelligence.
"""


from .ioc_matcher import IOCMatcher
from .correlation_result import CorrelationResult



class ThreatCorrelator:


    def __init__(
        self,
        knowledge_graph
    ):

        self.graph = knowledge_graph

        self.matcher = IOCMatcher(
            knowledge_graph
        )



    def correlate(
        self,
        indicator: str,
        indicator_type: str | None = None,
    ):

        matches = self.matcher.match(
            indicator,
            indicator_type,
        )


        if not matches:

            return CorrelationResult(
                matched=False,
                risk="unknown",
                confidence=0.0,
            )



        entities = []

        techniques = []

        confidence = 0.5


        for entity in matches:

            entities.append(
                entity.value
            )


            relationships = (
                self.graph.get_relationships(
                    entity.id
                )
            )


            for relationship in relationships:

                target = (
                    relationship.target
                )


                linked = (
                    self.graph.get_entity(
                        target
                    )
                )


                if linked:

                    entities.append(
                        linked.value
                    )


                    if (
                        linked.entity_type
                        == "mitre"
                    ):

                        techniques.append(
                            linked.value
                        )



            confidence = 0.9



        return CorrelationResult(
            matched=True,
            risk="high",
            confidence=confidence,
            entities=list(
                set(entities)
            ),
            techniques=list(
                set(techniques)
            ),
        )