"""
Sentinel DNA Investigation Result

Canonical investigation execution response contract.

Compatible with:

- InvestigationCoordinator
- InvestigationPipeline
- InvestigationOrchestrator
- ExecutionOrchestrator
- Reporting
- Decision Intelligence
- Runtime execution
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class InvestigationResult:
    """
    Unified investigation result envelope.

    Maintains backward compatibility across
    Sentinel DNA intelligence layers.
    """


    # =========================================================
    # EXECUTION STATE
    # =========================================================

    success: bool = False

    status: str = "failed"

    message: Optional[str] = None

    error: Optional[str] = None

    errors: list[Any] = field(
        default_factory=list
    )


    # =========================================================
    # IDENTIFIERS
    # =========================================================

    investigation_id: Optional[str] = None

    case_id: Optional[str] = None

    execution_id: Optional[str] = None



    # =========================================================
    # INPUT
    # =========================================================

    artifacts: list[Any] = field(
        default_factory=list
    )



    # =========================================================
    # PLAN / EXECUTION
    # =========================================================

    plan: Any = None

    plan_name: Optional[str] = None

    execution: Any = None



    # =========================================================
    # INTELLIGENCE
    # =========================================================

    correlation: Any = None

    fusion: Any = None

    reasoning: Any = None

    reasoning_report: Any = None

    memory_reference: Optional[str] = None

    decision_report: Any = None

    copilot_summary: Any = None

    narrative_report: Any = None

    threat_intelligence_report: Any = None

    soar_recommendation: Any = None

    integration_context: Any = None

    intelligence: Any = None

    ai_reasoning: Optional[str] = None

    ai_confidence: Optional[float] = None

    ai_evidence_references: list[str] = field(default_factory=list)

    ai_provider: Optional[str] = None



    # =========================================================
    # FINDINGS
    # =========================================================

    findings: list[Any] = field(
        default_factory=list
    )

    indicators: list[Any] = field(
        default_factory=list
    )

    entities: list[Any] = field(
        default_factory=list
    )

    relationships: list[Any] = field(
        default_factory=list
    )

    mitre: list[Any] = field(
        default_factory=list
    )



    # =========================================================
    # DECISION INTELLIGENCE
    # =========================================================

    recommendations: list[Any] = field(
        default_factory=list
    )

    decisions: list[Any] = field(
        default_factory=list
    )



    # =========================================================
    # RISK MODEL
    # =========================================================

    risk: Optional[str] = None

    confidence: Optional[float] = None

    priority: Optional[str] = None



    # =========================================================
    # ATTACK STORY / TIMELINE
    # =========================================================

    attack_story: Any = None

    timeline: list[Any] = field(
        default_factory=list
    )



    # =========================================================
    # LEGACY COMPATIBILITY
    # =========================================================

    results: list[Any] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )



    # =========================================================
    # HELPERS
    # =========================================================

    def update_metadata(
        self,
        data: dict[str, Any],
    ) -> None:

        self.metadata.update(data)



    def add_result(
        self,
        result: Any,
    ) -> None:

        self.results.append(result)



    def add_finding(
        self,
        finding: Any,
    ) -> None:

        self.findings.append(finding)



    def add_timeline_event(
        self,
        event: Any,
    ) -> None:

        self.timeline.append(event)



    # =========================================================
    # DICT COMPATIBILITY
    # =========================================================

    def __getitem__(
        self,
        key: str,
    ) -> Any:

        return self.to_dict()[key]



    def __setitem__(
        self,
        key: str,
        value: Any,
    ) -> None:

        setattr(
            self,
            key,
            value,
        )



    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:

        return self.to_dict().get(
            key,
            default,
        )



    # =========================================================
    # SERIALIZATION
    # =========================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {

            "success": self.success,
            "status": self.status,
            "message": self.message,
            "error": self.error,
            "errors": self.errors,

            "investigation_id":
                self.investigation_id,

            "case_id":
                self.case_id,

            "execution_id":
                self.execution_id,

            "plan":
                self.plan,

            "plan_name":
                self.plan_name,

            "execution":
                self.execution,

            "artifacts":
                self.artifacts,

            "correlation":
                self.correlation,

            "fusion":
                self.fusion,

            "reasoning":
                self.reasoning,

            "reasoning_report":
                self.reasoning_report.to_dict() if hasattr(self.reasoning_report, "to_dict") else self.reasoning_report,

            "memory_reference": self.memory_reference,

            "decision_report": self.decision_report.to_dict() if hasattr(self.decision_report, "to_dict") else self.decision_report,

            "copilot_summary": self.copilot_summary.to_dict() if hasattr(self.copilot_summary, "to_dict") else self.copilot_summary,

            "narrative_report": self.narrative_report.to_dict() if hasattr(self.narrative_report, "to_dict") else self.narrative_report,

            "threat_intelligence_report": self.threat_intelligence_report.to_dict() if hasattr(self.threat_intelligence_report, "to_dict") else self.threat_intelligence_report,

            "soar_recommendation": self.soar_recommendation,

            "integration_context": self.integration_context,

            "intelligence":
                self.intelligence,

            "ai_reasoning": self.ai_reasoning,

            "ai_confidence": self.ai_confidence,

            "ai_evidence_references": self.ai_evidence_references,

            "ai_provider": self.ai_provider,

            "findings":
                self.findings,

            "indicators":
                self.indicators,

            "entities":
                self.entities,

            "relationships":
                self.relationships,

            "mitre":
                self.mitre,

            "recommendations":
                self.recommendations,

            "decisions":
                self.decisions,

            "risk":
                self.risk,

            "confidence":
                self.confidence,

            "priority":
                self.priority,

            "attack_story":
                self.attack_story,

            "timeline":
                self.timeline,

            "results":
                self.results,

            "metadata":
                self.metadata,
        }



    # =========================================================
    # FACTORIES
    # =========================================================

    @classmethod
    def success_result(
        cls,
        **kwargs: Any,
    ) -> "InvestigationResult":

        return cls(
            success=True,
            status="completed",
            **kwargs,
        )



    @classmethod
    def failure_result(
        cls,
        error: str,
        **kwargs: Any,
    ) -> "InvestigationResult":

        return cls(
            success=False,
            status="failed",
            error=error,
            **kwargs,
        )
