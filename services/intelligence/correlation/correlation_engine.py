"""
Sentinel DNA Correlation Engine

Responsibilities:

- IOC correlation
- Threat relationship discovery
- Entity graph analysis
- Confidence scoring
- Attack story generation

This module provides the intelligence correlation layer
between evidence collection and AI investigation reasoning.
"""


from datetime import datetime, timezone



# ==========================================================
# Correlation Result
# ==========================================================

class CorrelationResult:
    """
    Stable correlation result contract.
    """

    def __init__(
        self,
        case_id,
        indicators=None,
        techniques=None,
        confidence=0.0,
        attack_story=None,
        metadata=None,
    ):

        self.case_id = case_id

        self.indicators = indicators or []

        self.techniques = techniques or []

        self.confidence = confidence

        self.attack_story = attack_story or []

        self.metadata = metadata or {}



    def to_dict(self):

        return {

            "case_id":
                self.case_id,

            "indicators":
                self.indicators,

            "techniques":
                self.techniques,

            "confidence":
                self.confidence,

            "attack_story":
                self.attack_story,

            "metadata":
                self.metadata,

        }




# ==========================================================
# Threat Correlation Result
# ==========================================================

class ThreatCorrelationResult:
    """
    Threat graph correlation response.
    """

    def __init__(
        self,
        matched=False,
        entities=None,
        risk="unknown",
        confidence=0.0,
    ):

        self.matched = matched

        self.entities = entities or []

        self.risk = risk

        self.confidence = confidence



    def to_dict(self):

        return {

            "matched":
                self.matched,

            "entities":
                self.entities,

            "risk":
                self.risk,

            "confidence":
                self.confidence,

        }




# ==========================================================
# Correlation Engine
# ==========================================================

class CorrelationEngine:
    """
    Main intelligence correlation engine.
    """



    def correlate(
        self,
        case_id,
        indicators=None,
        techniques=None,
        reason=None,
        reasoning=None,
    ):
        """
        Correlate investigation intelligence.

        Supports:

        reasoning={
            "classification":"phishing"
        }

        and legacy:

        reason="phishing"
        """

        indicators = indicators or []

        techniques = techniques or []



        if reasoning:

            reason = reasoning.get(
                "classification"
            )



        confidence = 0.0



        # IOC evidence

        if indicators:

            confidence += 0.3



        # ATT&CK technique mapping

        if techniques:

            confidence += 0.3



        # Intelligence classification

        if reason:

            confidence += 0.3



        if confidence > 1.0:

            confidence = 1.0



        attack_story = []



        if indicators:

            attack_story.append(
                "IOC indicators correlated"
            )



        if techniques:

            attack_story.append(
                "Attack techniques identified"
            )



        if reason:

            attack_story.append(
                f"Threat classified as {reason}"
            )



        return CorrelationResult(

            case_id=case_id,

            indicators=indicators,

            techniques=techniques,

            confidence=confidence,

            attack_story=attack_story,

            metadata={

                "created_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat()

            },

        )





# ==========================================================
# Threat Correlator
# ==========================================================

class ThreatCorrelator:
    """
    Knowledge graph threat relationship correlator.
    """



    def __init__(
        self,
        graph=None,
    ):

        self.graph = graph



    def correlate(
        self,
        indicator,
        entity_type=None,
    ):

        if not self.graph:

            return ThreatCorrelationResult()



        entities = getattr(
            self.graph,
            "entities",
            []
        )



        # Support dict graph storage

        if isinstance(
            entities,
            dict,
        ):

            entities = list(
                entities.values()
            )



        matched_entities = []



        for entity in entities:

            value = getattr(
                entity,
                "value",
                entity,
            )

            current_type = getattr(
                entity,
                "entity_type",
                None,
            )



            if (

                value == indicator

                and

                (
                    entity_type is None

                    or

                    current_type == entity_type

                )

            ):

                matched_entities.append(
                    entity
                )



        expanded_entities = list(
            matched_entities
        )



        relationships = getattr(
            self.graph,
            "relationships",
            []
        )



        matched_ids = [

            getattr(
                item,
                "id",
                None,
            )

            for item in matched_entities

        ]



        # Expand graph relationships

        for relationship in relationships:


            source = getattr(
                relationship,
                "source",
                None,
            )


            target = getattr(
                relationship,
                "target",
                None,
            )



            if source in matched_ids:


                for entity in entities:


                    if getattr(
                        entity,
                        "id",
                        None,
                    ) == target:

                        expanded_entities.append(
                            entity
                        )



            if target in matched_ids:


                for entity in entities:


                    if getattr(
                        entity,
                        "id",
                        None,
                    ) == source:

                        expanded_entities.append(
                            entity
                        )



        values = []



        for entity in expanded_entities:


            value = getattr(
                entity,
                "value",
                entity,
            )


            values.append(
                value
            )



        risk = "unknown"

        confidence = 0.0



        if matched_entities:

            risk = "high"

            confidence = 0.6



        return ThreatCorrelationResult(

            matched=bool(
                matched_entities
            ),

            entities=values,

            risk=risk,

            confidence=confidence,

        )