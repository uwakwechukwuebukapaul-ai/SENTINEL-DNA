"""
Sentinel DNA Threat Correlator

High-level threat correlation layer.

Responsibilities:

- IOC relationship analysis
- Threat entity matching
- Malware / actor correlation
- Confidence calculation
- Relationship expansion
- CorrelationResult normalization
"""

from __future__ import annotations

from typing import Any

from .correlation_result import CorrelationResult
from .entity_graph import KnowledgeGraph


class ThreatCorrelator:
    """
    Threat intelligence correlation service.
    """


    def __init__(
        self,
        graph: KnowledgeGraph | None = None,
    ) -> None:

        self.graph = graph or KnowledgeGraph()



    def correlate(
        self,
        indicators: list[dict[str, Any]],
    ) -> CorrelationResult:
        """
        Correlate threat indicators.

        Example:

        [
            {
                "type": "domain",
                "value": "malicious.com"
            }
        ]
        """

        entities = []

        relationships = []

        confidence = 0.0

        risk = "unknown"

        matched = False

        attack_story = None



        for indicator in indicators:

            value = indicator.get(
                "value"
            )

            entity_type = indicator.get(
                "type",
                indicator.get(
                    "entity_type"
                ),
            )


            entity = self.graph.find_entity(
                value,
                entity_type,
            )


            if not entity:
                continue


            matched = True


            entities.append(
                entity.value
            )


            confidence = max(
                confidence,
                0.80,
            )


            risk = "high"



            related_entities = (
                self.graph.get_relationship_objects(
                    entity.id
                )
                if hasattr(
                    self.graph,
                    "get_relationship_objects",
                )
                else []
            )


            for relation in related_entities:

                relationships.append(
                    relation
                )


                if hasattr(
                    relation,
                    "value",
                ):

                    entities.append(
                        relation.value
                    )



        #
        # IOC relationship reasoning
        #

        if relationships:

            confidence = max(
                confidence,
                0.90,
            )


            attack_story = (
                "Indicator linked to known "
                "threat intelligence entities."
            )



        #
        # Deduplicate entities
        #

        entities = list(
            dict.fromkeys(
                entities
            )
        )



        #
        # Unknown indicator handling
        #

        if not matched:

            return CorrelationResult(

                matched=False,

                risk="unknown",

                confidence=0.0,

                entities=[],

                relationships=[],

                attack_story=None,

                metadata={
                    "reason":
                        "No matching threat intelligence found"
                },

            )



        return CorrelationResult(

            matched=True,

            risk=risk,

            confidence=confidence,

            entities=entities,

            relationships=relationships,

            attack_story=attack_story,

            metadata={

                "entity_count":
                    len(entities),

                "relationship_count":
                    len(relationships),

            },

        )



    def correlate_ioc(
        self,
        ioc: dict[str, Any],
    ) -> CorrelationResult:
        """
        Compatibility wrapper.
        """

        return self.correlate(
            [
                ioc
            ]
        )