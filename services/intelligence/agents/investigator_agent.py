"""
Sentinel DNA Autonomous Investigator Agent.

Coordinates investigation reasoning flow.

Pipeline:

Input Alert
    |
Normalize Investigation
    |
Analyze Threat
    |
Generate Decision
    |
Determine Approval
    |
Return Investigation Result
"""

from __future__ import annotations

from typing import Any



class InvestigatorAgent:
    """
    Autonomous SOC investigation agent.
    """


    def __init__(
        self,
        decision_engine=None,
        recommendation_engine=None,
        response_orchestrator=None,
    ) -> None:


        self.decision_engine = (
            decision_engine
        )

        self.recommendation_engine = (
            recommendation_engine
        )

        self.response_orchestrator = (
            response_orchestrator
        )



    def investigate(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute autonomous investigation.
        """


        investigation_id = (
            investigation.get(
                "id",
                "UNKNOWN",
            )
        )


        normalized = (
            self._normalize(
                investigation
            )
        )


        decision = (
            self._generate_decision(
                normalized
            )
        )


        recommendations = (
            self._generate_recommendations(
                decision
            )
        )


        approval_required = (
            investigation.get(
                "requires_approval",
                False,
            )
        )


        return {

            "status":
                "completed",


            "investigation_id":
                investigation_id,


            "decision":
                decision,


            "recommendations":
                recommendations,


            "approval_required":
                approval_required,


            "state":
                "completed",

        }



    def _normalize(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:

        return {

            "classification":
                investigation.get(
                    "classification",
                    "unknown",
                ),


            "severity":
                investigation.get(
                    "severity",
                    "low",
                ),


            "confidence":
                investigation.get(
                    "confidence",
                    0.0,
                ),

        }



    def _generate_decision(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Produce investigation decision.

        Uses DecisionEngine when available.
        """


        if self.decision_engine:

            return (
                self.decision_engine.decide(
                    investigation
                )
            )


        severity = (
            investigation.get(
                "severity"
            )
        )


        if severity in (
            "critical",
            "high",
        ):

            return {

                "decision":
                    "respond",

                "priority":
                    "P1",

            }


        return {

            "decision":
                "monitor",

            "priority":
                "P3",

        }



    def _generate_recommendations(
        self,
        decision: dict[str, Any],
    ) -> list[str]:
        """
        Generate response recommendations.
        """


        if self.recommendation_engine:

            result = (
                self.recommendation_engine.recommend(
                    decision
                )
            )

            return result


        if decision.get(
            "decision"
        ) == "respond":

            return [

                "Investigate affected assets",

                "Block malicious indicators",

                "Collect additional evidence",

            ]


        return [

            "Continue monitoring",

        ]