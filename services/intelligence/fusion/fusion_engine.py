"""
Fusion Engine

Combines intelligence signals,
provider enrichment, and correlation
results into a unified intelligence
assessment.
"""

from typing import Any

from services.intelligence.fusion.fusion_result import (
    FusionResult,
)



class FusionEngine:
    """
    Intelligence decision engine.

    Responsible for:
    - risk scoring
    - confidence calculation
    - MITRE mapping
    - intelligence aggregation
    """



    def __init__(
        self,
    ):

        self.risk_weights = {

            "critical": 1.0,

            "high": 0.8,

            "medium": 0.5,

            "low": 0.2,

        }



    def fuse(
        self,
        context: Any,
    ) -> FusionResult:

        """
        Generate unified intelligence result.
        """


        signals = []

        records = []

        correlation = None



        #
        # Support runtime context
        #

        if hasattr(
            context,
            "signals",
        ):

            signals = (
                context.signals
            )


        elif isinstance(
            context,
            dict,
        ):

            signals = (
                context.get(
                    "signals",
                    [],
                )
            )



        if hasattr(
            context,
            "intelligence_records",
        ):

            records = (
                context.intelligence_records
            )


        elif isinstance(
            context,
            dict,
        ):

            records = (
                context.get(
                    "records",
                    [],
                )
            )



        if hasattr(
            context,
            "correlations",
        ):

            if context.correlations:

                correlation = (
                    context.correlations[0]
                )


        elif isinstance(
            context,
            dict,
        ):

            correlation = (
                context.get(
                    "correlation"
                )
            )



        #
        # Risk calculation
        #

        risk = (
            self._calculate_risk(
                correlation,
                records,
                signals,
            )
        )



        confidence = (
            self._calculate_confidence(
                correlation,
                records,
                signals,
            )
        )



        mitre = (
            self._extract_mitre(
                correlation,
                records,
            )
        )



        attack_pattern = (
            self._extract_attack_pattern(
                correlation
            )
        )



        return FusionResult(

            risk=risk,

            confidence=confidence,

            mitre=mitre,

            attack_pattern=attack_pattern,

            signals=signals,

            records=records,

            metadata={

                "signal_count":
                    len(signals),

                "record_count":
                    len(records),

            },

        )



    def _calculate_risk(
        self,
        correlation,
        records,
        signals,
    ):

        if correlation:

            value = getattr(
                correlation,
                "risk",
                None,
            )

            if value:

                return value



        if records:

            return "medium"



        if len(signals) >= 3:

            return "medium"



        return "low"



    def _calculate_confidence(
        self,
        correlation,
        records,
        signals,
    ):

        score = 0.0



        if correlation:

            score += 0.5



        if records:

            score += 0.3



        if len(signals) >= 3:

            score += 0.2



        return min(
            score,
            1.0,
        )



    def _extract_mitre(
        self,
        correlation,
        records,
    ):

        techniques = []



        if correlation:

            techniques.extend(

                getattr(
                    correlation,
                    "mitre",
                    [],
                )
                or []

            )



        for record in records:

            techniques.extend(

                getattr(
                    record,
                    "mitre",
                    [],
                )
                or []

            )



        return list(
            set(
                techniques
            )
        )



    def _extract_attack_pattern(
        self,
        correlation,
    ):

        if correlation:

            return getattr(
                correlation,
                "attack_pattern",
                None,
            )


        return None