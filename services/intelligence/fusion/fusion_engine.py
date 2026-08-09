"""
Intelligence Fusion Engine

Responsible for combining:
- Threat providers
- Reputation analysis
- Knowledge graph correlation
- MITRE enrichment

into one intelligence decision.
"""

from typing import Any

from .fusion_result import FusionResult


class FusionEngine:
    """
    Central intelligence fusion orchestrator.
    """


    def __init__(
        self,
        providers=None,
        knowledge_graph=None,
        correlator=None,
    ):

        self.providers = (
            providers or []
        )

        self.knowledge_graph = (
            knowledge_graph
        )

        self.correlator = (
            correlator
        )


    def register_provider(
        self,
        provider,
    ):
        """
        Add intelligence provider.
        """

        self.providers.append(
            provider
        )


    def fuse(
        self,
        indicator: str,
        indicator_type: str | None = None,
    ) -> FusionResult:
        """
        Execute intelligence fusion.
        """

        provider_results = []

        provider_names = []

        risk_scores = []


        #
        # Provider enrichment
        #

        for provider in self.providers:

            try:

                result = provider.lookup(
                    indicator,
                    indicator_type,
                )

                provider_results.append(
                    result
                )

                provider_names.append(
                    provider.name
                )


                if result.get(
                    "risk"
                ):

                    risk_scores.append(
                        result["risk"]
                    )


            except Exception:

                continue



        #
        # Knowledge graph correlation
        #

        entities = []

        relationships = []

        mitre = []


        if self.correlator:

            correlation = (
                self.correlator.correlate(
                    indicator,
                    indicator_type,
                )
            )


            if correlation:

                entities.extend(
                    correlation.entities
                )

                relationships.extend(
                    correlation.relationships
                )

                if correlation.metadata:

                    mitre.extend(
                        correlation.metadata.get(
                            "mitre",
                            []
                        )
                    )



        #
        # Risk calculation
        #

        risk = self.calculate_risk(
            risk_scores,
            bool(entities),
        )


        confidence = (
            self.calculate_confidence(
                provider_names,
                entities,
            )
        )


        return FusionResult(
            indicator=indicator,
            indicator_type=indicator_type,
            risk=risk,
            confidence=confidence,
            providers=provider_names,
            mitre=mitre,
            entities=entities,
            relationships=relationships,
            metadata={
                "provider_results":
                    provider_results
            },
        )


    def calculate_risk(
        self,
        scores,
        correlated,
    ):

        if correlated:

            return "high"


        if not scores:

            return "unknown"


        if "critical" in scores:

            return "critical"


        if "high" in scores:

            return "high"


        if "medium" in scores:

            return "medium"


        return "low"



    def calculate_confidence(
        self,
        providers,
        entities,
    ):

        confidence = 0.0


        if providers:

            confidence += 0.5


        if entities:

            confidence += 0.3


        if len(providers) > 1:

            confidence += 0.2


        return min(
            confidence,
            1.0
        )