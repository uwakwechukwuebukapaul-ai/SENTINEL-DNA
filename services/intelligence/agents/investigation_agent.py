"""Sentinel DNA autonomous investigation agent."""

from __future__ import annotations

from services.intelligence.agents.agent_capability import AgentCapability
from services.intelligence.agents.agent_context import AgentContext
from services.intelligence.agents.agent_metadata import AgentMetadata
from services.intelligence.agents.agent_result import (
    AgentExecutionStatus,
    AgentResult,
)
from services.intelligence.agents.base_agent import BaseAgent
from services.investigation_runtime.autonomous_investigation_intelligence_engine import (
    AutonomousInvestigationIntelligenceEngine,
)


class InvestigationAgent(BaseAgent):
    """Execute the autonomous investigation workflow."""

    def __init__(self) -> None:
        self.engine = AutonomousInvestigationIntelligenceEngine()

    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="Investigation Agent",
            version="1.0",
            description="Executes autonomous AI investigations.",
            investigation_types=[
                "phishing",
                "malware",
                "credential_access",
                "lateral_movement",
            ],
            tags=["investigation", "planner", "autonomous"],
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [
            AgentCapability(
                name="investigation_execution",
                description="Executes autonomous security investigations",
                category="investigation",
            )
        ]

    def validate(self, context: AgentContext) -> bool:
        return isinstance(context, AgentContext) and bool(context.case_id)

    def execute(self, context: AgentContext) -> AgentResult:
        if not self.validate(context):
            return AgentResult(
                agent_name=self.metadata.name,
                status=AgentExecutionStatus.FAILED,
                confidence=0.0,
                errors=["Invalid investigation context."],
            )

        investigation_id = context.case_id
        self.engine.create_investigation(
            investigation_id=investigation_id,
            investigation_type="security_alert",
            severity="high",
        )
        analysis = self.engine.investigate(
            context.alert,
            artifacts=context.evidence,
            iocs=context.iocs,
        )

        findings = [
            {
                "type": "investigation_analysis",
                "severity": "high",
                "description": "Autonomous investigation workflow completed.",
                "details": analysis,
            }
        ]
        recommendations = [
            "Investigate source IP reputation",
            "Review affected account activity",
        ]

        result = AgentResult(
            agent_name=self.metadata.name,
            status=AgentExecutionStatus.SUCCESS,
            confidence=90.0,
            findings=findings,
            recommendations=recommendations,
        )

        result.artifacts["investigation_analysis"] = analysis
        result.artifacts["investigation_plan"] = {
            "steps": analysis.get("steps", [])
            if isinstance(analysis, dict)
            else [],
            "status": analysis.get("status", "completed")
            if isinstance(analysis, dict)
            else "completed",
        }
        result.metrics["engine"] = (
            "AutonomousInvestigationIntelligenceEngine"
        )

        evidence = list(getattr(context, "evidence", []) or [])
        if not evidence:
            evidence = list(context.shared_data.get("artifacts", []) or [])
        if not evidence:
            evidence = list(context.shared_data.get("evidence", []) or [])

        indicators = list(getattr(context, "iocs", []) or [])
        suspicious_text = " ".join(str(item).lower() for item in evidence)
        suspicious = bool(indicators) or any(
            keyword in suspicious_text
            for keyword in (
                "failed",
                "suspicious",
                "malicious",
                "attack",
                "threat",
            )
        )

        result.metadata["artifact_count"] = len(evidence)
        result.metadata["indicator_count"] = len(indicators)
        result.metadata["suspicious_activity"] = suspicious

        if suspicious:
            result.findings.append(
                {
                    "type": "investigation",
                    "description": "Suspicious authentication activity detected",
                    "severity": "high",
                    "case_id": context.case_id,
                    "indicators": indicators,
                }
            )

        return result

    def summarize(self, result: AgentResult) -> str:
        analysis = result.artifacts.get("investigation_analysis", {})
        steps = analysis.get("steps", []) if isinstance(analysis, dict) else []
        return (
            f"Autonomous investigation completed with confidence "
            f"{result.confidence}%.\nsteps: {steps}"
        )

    def cleanup(self) -> None:
        """Release agent resources."""
