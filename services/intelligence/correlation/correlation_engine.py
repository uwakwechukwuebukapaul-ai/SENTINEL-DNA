"""
Sentinel DNA Correlation Engine

Responsible for:
- IOC correlation
- Threat signal enrichment
- Attack pattern detection
- MITRE ATT&CK mapping
- Confidence scoring
- Knowledge graph reasoning
"""

from typing import Any

from .correlation_result import CorrelationResult
from .entity_graph import KnowledgeGraph



class CorrelationEngine:
    """
    Core threat intelligence correlation engine.
    """


    def __init__(
        self,
        graph: KnowledgeGraph | None = None,
    ):
        self.graph = graph or KnowledgeGraph()



    def correlate(
        self,
        signals: list[dict[str, Any]],
    ) -> CorrelationResult:
        """
        Correlate security signals.

        Example:

        [
            {
                "type": "email",
                "value": "phishing_email"
            },
            {
                "type": "domain",
                "value": "evil.com"
            }
        ]
        """


        entities = []

        relationships = []

        attack_pattern = None

        mitre = []

        confidence = 0.0

        risk = "unknown"



        signal_types = {
            signal.get("type")
            for signal in signals
        }



        #
        # Credential phishing detection
        #

        if (
            "email" in signal_types
            and "domain" in signal_types
        ):

            attack_pattern = (
                "credential_phishing"
            )

            mitre = [
                "T1566",
            ]

            confidence = 0.85

            risk = "high"



        #
        # Multiple indicators increase confidence
        #

        if len(signals) >= 4:

            confidence = max(
                confidence,
                0.90,
            )

            risk = "high"



        #
        # Knowledge graph lookup
        #

        for signal in signals:

            value = signal.get(
                "value",
                "",
            )


            entity_type = signal.get(
                "type",
                signal.get(
                    "entity_type"
                ),
            )


            entity = self.graph.find_entity(
                value,
                entity_type,
            )


            if entity:

                entities.append(
                    entity.value
                )


                confidence = max(
                    confidence,
                    1.0,
                )


                risk = "high"



                related = (
                    self.graph.get_relationships(
                        entity.id
                    )
                )


                relationships.extend(
                    related
                )


                for item in related:

                    entities.append(
                        item.value
                    )



        #
        # Determine match state
        #

        matched = bool(
            entities
            or attack_pattern
        )



        #
        # Normalize unknown IOC behavior
        #

        if not matched:

            risk = "unknown"

            confidence = 0.0



        return CorrelationResult(

            matched=matched,

            risk=risk,

            confidence=confidence,

            entities=list(
                dict.fromkeys(
                    entities
                )
            ),

            relationships=relationships,

            attack_pattern=attack_pattern,

            mitre=mitre,

            entity_type=None,

            value=None,

            metadata={
                "mitre": mitre,
            },

        )