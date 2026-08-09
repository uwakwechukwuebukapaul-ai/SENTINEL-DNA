"""
Sentinel DNA Correlation Engine

Core threat intelligence correlation layer.

Responsibilities:

- IOC correlation
- Threat signal enrichment
- Attack pattern detection
- MITRE ATT&CK mapping
- Knowledge graph reasoning
- Confidence scoring
- Relationship traversal
"""

from __future__ import annotations

from typing import Any

from .correlation_result import CorrelationResult
from .entity_graph import KnowledgeGraph


class CorrelationEngine:
    """
    Enterprise correlation engine.
    """


    def __init__(
        self,
        graph: KnowledgeGraph | None = None,
    ):
        self.graph = graph or KnowledgeGraph()



    def correlate(
        self,
        signals: list[dict[str, Any]] | None = None,
        *,
        case_id: str | None = None,
        indicators: list[dict[str, Any]] | None = None,
        techniques: list[dict[str, Any]] | None = None,
        reasoning: dict[str, Any] | None = None,
    ) -> CorrelationResult:
        """
        Correlate threat intelligence signals.

        Supports:

        correlate(signals)

        and compatibility:

        correlate(
            case_id="CASE",
            indicators=[],
            techniques=[],
            reasoning={}
        )
        """


        signals = signals or []


        if indicators:

            signals.extend(
                [
                    {
                        "type":
                            item.get(
                                "type",
                                "ioc",
                            ),

                        "value":
                            item.get(
                                "value",
                                item.get(
                                    "ioc"
                                ),
                            ),
                    }

                    for item in indicators
                ]
            )


        if techniques:

            signals.extend(
                [
                    {
                        "type":
                            "technique",

                        "value":
                            item.get(
                                "value",
                                item.get(
                                    "technique"
                                ),
                            ),
                    }

                    for item in techniques
                ]
            )



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



        values = [
            signal.get(
                "value"
            )
            for signal in signals
            if signal.get("value")
        ]



        #
        # Phishing detection
        #

        if (
            "email" in signal_types
            and "domain" in signal_types
        ):

            attack_pattern = (
                "credential_phishing"
            )

            mitre = [
                "T1566"
            ]

            confidence = 0.85

            risk = "high"



        #
        # Threat artifact detection
        #

        if (
            "ioc" in signal_types
            or "domain" in signal_types
            or "hash" in signal_types
            or "ip" in signal_types
        ):

            confidence = max(
                confidence,
                0.60,
            )



        if len(signals) >= 4:

            confidence = max(
                confidence,
                0.90,
            )

            risk = "high"



        #
        # Knowledge graph correlation
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


            if not entity:

                continue



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


                nested = (
                    self.graph.get_relationships(
                        item.id
                    )
                )


                relationships.extend(
                    nested
                )


                for child in nested:

                    entities.append(
                        child.value
                    )



        #
        # Deduplicate
        #

        entities = list(
            dict.fromkeys(
                entities
            )
        )



        matched = bool(
            entities
            or attack_pattern
        )



        #
        # Unknown IOC normalization
        #

        if not matched:

            risk = "unknown"

            confidence = 0.0



        return CorrelationResult(

            matched=matched,

            risk=risk,

            confidence=confidence,

            entities=entities,

            relationships=relationships,

            attack_pattern=attack_pattern,

            mitre=mitre,

            case_id=case_id,

            indicators=indicators or [],

            techniques=techniques or [],

            metadata={

                "mitre":
                    mitre,

                "case_id":
                    case_id,

                "reasoning":
                    reasoning or {},

            },

        )