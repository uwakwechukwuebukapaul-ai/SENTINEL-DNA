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

    status: str = "unknown"

    evidence: list[Any] = field(default_factory=list)

    threat_intelligence: Any = None

    intelligence_disposition: dict[str, Any] = field(default_factory=dict)

    timeline: list[Any] = field(default_factory=list)

    reasoning: Any = None

    reasoning_report: Any = None

    intelligence: Any = None

    decision_intelligence: Any = None

    governance: dict[str, Any] = field(default_factory=dict)

    confidence: Any = None

    uncertainty: Any = None

    tenant_context: Any = None

    agent_results: Any = field(
        default_factory=list
    )

    attack_story: list[Any] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    quality_assessment: Any = None

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

            "status": self.status,

            "evidence": self.evidence,

            "threat_intelligence": self.threat_intelligence,

            "intelligence_disposition": self.intelligence_disposition,

            "timeline": self.timeline,

            "reasoning": self.reasoning,

            "reasoning_report": self.reasoning_report,

            "intelligence": self.intelligence,

            "decision_intelligence": self.decision_intelligence.to_dict() if hasattr(self.decision_intelligence, "to_dict") else self.decision_intelligence,

            "governance": self.governance,

            "confidence": self.confidence,

            "uncertainty": self.uncertainty,

            "tenant_context": self.tenant_context,


            "agent_results":
                self.agent_results,


            "attack_story":
                self.attack_story,


            "metadata":
                self.metadata,

            "quality_assessment":
                self.quality_assessment,


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

    def generate_from_result(self, result: Any) -> InvestigationReport:
        """Build the analyst report from the canonical final result envelope."""
        data = result.to_dict() if hasattr(result, "to_dict") else dict(result or {})
        decision = data.get("decision_report") or {}
        if hasattr(decision, "to_dict"):
            decision = decision.to_dict()
        normalized = (data.get("intelligence") or {}).get("normalized", {})
        status_metadata = normalized.get("metadata", {}).get("intelligence_status", {}) if isinstance(normalized, dict) else {}
        governance = decision.get("metadata", {}).get("governance", {}) if isinstance(decision, dict) else {}
        if not governance:
            governance = {
                "mode": "ADVISORY_ONLY",
                "analyst_authority_required": True,
                "autonomous_action": False,
            }
        reasoning = data.get("reasoning_report")
        if hasattr(reasoning, "to_dict"):
            reasoning = reasoning.to_dict()
        uncertainty = data.get("metadata", {}).get("uncertainty", "unknown")
        report_metadata = {
            "report_type": "analyst_investigation_report",
            "recommendation_sources": list(data.get("recommendation_sources", []) or []),
        }
        provenance = status_metadata.get("intelligence_provenance") if isinstance(status_metadata, dict) else None
        if isinstance(provenance, dict):
            report_metadata["intelligence_provenance"] = {
                "providers": list(provenance.get("providers", []) or []),
                "status": list(provenance.get("status", []) or []),
                "disposition": provenance.get("disposition", "unavailable"),
            }
        fusion = status_metadata.get("fusion") if isinstance(status_metadata, dict) else None
        if isinstance(fusion, dict):
            report_metadata["intelligence_fusion"] = {
                key: fusion.get(key)
                for key in (
                    "status",
                    "aggregate_reputation",
                    "aggregate_confidence",
                    "supporting_providers",
                    "conflicting_providers",
                    "stale_providers",
                    "unavailable_providers",
                )
                if key in fusion
            }
        elif isinstance(status_metadata.get("fusion_results") if isinstance(status_metadata, dict) else None, list):
            report_metadata["intelligence_fusion"] = [
                {
                    key: item.get(key)
                    for key in (
                        "status",
                        "aggregate_reputation",
                        "aggregate_confidence",
                        "supporting_providers",
                        "conflicting_providers",
                        "stale_providers",
                        "unavailable_providers",
                    )
                    if isinstance(item, dict) and key in item
                }
                for item in status_metadata["fusion_results"]
                if isinstance(item, dict)
            ]
        provider_errors = status_metadata.get("provider_results") if isinstance(status_metadata, dict) else None
        if isinstance(provider_errors, list):
            report_metadata["intelligence_provider_errors"] = [
                {
                    "provider": item.get("provider"),
                    "code": getattr((item.get("error") or {}).get("code"), "value", (item.get("error") or {}).get("code")),
                    "retryable": (item.get("error") or {}).get("retryable"),
                }
                for item in provider_errors
                if isinstance(item, dict) and isinstance(item.get("error"), dict)
            ]
        correlation_id = (data.get("metadata") or {}).get("correlation_id") if isinstance(data.get("metadata"), dict) else None
        if correlation_id:
            report_metadata["correlation_id"] = correlation_id
        report = InvestigationReport(
            case_id=str(data.get("case_id") or "unknown"),
            title="AI Investigation Report",
            summary=(reasoning or {}).get("summary", "No investigation conclusion was recorded.") if isinstance(reasoning, dict) else "No investigation conclusion was recorded.",
            status=str(data.get("status") or "unknown"),
            risk=data.get("risk") if isinstance(data.get("risk"), dict) else {"value": data.get("risk", "unknown")},
            risk_score=float((data.get("risk") or {}).get("score", 0) if isinstance(data.get("risk"), dict) else 0),
            findings=list(data.get("findings", []) or []),
            evidence=list(data.get("artifacts", []) or []),
            threat_intelligence=data.get("threat_intelligence_report") or "unavailable",
            intelligence_disposition={
                "status": status_metadata.get("statuses", []),
                "disposition": status_metadata.get("disposition", "unavailable"),
            },
            mitre=list(data.get("mitre", []) or []),
            timeline=list(data.get("timeline", []) or []),
            reasoning=reasoning or "unavailable",
            reasoning_report=reasoning,
            intelligence=data.get("intelligence"),
            decision_intelligence=data.get("decision_intelligence"),
            recommendations=list(data.get("recommendations", []) or []),
            governance=governance,
            confidence=data.get("confidence"),
            uncertainty=uncertainty,
            tenant_context=data.get("tenant_context") or "unavailable",
            attack_story=data.get("attack_story") or "unavailable",
            metadata=report_metadata,
        )
        self.history_store.append(report)
        return report

    def generate_from_read_model(self, read_model: Any) -> InvestigationReport:
        """Create a compatibility report from the canonical analyst projection."""
        data = read_model.to_dict() if hasattr(read_model, "to_dict") else dict(read_model or {})
        investigation = data.get("investigation", {})
        summary = data.get("summary", {})
        report = InvestigationReport(
            case_id=str(investigation.get("case_id", "unknown")),
            title=str(summary.get("title", "AI Investigation Report")),
            summary=str(summary.get("decision") or "No investigation conclusion was recorded."),
            status=str(investigation.get("status", "unknown")),
            risk={"score": summary.get("risk", 0)},
            risk_score=float(summary.get("risk", 0) or 0),
            findings=list(data.get("findings", []) or []),
            evidence=list(data.get("evidence", []) or []),
            recommendations=list(data.get("recommendations", []) or []),
            mitre=list(data.get("mitre", []) or []),
            timeline=list(data.get("timeline", []) or []),
            confidence=summary.get("confidence"),
            quality_assessment=data.get("quality") or {},
            metadata={"source": "investigation_read_model", "feedback_count": len(data.get("feedback", []) or [])},
            tenant_context={"tenant_id": investigation.get("tenant_id")} if investigation.get("tenant_id") else None,
        )
        self.history_store.append(report)
        return report



    def history(self):

        return list(
            self.history_store
        )



    def clear_history(self):

        self.history_store.clear()
