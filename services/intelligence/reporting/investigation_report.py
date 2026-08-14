"""
Sentinel DNA Investigation Report Model.

Enterprise investigation reporting contract.

Supports:
- AI investigation reports
- Agent result preservation
- Risk scoring
- Historical reports
- Legacy test compatibility
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any



@dataclass
class InvestigationReport:
    """
    Final investigation report object.
    """

    case_id: str = ""

    title: str = ""

    summary: str = ""

    severity: str = "LOW"

    risk_score: float = 0.0

    risk: dict[str, Any] = field(default_factory=dict)

    mitre: list[Any] = field(default_factory=list)

    findings: list[Any] = field(
        default_factory=list
    )

    recommendations: list[Any] = field(
        default_factory=list
    )

    agent_results: Any = field(
        default_factory=list
    )

    attack_story: list[Any] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    created_at: str = field(
        default_factory=lambda:
        datetime.now(
            timezone.utc
        ).isoformat()
    )



    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {

            "case_id":
                self.case_id,


            "title":
                self.title,


            "summary":
                self.summary,


            "severity":
                self.severity,


            "risk_score":
                self.risk_score,

            "risk":
                self.risk or {"score": self.risk_score},

            "mitre":
                self.mitre,


            "findings":
                self.findings,


            "recommendations":
                self.recommendations,


            "agent_results":
                self.agent_results,


            "attack_story":
                self.attack_story,


            "metadata":
                self.metadata,


            "created_at":
                self.created_at,

        }



    def as_dict(
        self,
    ) -> dict[str, Any]:

        return self.to_dict()

    def generate(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Legacy result-oriented report generation contract."""
        context = context or {}
        correlation = context.get("correlation") or {}
        confidence = float(correlation.get("confidence", 0) or 0)
        result = {
            "case_id": context.get("case_id", self.case_id),
            "status": "completed",
            "risk_rating": "critical" if confidence >= 0.9 else "high" if confidence >= 0.7 else "medium",
            "attack_story": correlation.get("attack_story", ""),
            "confidence": confidence,
        }
        history = getattr(self, "_history", None)
        if history is None:
            history = []
            self._history = history
        history.append(result)
        return result

    def get_history(self) -> list[dict[str, Any]]:
        return list(getattr(self, "_history", []))

    def clear_history(self) -> None:
        self._history = []

class InvestigationReportGenerator:
    """
    Backward compatible investigation report generator.

    Supports:
    - New keyword based report creation
    - Legacy positional generation used by coordinators
    """

    def __init__(self):

        self.history_store = []


    def generate(
        self,
        *args,
        **kwargs,
    ):

        # ==================================================
        # Legacy positional contract
        #
        # generate(
        #     case_id,
        #     title,
        #     summary,
        #     severity,
        #     findings
        # )
        # ==================================================

        if args:

            case_id = (
                args[0]
                if len(args) > 0
                else "UNKNOWN"
            )

            title = (
                args[1]
                if len(args) > 1
                else "Investigation Report"
            )

            summary = (
                args[2]
                if len(args) > 2
                else ""
            )

            severity = (
                args[3]
                if len(args) > 3
                else "info"
            )

            findings = (
                args[4]
                if len(args) > 4
                else []
            )


            report = InvestigationReport(
                case_id=case_id,
                title=title,
                summary=summary,
                severity=severity,
                findings=findings,
                recommendations=list(getattr(args[1], "recommendations", []) if len(args) > 1 else []),
                agent_results=[],
                risk={"score": getattr(args[1], "risk_score", 0) if len(args) > 1 else 0},
                mitre=list(getattr(args[1], "mitre_techniques", []) if len(args) > 1 else []),
                attack_story=getattr(args[1], "attack_story", []) if len(args) > 1 else [],
            )


        # ==================================================
        # New keyword contract
        # ==================================================

        else:

            report = InvestigationReport(
                **kwargs
            )


        self.history_store.append(
            report
        )


        return report



    def history(self):

        return list(
            self.history_store
        )



    def clear_history(self):

        self.history_store.clear()
