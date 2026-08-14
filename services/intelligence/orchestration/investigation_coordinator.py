"""
Sentinel DNA Investigation Coordinator.

Canonical application-level investigation coordinator.

Responsibilities:

- Investigation planning
- Investigation context creation
- Runtime task creation
- Runtime capability validation
- Runtime task execution
- Stable investigation result generation

Architecture:

API
 |
 v
InvestigationRuntime
 |
 v
InvestigationCoordinator
 |
 v
InvestigationPlan
 |
 v
Runtime Task(s)
 |
 v
RuntimeTaskExecutor
 |
 v
AI Investigation Capabilities

The coordinator owns workflow coordination.

RuntimeTaskExecutor owns task execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


from .investigation_plan import InvestigationPlan
from .investigation_orchestrator import InvestigationOrchestrator

from services.intelligence.runtime.task import Task

from services.intelligence.investigation.investigation_result import (
    InvestigationResult,
)
from services.investigation_intelligence import (
    ConfidenceResolver,
    FindingAggregator,
)
from services.intelligence.investigation.attack_story_builder import (
    AttackStoryBuilder,
)
from services.intelligence.investigation.mitre_adapter import MITREAdapter
from services.intelligence.investigation.risk_adapter import RiskAdapter
from services.intelligence.models.investigation_intelligence import (
    InvestigationIntelligence,
)
from services.intelligence.repository.intelligence_repository import IntelligenceRepository
from services.intelligence.timeline.timeline_engine import InvestigationTimelineEngine
from services.intelligence.reporting.investigation_report import InvestigationReportGenerator
from services.intelligence.repository.report_repository import InvestigationReportRepository
from services.observability import ObservabilityService
from services.intelligence.reasoning import EvidenceReasoner
from services.intelligence.memory import MemoryService
import time


# ============================================================
# Investigation Context
# ============================================================


@dataclass
class InvestigationContext:
    """
    Coordinator-level investigation execution context.
    """

    investigation_id: str

    artifacts: list[dict[str, Any]] = field(
        default_factory=list
    )

    evidence: list[dict[str, Any]] = field(default_factory=list)

    iocs: list[dict[str, Any]] = field(default_factory=list)

    timeline: list[dict[str, Any]] = field(default_factory=list)


# ============================================================
# Investigation Coordinator
# ============================================================


class InvestigationCoordinator:
    """
    Canonical application-level investigation coordinator.

    Coordinates:

        Investigation planning
              |
              v
        Runtime task creation
              |
              v
        Runtime task execution
              |
              v
        AI investigation capabilities


    RuntimeTaskExecutor owns execution.

    Coordinator owns workflow.
    """


    def __init__(
        self,
        registry: Any = None,
        runtime: Any = None,
        orchestrator: Any = None,
    ) -> None:

        self.registry = registry
        self.runtime = runtime
        self.orchestrator = (
            orchestrator
            if orchestrator is not None
            else InvestigationOrchestrator()
        )
        self.finding_aggregator = FindingAggregator()
        self.confidence_resolver = ConfidenceResolver()
        self.risk_adapter = RiskAdapter()
        self.mitre_adapter = MITREAdapter()
        self.attack_story_builder = AttackStoryBuilder()
        self.intelligence_repository = IntelligenceRepository()
        self.timeline_engine = InvestigationTimelineEngine()
        self.report_generator = InvestigationReportGenerator()
        self.report_repository = InvestigationReportRepository()
        self.evidence_reasoner = EvidenceReasoner(
            getattr(runtime, "ai_runtime", None) or getattr(self.orchestrator, "ai_runtime", None)
        )
        self.memory_service = MemoryService()


    # ========================================================
    # Context
    # ========================================================


    def create_context(
        self,
        investigation_id: str,
        artifacts: list[dict[str, Any]],
        evidence: Optional[list[dict[str, Any]]] = None,
        iocs: Optional[list[dict[str, Any]]] = None,
        timeline: Optional[list[dict[str, Any]]] = None,
    ) -> InvestigationContext:

        return InvestigationContext(
            investigation_id=investigation_id,
            artifacts=list(artifacts),
            evidence=list(evidence or []),
            iocs=list(iocs or []),
            timeline=list(timeline or []),
        )


    # ========================================================
    # Planning
    # ========================================================


    def create_plan(
        self,
        case_id: str,
        alert: dict[str, Any],
    ) -> InvestigationPlan:

        return InvestigationPlan(
            case_id=case_id,
            name="Standard Security Investigation",
            plan_name="Standard Security Investigation",
            agents=[
                "investigation_execution",
                "threat_intelligence",
                "ioc_enrichment",
            ],
        )


    # ========================================================
    # Runtime Task Creation
    # ========================================================


    def _create_runtime_task(
        self,
        case_id: str,
        alert: dict[str, Any],
        plan: InvestigationPlan,
        capability: str,
        context: InvestigationContext,
    ) -> Task:

        return Task(
            capability=capability,
            payload={
                "case_id": case_id,
                "alert": alert,
                "plan": plan,
                "context": context,
                "investigation_id": context.investigation_id,
                "artifacts": list(context.artifacts),
                "evidence": list(context.evidence),
                "iocs": list(context.iocs),
                "timeline": list(context.timeline),
            },
        )


    # ========================================================
    # Capability Handling
    # ========================================================


    def _get_plan_capabilities(
        self,
        plan: InvestigationPlan,
    ) -> list[str]:

        capabilities = getattr(
            plan,
            "agents",
            [],
        )

        return [
            str(capability)
            for capability in capabilities
            if capability
        ]


    def _validate_capabilities(
        self,
        capabilities: list[str],
    ) -> list[str]:

        if self.runtime is None:
            return list(capabilities)

        missing = []

        for capability in capabilities:

            if not self.runtime.available(
                capability
            ):
                missing.append(
                    capability
                )

        return missing


    # ========================================================
    # Investigation Execution
    # ========================================================

    @staticmethod
    def _agent_result_to_dict(result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            return dict(result)
        if hasattr(result, "to_dict"):
            return dict(result.to_dict())
        return {
            "findings": list(getattr(result, "findings", []) or []),
            "recommendations": list(getattr(result, "recommendations", []) or []),
            "metadata": dict(getattr(result, "metadata", {}) or {}),
            "artifacts": dict(getattr(result, "artifacts", {}) or {}),
            "confidence": getattr(result, "confidence", None),
            "status": getattr(getattr(result, "status", None), "value", getattr(result, "status", None)),
        }

    def _build_success_result(
        self,
        case_id: str,
        alert: dict[str, Any],
        plan: InvestigationPlan,
        normalized_artifacts: list[dict[str, Any]],
        execution: dict[str, Any],
        workflow: Any,
    ) -> InvestigationResult:
        intelligence: dict[str, dict[str, Any]] = {}
        findings: list[Any] = []
        recommendations: list[Any] = []
        confidence_values: list[float] = []
        engine_analysis: dict[str, Any] = {}

        for item in execution["results"]:
            result = self._agent_result_to_dict(item.get("result"))
            intelligence[item["capability"]] = result
            findings.extend(result.get("findings", []) or [])
            recommendations.extend(result.get("recommendations", []) or [])
            artifacts = result.get("artifacts", {}) or {}
            if isinstance(artifacts, dict):
                analysis = artifacts.get("investigation_analysis")
                if isinstance(analysis, dict):
                    engine_analysis.update(analysis)
            confidence = result.get("confidence")
            if confidence is not None:
                try:
                    value = float(confidence)
                    confidence_values.append(value / 100 if value > 1 else value)
                except (TypeError, ValueError):
                    pass

        confidence_data = self.confidence_resolver.resolve(intelligence)
        if confidence_values:
            confidence_data["score"] = round(sum(confidence_values) / len(confidence_values), 4)
        ioc_count = int(
            intelligence.get("ioc_enrichment", {})
            .get("metadata", {})
            .get("ioc_count", 0)
            or len(engine_analysis.get("iocs", []) or [])
        )
        engine_mitre = engine_analysis.get("mitre", []) or []
        mitre = {
            "case_id": case_id,
            "techniques": list(engine_mitre),
        }
        if not mitre["techniques"]:
            mitre = self.mitre_adapter.execute(case_id, alert)
        if engine_analysis.get("risk_score") is not None:
            score = float(engine_analysis["risk_score"])
            risk = {
                "score": int(score) if score.is_integer() else score,
                "severity": (
                    "critical" if score >= 80
                    else "high" if score >= 60
                    else "medium" if score >= 30
                    else "low"
                ),
                "confidence": engine_analysis.get("confidence", 0.0),
                "reasons": [],
            }
        else:
            risk = self.risk_adapter.calculate(
                alert,
                {"ioc": {"ioc_count": ioc_count}, "mitre": mitre},
            )
        if engine_analysis.get("confidence") is not None:
            confidence_data["score"] = engine_analysis["confidence"]
        if engine_analysis.get("recommendations"):
            recommendations.extend(engine_analysis["recommendations"])
        if engine_analysis.get("findings"):
            findings.extend(engine_analysis["findings"])
        attack_story = engine_analysis.get("attack_story") or self.attack_story_builder.build(
            {"ioc": {"ioc_count": ioc_count}, "mitre": mitre}
        )
        normalized_intelligence = InvestigationIntelligence(
            findings=findings,
            recommendations=list(dict.fromkeys(recommendations)),
            risk_score=risk.get("score", 0),
            risk_severity=risk.get("severity", "unknown"),
            confidence=confidence_data["score"],
            mitre_techniques=mitre.get("techniques", []),
            attack_story=attack_story,
            iocs=engine_analysis.get("iocs", []),
            evidence_summary={"count": len(normalized_artifacts)},
            timeline=[],
            metadata={"case_id": case_id},
        )
        normalized_intelligence.timeline = self.timeline_engine.generate(
            normalized_intelligence.to_dict(), alert
        )
        self.intelligence_repository.save(case_id, normalized_intelligence)
        report = self.report_generator.generate(
            case_id,
            normalized_intelligence,
            alert,
            normalized_intelligence.timeline,
        )
        self.report_repository.save(report)
        aggregate = self.finding_aggregator.aggregate(
            {"case_id": case_id, "artifacts": normalized_artifacts},
            intelligence,
            {},
            confidence_data,
        )
        findings.extend(aggregate.get("findings", []))
        reasoning_report = self.evidence_reasoner.reason(
            self.create_context(
                investigation_id=case_id,
                artifacts=normalized_artifacts,
                evidence=[item for item in normalized_artifacts if isinstance(item, dict)] + list(engine_analysis.get("evidence", []) or []),
                iocs=list(engine_analysis.get("iocs", []) or []),
                timeline=list(normalized_intelligence.timeline or []),
            ),
            plan,
        )
        result = InvestigationResult(
            success=True,
            status="completed",
            message="Investigation completed.",
            case_id=case_id,
            plan=plan,
            plan_name=plan.plan_name,
            execution=execution,
            results=list(execution["results"]),
            artifacts=normalized_artifacts,
            findings=findings,
            recommendations=list(dict.fromkeys(recommendations)),
            risk=risk,
            confidence=confidence_data["score"],
            mitre=mitre.get("techniques", []),
            attack_story=attack_story,
            intelligence={
                "normalized": normalized_intelligence.to_dict(),
                "timeline": normalized_intelligence.timeline,
                "report": report.to_dict(),
                "agents": intelligence,
                "workflow": workflow,
            },
            reasoning_report=reasoning_report,
            errors=list(execution["errors"]),
        )
        try:
            memory = self.memory_service.store_investigation_memory(
                self.create_context(case_id, normalized_artifacts, evidence=normalized_artifacts,
                                    iocs=list(engine_analysis.get("iocs", []) or []),
                                    timeline=list(normalized_intelligence.timeline or [])),
                reasoning_report,
                result,
            )
            result.memory_reference = memory.memory_id
        except Exception:
            # Memory is post-completion enrichment and must never block execution.
            result.metadata["memory_storage_error"] = True
        return result

    def get_report_by_case_id(self, case_id: str) -> dict[str, Any] | None:
        return self.report_repository.get_by_case_id(case_id)


    def investigate(
        self,
        case_id: str,
        alert: Optional[dict[str, Any]] = None,
        artifacts: Optional[list[dict[str, Any]]] = None,
        evidence: Optional[list[dict[str, Any]]] = None,
        iocs: Optional[list[dict[str, Any]]] = None,
        timeline: Optional[list[dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> InvestigationResult:
        started_at = time.perf_counter()
        observer = ObservabilityService()
        observer.event("INVESTIGATION_STARTED", case_id=case_id, status="started")
        alert_data = dict(
            alert or {}
        )

        alert_data["case_id"] = case_id


        normalized_artifacts = []

        for item in artifacts or []:

            if isinstance(item, dict):

                normalized_artifacts.append(
                    dict(item)
                )

            else:

                normalized_artifacts.append(
                    {
                        "type": "unknown",
                        "value": item,
                    }
                )


        if not normalized_artifacts:

            normalized_artifacts.append(
                {
                    "type": "alert",
                    "value": alert_data,
                }
            )

        plan = self.create_plan(
            case_id,
            alert_data,
        )


        context = self.create_context(
            investigation_id=alert_data.get(
                "investigation_id",
                case_id,
            ),
            artifacts=normalized_artifacts,
            evidence=evidence,
            iocs=iocs,
            timeline=timeline,
        )

        orchestrator_kwargs = dict(kwargs)
        orchestrator_kwargs["context"] = context
        workflow = self.orchestrator.investigate(
            case_id=case_id,
            artifacts=normalized_artifacts,
            alert=alert_data,
            **orchestrator_kwargs,
        )


        capabilities = self._get_plan_capabilities(
            plan
        )


        execution = {
            "case_id": case_id,
            "status": "pending",
            "capabilities": capabilities,
            "results": [],
            "errors": [],
            "tasks": [],
            "workflow": workflow,
        }


        # ----------------------------------------------------
        # Runtime validation
        # ----------------------------------------------------


        if self.runtime is None:

            return InvestigationResult(
                success=False,
                status="failed",
                message="Runtime task executor is not configured.",
                error="Runtime task executor is not configured.",
                case_id=case_id,
                plan=plan,
                plan_name=plan.plan_name,
                execution=execution,
                results=[],
                artifacts=normalized_artifacts,
                findings=[],
                intelligence={
                    "workflow": workflow,
                },
                errors=[
                    "Runtime task executor is not configured."
                ],
            )


        missing = self._validate_capabilities(
            capabilities
        )


        if missing:

            error_message = (
                "Missing runtime capabilities: "
                + ", ".join(missing)
            )

            return InvestigationResult(
                success=False,
                status="failed",
                message="Missing runtime capabilities.",
                error=error_message,
                case_id=case_id,
                plan=plan,
                plan_name=plan.plan_name,
                execution=execution,
                results=[],
                artifacts=normalized_artifacts,
                findings=[],
                intelligence={
                    "workflow": workflow,
                },
                errors=[
                    error_message
                ],
            )


        # ----------------------------------------------------
        # Execute capabilities
        # ----------------------------------------------------


        for capability in capabilities:

            task = self._create_runtime_task(
                case_id=case_id,
                alert=alert_data,
                plan=plan,
                capability=capability,
                context=context,
            )


            try:

                result = self.runtime.execute(
                    task
                )


                execution["results"].append(
                    {
                        "capability": capability,
                        "task_id": task.task_id,
                        "result": result,
                    }
                )


            except Exception as exc:

                execution["errors"].append(
                    {
                        "capability": capability,
                        "task_id": task.task_id,
                        "error": str(exc),
                    }
                )


            execution["tasks"].append(
                task.to_dict()
            )


        success = not bool(
            execution["errors"]
        )


        execution["status"] = (
            "completed"
            if success
            else "failed"
        )


        if success:
            result = self._build_success_result(
                case_id,
                alert_data,
                plan,
                normalized_artifacts,
                execution,
                workflow,
            )
            observer.event("INTELLIGENCE_GENERATED", case_id=case_id, status=result.status, duration_ms=round((time.perf_counter()-started_at)*1000, 2), agent_metrics={"tasks": len(execution.get("tasks", [])), "errors": len(execution.get("errors", []))})
            return result

        result = InvestigationResult(
            success=False,
            status="failed",
            message="Investigation failed.",
            error=str(execution["errors"]),
            case_id=case_id,
            plan=plan,
            plan_name=plan.plan_name,
            execution=execution,
            results=list(execution["results"]),
            errors=list(execution["errors"]),
            artifacts=normalized_artifacts,
            findings=[],
            intelligence={"workflow": workflow},
        )
        observer.event("INVESTIGATION_STARTED", case_id=case_id, status="failed", duration_ms=round((time.perf_counter()-started_at)*1000, 2), errors=result.errors)
        return result
