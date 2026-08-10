"""
Sentinel DNA Investigation Reporting Contract

Unified analyst-ready investigation report.

Used by:

- Investigation Report Builder
- Investigation Orchestrator
- Investigation Service
- Analyst Dashboard
- Reporting APIs
- Investigation History
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


class InvestigationReport:
    """
    Enterprise investigation report object.

    Supports:

        report.case_id

    and:

        report["case_id"]
    """

    def __init__(
        self,
        case_id: Optional[str] = None,
        severity: str = "unknown",
        risk_score: float = 0.0,
        findings: Optional[list[Any]] = None,
        recommendations: Optional[list[Any]] = None,
        agent_results: Optional[dict[str, Any]] = None,
        attack_story: str = "",
        indicators: Optional[list[Any]] = None,
        techniques: Optional[list[Any]] = None,
        confidence: float = 0.0,
        decision: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):

        self.case_id = case_id

        self.severity = severity

        self.risk_score = risk_score

        self.findings = findings or []

        self.recommendations = (
            recommendations or []
        )

        self.agent_results = (
            agent_results or {}
        )

        self.attack_story = attack_story

        self.indicators = indicators or []

        self.techniques = techniques or []

        self.confidence = confidence

        self.decision = decision

        self.metadata = metadata or {}

        self.history: list[dict[str, Any]] = []


    # --------------------------------------------------
    # GENERATION
    # --------------------------------------------------

    def generate(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate analyst-ready report.
        """

        correlation = (
            investigation.get(
                "correlation",
                {},
            )
        )

        if hasattr(
            correlation,
            "to_dict",
        ):
            correlation = correlation.to_dict()


        decision_data = (
            investigation.get(
                "decision",
                {},
            )
        )


        if hasattr(
            decision_data,
            "to_dict",
        ):
            decision_data = decision_data.to_dict()


        self.case_id = (
            investigation.get(
                "case_id",
                self.case_id,
            )
        )


        self.agent_results = (
            investigation.get(
                "agent_results",
                investigation.get(
                    "agents",
                    self.agent_results,
                ),
            )
        )


        self.attack_story = (
            investigation.get(
                "attack_story",
                correlation.get(
                    "attack_story",
                    self.attack_story,
                ),
            )
        )


        self.indicators = (
            correlation.get(
                "indicators",
                self.indicators,
            )
        )


        self.techniques = (
            correlation.get(
                "techniques",
                self.techniques,
            )
        )


        self.confidence = (
            correlation.get(
                "confidence",
                self.confidence,
            )
        )


        self.decision = (
            decision_data.get(
                "decision",
                self.decision,
            )
        )


        self.severity = self._calculate_risk(
            confidence=self.confidence,
            indicators=self.indicators,
            decision=self.decision,
        )


        report = {

            "status":
                "completed",

            "case_id":
                self.case_id,

            "severity":
                self.severity,

            "risk_rating":
                self.severity,

            "confidence":
                self.confidence,

            "attack_story":
                self.attack_story,

            "indicators":
                self.indicators,

            "techniques":
                self.techniques,

            "decision":
                self.decision,

            "agent_results":
                self.agent_results,

            "generated_at":
                self._timestamp(),

        }


        self.history.append(
            report
        )


        return report


    # --------------------------------------------------
    # RISK ENGINE
    # --------------------------------------------------

    def _calculate_risk(
        self,
        confidence: float,
        indicators: list[Any],
        decision: Optional[str],
    ) -> str:

        if decision == "respond":
            return "critical"


        if confidence >= 0.8:
            return "high"


        if confidence >= 0.5:
            return "medium"


        if indicators:
            return "medium"


        return "low"



    # --------------------------------------------------
    # HISTORY
    # --------------------------------------------------

    def get_history(
        self,
    ) -> list[dict[str, Any]]:

        return list(
            self.history
        )


    def clear_history(
        self,
    ) -> None:

        self.history.clear()



    # --------------------------------------------------
    # SERIALIZATION
    # --------------------------------------------------

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {

            "case_id":
                self.case_id,

            "severity":
                self.severity,

            "risk_score":
                self.risk_score,

            "findings":
                self.findings,

            "recommendations":
                self.recommendations,

            "agent_results":
                self.agent_results,

            "attack_story":
                self.attack_story,

            "indicators":
                self.indicators,

            "techniques":
                self.techniques,

            "confidence":
                self.confidence,

            "decision":
                self.decision,

            "metadata":
                self.metadata,
        }


    # --------------------------------------------------
    # DICT COMPATIBILITY
    # --------------------------------------------------

    def __getitem__(
        self,
        key: str,
    ) -> Any:

        return self.to_dict()[key]


    def get(
        self,
        key: str,
        default=None,
    ) -> Any:

        return self.to_dict().get(
            key,
            default,
        )


    # --------------------------------------------------
    # TIME
    # --------------------------------------------------

    @staticmethod
    def _timestamp() -> str:

        return datetime.now(
            timezone.utc
        ).isoformat()



__all__ = [
    "InvestigationReport",
]