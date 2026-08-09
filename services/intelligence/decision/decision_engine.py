"""
Sentinel DNA Decision Intelligence Engine.

Responsible for:

- incident decision generation
- SOC priority calculation
- recommended response actions
- automation readiness
"""

from __future__ import annotations

from typing import Any


class DecisionEngine:
    """
    Enterprise decision reasoning engine.
    """

    def __init__(self) -> None:
        self.version = "1.0"


    def analyze(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Compatibility API for investigation workflows.

        Converts raw investigation objects into
        normalized decision intelligence input.
        """

        normalized = {

            "classification":
                investigation.get(
                    "classification",
                    "security_incident",
                ),

            "severity":
                investigation.get(
                    "severity",
                    "low",
                ),

            "confidence":
                investigation.get(
                    "confidence",
                    1.0,
                ),

        }


        return self.decide(
            normalized
        )


    def decide(
        self,
        intelligence: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate security response decision.
        """

        classification = str(
            intelligence.get(
                "classification",
                "unknown",
            )
        ).lower()


        severity = str(
            intelligence.get(
                "severity",
                "low",
            )
        ).lower()


        confidence = float(
            intelligence.get(
                "confidence",
                0,
            )
        )


        priority = self._calculate_priority(
            classification,
            severity,
            confidence,
        )


        return {

            "status":
                "completed",


            "decision":
                self._calculate_decision(
                    priority
                ),


            "priority":
                priority,


            "classification":
                classification,


            "confidence":
                confidence,


            "recommended_actions":
                self._recommended_actions(
                    classification
                ),


            "automation_ready":
                self._automation_ready(
                    priority,
                    confidence,
                ),
        }


    def _calculate_priority(
        self,
        classification: str,
        severity: str,
        confidence: float,
    ) -> str:
        """
        Calculate SOC incident priority.
        """

        if classification == "unknown":

            if severity == "critical":

                return "P1"

            return "P4"


        if severity == "critical":

            return "P1"


        if (
            classification in {
                "phishing",
                "malware",
            }
            and severity == "high"
        ):

            return "P1"


        if severity == "high":

            return "P2"


        if severity == "medium":

            return "P2"


        if severity == "low":

            return "P3"


        return "P4"


    def _calculate_decision(
        self,
        priority: str,
    ) -> str:
        """
        Convert priority into SOC action.
        """

        if priority == "P1":

            return "respond"


        if priority == "P2":

            return "investigate"


        return "monitor"


    def _recommended_actions(
        self,
        classification: str,
    ) -> list[str]:
        """
        Generate analyst response actions.
        """

        if classification == "phishing":

            return [

                "Block malicious sender and domains.",

                "Remove phishing emails.",

                "Reset affected credentials.",

            ]


        if classification == "malware":

            return [

                "Isolate affected endpoint.",

                "Collect malware artifacts.",

                "Run endpoint investigation.",

            ]


        if classification == "security_incident":

            return [

                "Escalate critical security incident.",

                "Collect additional evidence.",

                "Begin containment workflow.",

            ]


        return [

            "Collect additional evidence.",

            "Monitor activity.",

        ]


    def _automation_ready(
        self,
        priority: str,
        confidence: float,
    ) -> bool:
        """
        Determine if SOAR automation can execute.
        """

        return (

            priority in {
                "P1",
                "P2",
            }

            and confidence >= 0.5

        )