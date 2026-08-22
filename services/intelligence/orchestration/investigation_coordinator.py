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

from dataclasses import asdict, dataclass, field, is_dataclass
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
from database.connection import database
from services.observability import ObservabilityService
from services.intelligence.reasoning import EvidenceReasoner
from services.intelligence.memory import MemoryService
from services.intelligence.investigation.analyst_feedback import AnalystFeedback
from services.intelligence.investigation.analyst_feedback_service import AnalystFeedbackService
from services.intelligence.investigation.read_model import InvestigationReadModelBuilder
from services.intelligence.repository.feedback_repository import InvestigationFeedbackRepository
from services.intelligence.repository.execution_repository import InvestigationExecutionRepository
from services.intelligence.repository.collaboration_repository import AnalystCollaborationRepository
from services.intelligence.repository.evidence_review_repository import EvidenceReviewRepository
from services.intelligence.repository.operational_alert_repository import OperationalAlertRepository
from services.intelligence.repository.operational_alert_policy_repository import OperationalAlertPolicyRepository
from services.intelligence.repository.operational_alert_assignment_repository import OperationalAlertAssignmentRepository
from services.intelligence.repository.operations_evaluation_repository import OperationsEvaluationRepository
from services.intelligence.repository.operational_notification_repository import OperationalNotificationRepository
from services.intelligence.repository.operations_notification_rule_repository import OperationsNotificationRuleRepository
from services.intelligence.repository.case_lifecycle_repository import CaseLifecycleRepository
from services.intelligence.reporting.compliance_export import ComplianceExportBuilder
from services.intelligence.feedback.analytics import FeedbackAnalyticsService
from services.intelligence.investigation_quality import InvestigationQualityRepository, InvestigationQualityService
from services.audit.service import AuditService
from services.intelligence.decision.engine import DecisionEngine
from services.intelligence.copilot.copilot_engine import InvestigationCopilot
from services.intelligence.reporting.narrative_engine import InvestigationNarrativeEngine
from services.intelligence.reporting.investigation_report_v2 import InvestigationReportV2Builder, PdfReportRenderer
from services.intelligence.threat_intelligence import ThreatCorrelationEngine
from services.intelligence.fusion import ProviderNeutralFusionEngine
from services.intelligence.investigation.decision import DecisionIntelligenceEngine
from services.intelligence.investigation.attack_sequence import AttackSequenceAnalyzer
from services.intelligence.workspace.explainability_projection import ExplainabilityProjectionBuilder
from services.intelligence.workspace.evidence_graph import (
    EvidenceGraphProjectionBuilder,
    EvidenceGraphWorkspaceProjectionBuilder,
    EvidenceComparisonProjectionBuilder,
    ContradictionProjectionBuilder,
    InvestigationReportExportBuilder,
    productivity_latencies,
)
from services.intelligence.workflow_v3 import AnalystWorkflowV3Service
import time
from datetime import datetime, timezone
from uuid import uuid4


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

    tenant_id: str | None = None
    actor_id: str | None = None
    correlation_id: str | None = None
    intelligence_provenance: dict[str, Any] = field(default_factory=dict)
    intelligence_evidence: list[dict[str, Any]] = field(default_factory=list)
    _queried_intelligence: list[tuple[str, str, str]] = field(default_factory=list, repr=False)

    def add_evidence(self, evidence: dict[str, Any], tenant_id: str) -> None:
        if tenant_id != self.tenant_id:
            raise PermissionError("evidence tenant does not match investigation tenant")
        self.intelligence_evidence.append(dict(evidence))
        self.evidence.append(dict(evidence))


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
        threat_intelligence_gateway: Any = None,
        provider_neutral_fusion_engine: Any = None,
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
        self.report_repository = InvestigationReportRepository(database)
        self.evidence_reasoner = EvidenceReasoner(
            getattr(runtime, "ai_runtime", None) or getattr(self.orchestrator, "ai_runtime", None)
        )
        self.memory_service = MemoryService()
        self.decision_engine = DecisionEngine()
        self.decision_intelligence_engine = DecisionIntelligenceEngine()
        self.attack_sequence_analyzer = AttackSequenceAnalyzer()
        self.copilot = InvestigationCopilot(getattr(self.orchestrator, "ai_runtime", None))
        self.narrative_engine = InvestigationNarrativeEngine(getattr(self.orchestrator, "ai_runtime", None))
        self.threat_intelligence = ThreatCorrelationEngine()
        self.threat_intelligence_gateway = threat_intelligence_gateway
        self.provider_neutral_fusion_engine = (
            provider_neutral_fusion_engine
            if provider_neutral_fusion_engine is not None
            else ProviderNeutralFusionEngine()
        )
        self.feedback_repository = InvestigationFeedbackRepository(database)
        self.execution_repository = InvestigationExecutionRepository(database)
        self.collaboration_repository = AnalystCollaborationRepository(database)
        self.evidence_review_repository = EvidenceReviewRepository(database)
        self.case_lifecycle_repository = CaseLifecycleRepository(database)
        self.operational_alert_repository = OperationalAlertRepository(database)
        self.operational_alert_policy_repository = OperationalAlertPolicyRepository(database)
        self.operational_alert_assignment_repository = OperationalAlertAssignmentRepository(database)
        self.operations_evaluation_repository = OperationsEvaluationRepository(database)
        self.operational_notification_repository = OperationalNotificationRepository(database)
        self.operations_notification_rule_repository = OperationsNotificationRuleRepository(database)
        self.assignment_directory = None
        self.audit_service = AuditService(database)
        self.compliance_export_builder = ComplianceExportBuilder()
        self.feedback_service = AnalystFeedbackService(self.feedback_repository, AuditService(database))
        self.feedback_analytics = FeedbackAnalyticsService(self.feedback_repository)
        self.investigation_quality_repository = InvestigationQualityRepository(database)
        self.investigation_read_model_builder = InvestigationReadModelBuilder(
            self.report_repository,
            self.intelligence_repository,
            self.investigation_quality_repository,
            self.feedback_repository,
        )
        self.explainability_projection = ExplainabilityProjectionBuilder()
        self.evidence_graph_projection = EvidenceGraphProjectionBuilder()
        self.evidence_graph_workspace_projection = EvidenceGraphWorkspaceProjectionBuilder()
        self.evidence_comparison_projection = EvidenceComparisonProjectionBuilder()
        self.contradiction_projection = ContradictionProjectionBuilder()
        self.report_export_projection = InvestigationReportExportBuilder()
        self.report_v2_projection = InvestigationReportV2Builder()
        self.pdf_report_renderer = PdfReportRenderer()
        self.analyst_workflow_v3 = AnalystWorkflowV3Service(self)


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
        tenant_id: str | None = None,
        intelligence_provenance: Optional[dict[str, Any]] = None,
        correlation_id: str | None = None,
    ) -> InvestigationContext:

        return InvestigationContext(
            investigation_id=investigation_id,
            artifacts=list(artifacts),
            evidence=list(evidence or []),
            iocs=list(iocs or []),
            timeline=list(timeline or []),
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            intelligence_provenance=dict(intelligence_provenance or {}),
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

    @staticmethod
    def _normalize_intelligence_gateway_result(result: Any) -> dict[str, Any]:
        """Preserve provider outcomes without turning them into findings."""
        provider_results = []
        observations = []
        statuses = set()
        dispositions = set()
        for provider_result in getattr(result, "provider_results", ()):
            provider = getattr(getattr(provider_result, "provider", None), "name", None)
            observation = getattr(provider_result, "observation", None)
            error = getattr(provider_result, "error", None)
            item = {"provider": provider, "observation": observation, "error": error}
            if is_dataclass(observation):
                item["observation"] = asdict(observation)
            if is_dataclass(error):
                item["error"] = asdict(error)
            provider_results.append(item)
            if error is not None:
                code = getattr(getattr(error, "code", None), "value", getattr(error, "code", "unavailable"))
                statuses.add("invalid" if code == "normalization_error" else "unavailable")
            if observation is not None:
                observations.append(asdict(observation) if is_dataclass(observation) else dict(getattr(observation, "__dict__", {})))
                if getattr(observation, "stale", False):
                    statuses.add("stale")
                reputation = str(getattr(observation, "reputation", "") or "").lower()
                if reputation in {"malicious", "high_risk", "suspicious"}:
                    dispositions.add("supporting")
                elif reputation in {"benign", "clean", "low_risk"}:
                    dispositions.add("contradicting")
        if len(dispositions) > 1:
            disposition = "mixed"
        elif dispositions:
            disposition = next(iter(dispositions))
        elif statuses and not observations:
            disposition = "unavailable"
        else:
            disposition = "neutral" if observations else "unavailable"
        providers = sorted({
            provider
            for provider in (
                item.get("provider")
                for item in provider_results
            )
            if provider
        })
        return {
            "provider_results": provider_results,
            "observations": observations,
            "statuses": sorted(statuses),
            "disposition": disposition,
            "audit": asdict(result.audit) if is_dataclass(getattr(result, "audit", None)) else getattr(result, "audit", None),
            "intelligence_provenance": {
                "providers": providers,
                "status": sorted(statuses),
                "disposition": disposition,
            },
        }

    def _fuse_intelligence_gateway_result(
        self,
        result: Any,
        ioc: Any,
        context: InvestigationContext,
    ) -> dict[str, Any]:
        """Fuse trusted gateway observations without changing their provenance."""
        fusion = self.provider_neutral_fusion_engine.fuse(
            ioc,
            tuple(getattr(result, "observations", ()) or ()),
            context={
                "tenant_id": context.tenant_id,
                "investigation_id": context.investigation_id,
            },
        )
        payload = fusion.to_dict()
        errors: list[dict[str, Any]] = []
        unavailable: set[str] = set(payload.get("unavailable_providers", ()) or ())
        for provider_result in getattr(result, "provider_results", ()) or ():
            error = getattr(provider_result, "error", None)
            if error is None:
                continue
            provider = getattr(getattr(provider_result, "provider", None), "name", None)
            if not provider:
                continue
            unavailable.add(str(provider))
            errors.append({
                "provider": str(provider),
                "error": asdict(error) if is_dataclass(error) else dict(getattr(error, "__dict__", {})),
            })
        if errors:
            payload["provider_errors"] = errors
            payload["unavailable_providers"] = sorted(unavailable)
        if context.correlation_id:
            payload["correlation_id"] = context.correlation_id
        return payload

    @staticmethod
    def _merge_intelligence_metadata(
        current: dict[str, Any],
        incoming: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge per-IOC metadata deterministically while retaining legacy keys."""
        if not current:
            merged = dict(incoming)
            if incoming.get("fusion") is not None:
                merged["fusion_results"] = [incoming["fusion"]]
            return merged
        merged = dict(current)
        for key in ("provider_results", "observations"):
            merged[key] = list(current.get(key, ()) or ()) + list(incoming.get(key, ()) or ())
        audits = list(current.get("audits", ()) or ())
        if current.get("audit") is not None and not audits:
            audits.append(current["audit"])
        if incoming.get("audit") is not None:
            audits.append(incoming["audit"])
        if audits:
            merged["audits"] = audits
        fusion_results = list(current.get("fusion_results", ()) or ())
        if not fusion_results and current.get("fusion") is not None:
            fusion_results.append(current["fusion"])
        if incoming.get("fusion") is not None:
            fusion_results.append(incoming["fusion"])
        if fusion_results:
            merged["fusion_results"] = fusion_results
        statuses = sorted(set(current.get("statuses", ()) or ()) | set(incoming.get("statuses", ()) or ()))
        merged["statuses"] = statuses
        current_provenance = current.get("intelligence_provenance", {}) or {}
        incoming_provenance = incoming.get("intelligence_provenance", {}) or {}
        providers = sorted(set(current_provenance.get("providers", ()) or ()) | set(incoming_provenance.get("providers", ()) or ()))
        dispositions = {
            value for value in (
                current_provenance.get("disposition"),
                incoming_provenance.get("disposition"),
            ) if value and value != "unavailable"
        }
        if len(dispositions) > 1:
            disposition = "mixed"
        elif dispositions:
            disposition = next(iter(dispositions))
        else:
            disposition = "unavailable"
        merged["disposition"] = disposition
        merged["intelligence_provenance"] = {
            "providers": providers,
            "status": statuses,
            "disposition": disposition,
        }
        return merged

    def _build_success_result(
        self,
        case_id: str,
        alert: dict[str, Any],
        plan: InvestigationPlan,
        normalized_artifacts: list[dict[str, Any]],
        execution: dict[str, Any],
        workflow: Any,
        tenant_context: dict[str, Any] | None = None,
        intelligence_metadata: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        owned_evidence: Optional[list[dict[str, Any]]] = None,
        source_timeline: Optional[list[dict[str, Any]]] = None,
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
            metadata={
                "case_id": case_id,
                **(
                    {"tenant_id": (tenant_context or {}).get("tenant_id")}
                    if (tenant_context or {}).get("tenant_id")
                    else {}
                ),
                **({"correlation_id": correlation_id} if correlation_id else {}),
            },
        )
        normalized_intelligence.metadata["intelligence_status"] = dict(intelligence_metadata or {})
        normalized_intelligence.timeline = self.timeline_engine.generate(
            normalized_intelligence.to_dict(), alert
        )
        scoped_tenant_id = (tenant_context or {}).get("tenant_id")
        if scoped_tenant_id:
            save_intelligence_for_tenant = getattr(self.intelligence_repository, "save_for_tenant", None)
            if callable(save_intelligence_for_tenant):
                save_intelligence_for_tenant(case_id, scoped_tenant_id, normalized_intelligence)
            else:
                self.intelligence_repository.save(case_id, normalized_intelligence)
        else:
            self.intelligence_repository.save(case_id, normalized_intelligence)
        report = self.report_generator.generate(
            case_id,
            normalized_intelligence,
            alert,
            normalized_intelligence.timeline,
        )
        report.tenant_context = dict(tenant_context or {}) if scoped_tenant_id else None
        if scoped_tenant_id:
            save_report_for_tenant = getattr(self.report_repository, "save_for_tenant", None)
            if callable(save_report_for_tenant):
                save_report_for_tenant(scoped_tenant_id, report)
            else:
                self.report_repository.save(report)
        else:
            self.report_repository.save(report)
        aggregate = self.finding_aggregator.aggregate(
            {"case_id": case_id, "artifacts": normalized_artifacts},
            intelligence,
            {},
            confidence_data,
        )
        findings.extend(aggregate.get("findings", []))
        evidence_for_reasoning = (
            list(owned_evidence or [])
            if scoped_tenant_id
            else list(normalized_artifacts) + list(engine_analysis.get("evidence", []) or [])
        )
        reasoning_report = self.evidence_reasoner.reason(
            self.create_context(
                investigation_id=case_id,
                artifacts=normalized_artifacts,
                evidence=evidence_for_reasoning,
                iocs=list(engine_analysis.get("iocs", []) or []),
                timeline=list(normalized_intelligence.timeline or []),
                tenant_id=(tenant_context or {}).get("tenant_id"),
                intelligence_provenance=intelligence_metadata.get("intelligence_provenance", {}),
                correlation_id=correlation_id,
            ),
            plan,
        )
        for finding in reasoning_report.findings:
            normalized_finding = finding.to_dict() if hasattr(finding, "to_dict") else dict(finding)
            if normalized_finding not in findings:
                findings.append(normalized_finding)
        threat_report = None
        try:
            threat_report = self.threat_intelligence.correlate_case(
                self.create_context(case_id, normalized_artifacts, evidence=evidence_for_reasoning,
                                    iocs=list(engine_analysis.get("iocs", []) or []),
                                    timeline=list(normalized_intelligence.timeline or []),
                                    tenant_id=scoped_tenant_id),
                evidence_for_reasoning, list(engine_analysis.get("iocs", []) or []), None)
        except Exception:
            pass
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
            threat_intelligence_report=threat_report,
            tenant_context=tenant_context,
            metadata={
                "actor_id": (tenant_context or {}).get("actor_id"),
                **({"correlation_id": correlation_id} if correlation_id else {}),
            },
            errors=list(execution["errors"]),
        )
        # Phase 18.1 additive contract: preserve the legacy decision report and
        # attach a deterministic, evidence-backed decision result as well.
        result.decision_intelligence = self.decision_intelligence_engine.evaluate(
            result, tenant_id=scoped_tenant_id
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
        result.decision_report = self.decision_engine.decide(
            result, reasoning_report, result.memory_reference
        )
        # Phase 18.2 additive contract: only source-backed timeline data is
        # eligible for reconstruction.  The legacy presentation timeline is
        # intentionally not passed as evidence.
        result.attack_sequence = self.attack_sequence_analyzer.analyze(
            result,
            tenant_id=scoped_tenant_id,
            timeline=source_timeline,
            evidence=evidence_for_reasoning,
            iocs=list(engine_analysis.get("iocs", []) or []),
            fusion=list((intelligence_metadata or {}).get("fusion_results", []) or []),
        )
        quality_assessment = None
        try:
            quality_assessment = InvestigationQualityService(tenant_id=scoped_tenant_id, repository=self.investigation_quality_repository).assess_investigation(str(result.investigation_id or case_id), result)
            result.metadata["quality_assessment_id"] = quality_assessment.quality_id
            result.metadata["quality_status"] = quality_assessment.quality_status
            quality_data = quality_assessment.to_dict()
            result.metadata["quality_assessment"] = quality_data
            result.intelligence["quality_assessment"] = quality_data
        except Exception as exc:
            result.metadata["quality_assessment_error"] = type(exc).__name__
        try:
            result.copilot_summary = self.copilot.summarize_investigation(
                self.create_context(case_id, normalized_artifacts, evidence=normalized_artifacts,
                                    iocs=list(engine_analysis.get("iocs", []) or []),
                                    timeline=list(normalized_intelligence.timeline or [])),
                result, reasoning_report, result.decision_report, result.memory_reference
            )
        except Exception:
            result.metadata["copilot_error"] = True
        try:
            result.narrative_report = self.narrative_engine.generate_report(
                self.create_context(case_id, normalized_artifacts, evidence=normalized_artifacts,
                                    iocs=list(engine_analysis.get("iocs", []) or []),
                                    timeline=list(normalized_intelligence.timeline or [])),
                result, reasoning_report, result.decision_report, result.copilot_summary, result.memory_reference)
        except Exception:
            result.metadata["narrative_error"] = True
        analyst_report = self.report_generator.generate_from_result(result)
        if scoped_tenant_id:
            save_for_tenant = getattr(self.report_repository, "save_for_tenant", None)
            if callable(save_for_tenant):
                save_for_tenant(scoped_tenant_id, analyst_report)
            else:
                self.report_repository.save(analyst_report)
        else:
            self.report_repository.save(analyst_report)
        try:
            if quality_assessment is None:
                quality_assessment = InvestigationQualityService(tenant_id=scoped_tenant_id, repository=self.investigation_quality_repository).assess_investigation(str(result.investigation_id or case_id), result)
            quality_data = quality_assessment.to_dict()
            result.metadata["quality_assessment_id"] = quality_assessment.quality_id
            result.metadata["quality_status"] = quality_assessment.quality_status
            result.intelligence["quality_assessment"] = quality_data
            analyst_report.quality_assessment = quality_data
            if scoped_tenant_id and callable(getattr(self.report_repository, "save_for_tenant", None)):
                self.report_repository.save_for_tenant(scoped_tenant_id, analyst_report)
            else:
                self.report_repository.save(analyst_report)
        except Exception as exc:
            result.metadata["quality_assessment_error"] = type(exc).__name__
            try:
                ObservabilityService().event("investigation_quality_assessment_failed", investigation_id=str(result.investigation_id or case_id), case_id=case_id, tenant_id=scoped_tenant_id, error_type=type(exc).__name__, status="failed")
            except Exception:
                pass
        result.intelligence["report"] = analyst_report.to_dict()
        return result

    def get_quality_assessment(self, investigation_id: str, security_context: Any):
        tenant_id = getattr(security_context, "tenant_id", None)
        if not tenant_id: raise PermissionError("investigation tenant authorization is required")
        report = self.get_report_by_case_id(str(investigation_id), str(tenant_id))
        if report is None: return None
        report_investigation_id = str((report.get("metadata") or {}).get("investigation_id") if isinstance(report.get("metadata"), dict) else "").strip() or str(report.get("investigation_id") or investigation_id)
        assessment = self.investigation_quality_repository.get_assessment(str(tenant_id), report_investigation_id)
        return assessment.to_dict() if assessment else None

    def get_investigation_view(self, case_id: str, security_context: Any) -> dict[str, Any] | None:
        tenant_id = getattr(security_context, "tenant_id", None)
        if not tenant_id:
            raise PermissionError("investigation tenant authorization is required")
        view = self.investigation_read_model_builder.build(str(case_id), str(tenant_id))
        payload = view.to_dict() if view else None
        if payload:
            quality = payload.get("quality") or {}
            ObservabilityService().event(
                "investigation_view_retrieved",
                investigation_id=payload.get("investigation", {}).get("id"),
                case_id=str(case_id),
                tenant_id=str(tenant_id),
                status=payload.get("investigation", {}).get("status"),
                quality_score=quality.get("overall_score"),
            )
        return payload

    def get_investigation_metrics(self, case_id: str, security_context: Any) -> dict[str, Any] | None:
        view = self.get_investigation_view(case_id, security_context)
        if view is None:
            return None
        tenant_id = str(getattr(security_context, "tenant_id", ""))
        investigation_id = str(view["investigation"]["id"])
        analytics = self.feedback_analytics.summarize(tenant_id, investigation_id=investigation_id)
        rates = analytics.rates
        return {
            "case_id": str(case_id),
            "investigation_id": investigation_id,
            "acceptance_rate": rates.get("accepted_rate", 0.0),
            "false_positive_rate": rates.get("false_positive_rate", 0.0),
            "modification_rate": rates.get("modified_rate", 0.0),
            "escalation_rate": rates.get("escalated_rate", 0.0),
            "feedback_count": analytics.total_feedback_events,
            "advisory_only": True,
        }

    def get_report_by_case_id(self, case_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
        if tenant_id:
            scoped = getattr(self.report_repository, "get_by_case_id_for_tenant", None)
            if callable(scoped):
                return scoped(case_id, tenant_id)
            report = self.report_repository.get_by_case_id(case_id)
            context = report.get("tenant_context") if isinstance(report, dict) else {}
            metadata = report.get("metadata") if isinstance(report, dict) else {}
            report_tenant = context.get("tenant_id") if isinstance(context, dict) else None
            report_tenant = report_tenant or (metadata.get("tenant_id") if isinstance(metadata, dict) else None)
            return report if report_tenant == tenant_id else None
        return self.report_repository.get_by_case_id(case_id)

    def get_workspace_snapshot(self, tenant_id: str) -> dict[str, Any]:
        """Build the analyst entry projection from the canonical V1 repositories."""
        if not tenant_id:
            raise PermissionError("investigation tenant authorization is required")
        intelligence = {
            item["case_id"]: item
            for item in self.intelligence_repository.list_for_tenant(str(tenant_id))
        }
        reports = {
            item.get("case_id"): item
            for item in self.report_repository.list_for_tenant(str(tenant_id))
            if isinstance(item, dict) and item.get("case_id")
        }
        investigations = []
        alerts = []
        for case_id in sorted(set(intelligence) | set(reports)):
            result = intelligence.get(case_id) or {}
            report = reports.get(case_id) or {}
            evidence = report.get("evidence") or result.get("evidence") or result.get("artifacts") or []
            iocs = report.get("iocs") or result.get("iocs") or []
            risk = report.get("risk") if isinstance(report.get("risk"), dict) else {}
            score = risk.get("score", report.get("risk_score", result.get("risk_score", 0)))
            confidence = report.get("confidence", result.get("confidence", 0))
            investigations.append({
                "case_id": case_id,
                "title": report.get("title") or report.get("summary") or case_id,
                "status": str(report.get("status") or result.get("status") or "unknown").lower(),
                "risk_score": score,
                "risk_severity": risk.get("severity") or report.get("severity") or result.get("risk_severity", "unknown"),
                "ai_confidence": confidence,
                "evidence_count": len(evidence) if isinstance(evidence, (list, tuple)) else 0,
                "ioc_count": len(iocs) if isinstance(iocs, (list, tuple)) else 0,
            })
            timeline = report.get("timeline") or result.get("timeline") or []
            for event in timeline if isinstance(timeline, list) else []:
                if isinstance(event, dict) and str(event.get("type") or event.get("event_type") or "").lower() == "alert":
                    alerts.append({"case_id": case_id, "description": event.get("description") or event.get("summary") or "Alert observed", "created_at": event.get("created_at") or event.get("created")})
        active_statuses = {"open", "active", "investigating", "in_progress", "pending", "queued"}
        return {"investigations": investigations, "active_investigations": [item for item in investigations if item["status"] in active_statuses], "recent_alerts": alerts[-10:]}

    def submit_feedback(self, case_id: str, payload: dict[str, Any], *, tenant_id: str, analyst_id: str) -> AnalystFeedback:
        report = self.get_report_by_case_id(case_id, tenant_id)
        if report is None:
            raise LookupError("investigation_not_found")
        metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
        investigation_id = str(metadata.get("investigation_id") or report.get("investigation_id") or case_id)
        history = self.feedback_repository.list_for_investigation(str(tenant_id), investigation_id)
        previous_state = history[-1].to_dict().get("disposition") if history else "unassigned"
        feedback = self.feedback_service.record(
            investigation_id=investigation_id,
            case_id=str(case_id),
            tenant_id=str(tenant_id),
            analyst_id=str(analyst_id),
            payload=payload,
            report=report,
            previous_state=previous_state,
        )
        ObservabilityService().event(
            "investigation_feedback_recorded",
            investigation_id=investigation_id,
            case_id=str(case_id),
            tenant_id=str(tenant_id),
            feedback_decision=feedback.decision,
        )
        return feedback

    def add_collaboration_event(self, case_id: str, payload: dict[str, Any], *, tenant_id: str, actor_id: str) -> dict[str, Any]:
        report = self.get_report_by_case_id(case_id, tenant_id)
        if report is None:
            raise LookupError("investigation_not_found")
        evidence_ids = {str(item.get("evidence_id") or item.get("id") or item.get("reference")) for item in (report.get("evidence") or []) if isinstance(item, dict)}
        evidence_id = payload.get("evidence_id")
        if evidence_id and str(evidence_id) not in evidence_ids:
            raise ValueError("evidence_not_found")
        event_kind = str(payload.get("event_kind") or "note").lower()
        if event_kind not in {"note", "comment", "finding_annotation", "ioc_annotation", "reasoning_annotation"}:
            raise ValueError("invalid_collaboration_event")
        metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
        investigation_id = str(metadata.get("investigation_id") or report.get("investigation_id") or case_id)
        event = self.collaboration_repository.append(investigation_id=investigation_id, case_id=case_id, tenant_id=tenant_id, actor_id=actor_id, event_kind=event_kind, content=payload.get("content") or payload.get("note") or "", parent_event_id=payload.get("parent_event_id"), evidence_id=evidence_id, mentions=payload.get("mentions", []))
        AuditService(database).record("ANALYST_COLLABORATION_RECORDED", case_id=str(case_id), user_id=str(actor_id), details={"tenant_id": str(tenant_id), "event_id": event["event_id"], "event_kind": event_kind, "evidence_id": evidence_id})
        return event

    def get_collaboration(self, case_id: str, tenant_id: str) -> list[dict[str, Any]]:
        if self.get_report_by_case_id(case_id, tenant_id) is None:
            raise LookupError("investigation_not_found")
        return self.collaboration_repository.list_for_case(case_id, tenant_id=tenant_id)

    def review_evidence(self, case_id: str, evidence_id: str, new_state: str, reason: str, *, tenant_id: str, actor_id: str, priority="normal", assigned_to=None, review_deadline=None) -> dict[str, Any]:
        report = self.get_report_by_case_id(case_id, tenant_id)
        if report is None:
            raise LookupError("investigation_not_found")
        evidence = report.get("evidence") or report.get("artifacts") or []
        valid = {str(item.get("evidence_id") or item.get("id") or item.get("reference")) for item in evidence if isinstance(item, dict)}
        if str(evidence_id) not in valid:
            raise ValueError("evidence_not_found")
        metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
        investigation_id = str(metadata.get("investigation_id") or report.get("investigation_id") or case_id)
        event = self.evidence_review_repository.append(investigation_id=investigation_id, case_id=case_id, tenant_id=tenant_id, actor_id=actor_id, evidence_id=evidence_id, new_state=new_state, reason=reason, priority=priority, assigned_to=assigned_to, review_deadline=review_deadline)
        AuditService(database).record("EVIDENCE_REVIEW_CHANGED", case_id=str(case_id), user_id=str(actor_id), details={"tenant_id": str(tenant_id), "evidence_id": str(evidence_id), "previous_state": event["previous_state"], "new_state": event["new_state"]})
        return event

    def get_review_queue(self, tenant_id: str, *, states=None, priority=None, assigned_to=None) -> list[dict[str, Any]]:
        items = self.evidence_review_repository.current_queue(tenant_id=str(tenant_id), states=None, priority=None, assigned_to=None)
        if states:
            items = [item for item in items if item.get("new_state") in set(states)]
        if priority:
            items = [item for item in items if item.get("priority") == priority]
        if assigned_to:
            items = [item for item in items if item.get("assigned_to") == assigned_to]
        return items

    def assign_case(self, case_id: str, payload: dict[str, Any], *, tenant_id: str, actor_id: str) -> dict[str, Any]:
        if self.get_report_by_case_id(case_id, tenant_id) is None:
            raise LookupError("investigation_not_found")
        target = str(payload.get("assignee_id") or "").strip()
        assignment_type = str(payload.get("assignment_type") or "case_owner")
        if assignment_type not in {"case_owner", "reviewer", "escalation_owner"} or not target:
            raise ValueError("valid_assignment_required")
        if self.assignment_directory is not None:
            self.assignment_directory.validate_target(tenant_id=str(tenant_id), actor_id=target)
        event = self.case_lifecycle_repository.append(case_id=case_id, investigation_id=case_id, tenant_id=tenant_id, actor_id=actor_id, event_kind="assignment", state=assignment_type, reason=str(payload.get("reason") or ""), details={"assigned_to": target, "assignment_type": assignment_type})
        AuditService(database).record("INVESTIGATION_ASSIGNMENT_CHANGED", case_id=case_id, user_id=actor_id, details={"tenant_id": tenant_id, "assignment_type": assignment_type, "assigned_to": target})
        return event

    def get_assignments(self, case_id: str, tenant_id: str) -> list[dict[str, Any]]:
        if self.get_report_by_case_id(case_id, tenant_id) is None:
            raise LookupError("investigation_not_found")
        return self.case_lifecycle_repository.assignments(case_id, tenant_id=tenant_id)

    def set_sla(self, case_id: str, payload: dict[str, Any], *, tenant_id: str, actor_id: str) -> dict[str, Any]:
        if self.get_report_by_case_id(case_id, tenant_id) is None:
            raise LookupError("investigation_not_found")
        priority = str(payload.get("priority") or "normal")
        if priority not in {"low", "normal", "high", "critical"}:
            raise ValueError("invalid_investigation_priority")
        event = self.case_lifecycle_repository.append(case_id=case_id, investigation_id=case_id, tenant_id=tenant_id, actor_id=actor_id, event_kind="sla", state="overdue" if payload.get("overdue") else "active", reason=str(payload.get("reason") or ""), details={"priority": priority, "response_deadline": payload.get("response_deadline"), "review_deadline": payload.get("review_deadline"), "escalation_status": payload.get("escalation_status", "not_escalated")})
        AuditService(database).record("INVESTIGATION_SLA_RECORDED", case_id=case_id, user_id=actor_id, details={"tenant_id": tenant_id, "priority": priority})
        return event

    def escalate_case(self, case_id: str, payload: dict[str, Any], *, tenant_id: str, actor_id: str) -> dict[str, Any]:
        if self.get_report_by_case_id(case_id, tenant_id) is None:
            raise LookupError("investigation_not_found")
        owner = str(payload.get("escalation_owner") or "").strip()
        if not owner:
            raise ValueError("escalation_owner_required")
        event = self.case_lifecycle_repository.append(case_id=case_id, investigation_id=case_id, tenant_id=tenant_id, actor_id=actor_id, event_kind="escalation", state="escalated", reason=str(payload.get("reason") or ""), details={"escalation_owner": owner, "status": "open"})
        AuditService(database).record("INVESTIGATION_ESCALATED", case_id=case_id, user_id=actor_id, details={"tenant_id": tenant_id, "escalation_owner": owner})
        return event

    def get_evidence_reviews(self, case_id: str, tenant_id: str) -> list[dict[str, Any]]:
        if self.get_report_by_case_id(case_id, tenant_id) is None:
            raise LookupError("investigation_not_found")
        return self.evidence_review_repository.list_for_case(case_id, tenant_id=tenant_id)

    def change_case_lifecycle(self, case_id: str, state: str, reason: str, *, tenant_id: str, actor_id: str) -> dict[str, Any]:
        allowed_states = {"open", "under_review", "ready_for_closure", "closed", "reopened"}
        if state not in allowed_states:
            raise ValueError("invalid_case_lifecycle_state")
        report = self.get_report_by_case_id(case_id, tenant_id)
        if report is None:
            raise LookupError("investigation_not_found")
        feedback = self.get_feedback(case_id, tenant_id)
        if state == "closed" and not feedback:
            raise ValueError("disposition_required_before_closure")
        previous = self.case_lifecycle_repository.latest(case_id, tenant_id=tenant_id)
        metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
        event = self.case_lifecycle_repository.append(case_id=case_id, investigation_id=str(metadata.get("investigation_id") or case_id), tenant_id=tenant_id, actor_id=actor_id, event_kind="case_reopened" if state == "reopened" else "case_lifecycle", state=state, reason=reason, details={"previous_state": previous.get("state") if previous else "open"})
        AuditService(database).record("INVESTIGATION_LIFECYCLE_CHANGED", case_id=str(case_id), user_id=str(actor_id), details={"tenant_id": str(tenant_id), "previous_state": event["details"].get("previous_state"), "new_state": state, "reason": reason})
        return event

    def approve_report(self, case_id: str, state: str, reason: str, *, tenant_id: str, actor_id: str) -> dict[str, Any]:
        if state not in {"draft", "analyst_reviewed", "approved", "rejected"}:
            raise ValueError("invalid_report_approval_state")
        if self.get_report_by_case_id(case_id, tenant_id) is None:
            raise LookupError("investigation_not_found")
        event = self.case_lifecycle_repository.append(case_id=case_id, investigation_id=case_id, tenant_id=tenant_id, actor_id=actor_id, event_kind="report_approval", state=state, reason=reason, details={"reviewer_id": actor_id})
        AuditService(database).record("INVESTIGATION_REPORT_APPROVAL_CHANGED", case_id=str(case_id), user_id=str(actor_id), details={"tenant_id": str(tenant_id), "state": state, "reason": reason})
        return event

    def get_compliance_export(self, case_id: str, security_context: Any) -> dict[str, Any] | None:
        return self.compliance_export_builder.build(self, case_id, security_context)

    def get_audit_timeline(self, case_id: str, security_context: Any) -> list[dict[str, Any]]:
        tenant_id = getattr(security_context, "tenant_id", None)
        report = self.get_report_by_case_id(case_id, str(tenant_id)) if tenant_id else None
        if not tenant_id or report is None:
            raise LookupError("investigation_not_found")
        report_metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
        investigation_id = str(report_metadata.get("investigation_id") or report.get("investigation_id") or case_id)
        events = []
        for execution in self.execution_repository.list_for_case(case_id, tenant_id=str(tenant_id)):
            events.append({"timestamp": execution.get("started_at"), "event": "investigation_started", "actor_id": execution.get("actor_id"), "execution_id": execution.get("execution_id")})
            if execution.get("evidence_refs"):
                events.append({"timestamp": execution.get("updated_at", execution.get("completed_at")), "event": "evidence_collected", "evidence_refs": execution.get("evidence_refs", [])})
            for provider in execution.get("provider_states", []) or []:
                events.append({"timestamp": provider.get("timestamp", execution.get("completed_at")), "event": "provider_unavailable" if str(provider.get("status", "")).upper() == "UNAVAILABLE" else "intelligence_queried", "provider": provider.get("provider"), "reason": provider.get("unavailable_reason")})
        for item in self.feedback_repository.list_for_investigation(str(tenant_id), investigation_id):
            value = item.to_dict(); events.append({"timestamp": value.get("created_at"), "event": "disposition_changed", "actor_id": value.get("analyst_id"), "previous_state": value.get("metadata", {}).get("previous_state"), "new_state": value.get("disposition"), "evidence_refs": value.get("evidence_refs", [])})
        for item in self.collaboration_repository.list_for_case(case_id, tenant_id=str(tenant_id)):
            events.append({"timestamp": item.get("created_at"), "event": "analyst_" + str(item.get("event_kind")), "actor_id": item.get("actor_id"), "content": item.get("content"), "evidence_id": item.get("evidence_id")})
        for item in self.evidence_review_repository.list_for_case(case_id, tenant_id=str(tenant_id)):
            events.append({"timestamp": item.get("created_at"), "event": "evidence_review_changed", "actor_id": item.get("actor_id"), "evidence_id": item.get("evidence_id"), "previous_state": item.get("previous_state"), "new_state": item.get("new_state"), "reason": item.get("reason")})
        for item in self.case_lifecycle_repository.list_for_case(case_id, tenant_id=str(tenant_id)):
            events.append({"timestamp": item.get("created_at"), "event": item.get("event_kind"), "actor_id": item.get("actor_id"), "state": item.get("state"), "reason": item.get("reason"), "previous_state": item.get("details", {}).get("previous_state")})
        return sorted(events, key=lambda item: str(item.get("timestamp") or ""))

    def get_feedback(self, case_id: str, tenant_id: str) -> list[dict[str, Any]]:
        report = self.get_report_by_case_id(case_id, tenant_id)
        if report is None:
            raise LookupError("investigation_not_found")
        metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
        investigation_id = str(metadata.get("investigation_id") or report.get("investigation_id") or case_id)
        return [item.to_dict() for item in self.feedback_repository.list_for_investigation(tenant_id, investigation_id)]

    def get_feedback_analytics(self, tenant_id: str, **filters: Any) -> dict[str, Any]:
        return self.feedback_analytics.summarize(tenant_id, **filters).to_dict()

    def get_evidence_linked_quality(self, case_id: str, tenant_id: str, **filters: Any) -> dict[str, Any]:
        report = self.get_report_by_case_id(case_id, tenant_id)
        if report is None:
            raise LookupError("investigation_not_found")
        metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
        investigation_id = str(metadata.get("investigation_id") or report.get("investigation_id") or case_id)
        records = self.feedback_repository.list_for_investigation(tenant_id, investigation_id)
        return self.feedback_analytics.evidence_linked_quality(tenant_id, report, records, **filters)

    def _persist_execution_snapshot(self, result: InvestigationResult, *, tenant_id: str, actor_id: str | None = None) -> None:
        """Persist only the analyst-safe operational projection of a result."""
        data = result.to_dict()
        execution = dict(data.get("execution") or {})
        evidence = list(data.get("artifacts") or data.get("evidence") or [])
        evidence_refs = sorted({str(item.get("evidence_id") or item.get("reference") or item.get("id")) for item in evidence if isinstance(item, dict) and (item.get("evidence_id") or item.get("reference") or item.get("id"))})
        intelligence = data.get("intelligence") if isinstance(data.get("intelligence"), dict) else {}
        status = intelligence.get("normalized", {}).get("metadata", {}).get("intelligence_status", {}) if isinstance(intelligence.get("normalized"), dict) else {}
        provider_states = status.get("provider_results") or status.get("observations") or []
        snapshot = {
            **execution,
            "execution_id": data.get("execution_id") or execution.get("execution_id"),
            "investigation_id": data.get("investigation_id") or data.get("case_id"),
            "case_id": data.get("case_id"),
            "status": data.get("status") or execution.get("status"),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "task_states": execution.get("tasks", []),
            "provider_states": provider_states,
            "evidence_refs": evidence_refs,
            "findings": data.get("findings", []),
            "risk": data.get("risk"),
            "decision": data.get("decision_report"),
            "failures": data.get("errors", []),
        }
        saved = self.execution_repository.save(snapshot, tenant_id=str(tenant_id), actor_id=actor_id)
        data["execution_id"] = saved["execution_id"]
        result.execution_id = saved["execution_id"]
        result.execution = {**execution, "execution_id": saved["execution_id"], "started_at": saved.get("started_at"), "completed_at": saved.get("completed_at")}

    def get_evidence_drilldown(self, case_id: str, evidence_id: str, security_context: Any) -> dict[str, Any] | None:
        tenant_id = getattr(security_context, "tenant_id", None)
        if not tenant_id:
            raise PermissionError("investigation tenant authorization is required")
        view = self.get_investigation_view(case_id, security_context)
        if not view:
            return None
        evidence = next((item for item in view.get("evidence", []) if str(item.get("evidence_id") or item.get("id") or item.get("reference")) == str(evidence_id)), None)
        if not evidence:
            return None
        findings = [item for item in view.get("findings", []) if str(evidence_id) in {str(ref) for ref in item.get("evidence_refs", [])}]
        iocs = [item for item in view.get("iocs", []) if str(evidence_id) in {str(ref) for ref in item.get("evidence_refs", item.get("evidence_references", []))}]
        mitre = [item for item in view.get("mitre", []) if str(evidence_id) in {str(ref) for ref in item.get("evidence_refs", item.get("evidence_references", []))}]
        timeline = [item for item in view.get("timeline", []) if str(evidence_id) in {str(ref) for ref in item.get("evidence_refs", item.get("evidence_references", []))}]
        reviews = self.evidence_review_repository.list_for_evidence(case_id, evidence_id, tenant_id=str(tenant_id))
        return {"version": "evidence-drilldown-v1", "case_id": str(case_id), "evidence": evidence, "findings": findings, "reasoning_claims": findings, "iocs": iocs, "mitre": mitre, "timeline_events": timeline, "reviews": reviews, "why_it_matters": [item.get("finding") for item in findings if item.get("finding")], "provenance": evidence.get("provenance", {}), "tenant_id": str(tenant_id)}

    def get_investigation_explainability(self, case_id: str, security_context: Any) -> dict[str, Any] | None:
        tenant_id = getattr(security_context, "tenant_id", None)
        if not tenant_id:
            raise PermissionError("investigation tenant authorization is required")
        view = self.get_investigation_view(case_id, security_context)
        if view is None:
            return None
        timeline = self.get_audit_timeline(case_id, security_context)
        return self.explainability_projection.build(view, audit_timeline=timeline)

    def get_investigation_productivity(self, security_context: Any) -> dict[str, Any]:
        tenant_id = getattr(security_context, "tenant_id", None)
        if not tenant_id:
            raise PermissionError("investigation tenant authorization is required")
        return productivity_latencies(self, str(tenant_id))

    def get_evidence_graph(self, case_id: str, security_context: Any) -> dict[str, Any] | None:
        view = self.get_investigation_view(case_id, security_context)
        if view is None:
            return None
        explainability = self.get_investigation_explainability(case_id, security_context) or {}
        approval = self.case_lifecycle_repository.latest(case_id, tenant_id=str(getattr(security_context, "tenant_id", "")), event_kind="report_approval")
        return self.evidence_graph_projection.build(view, explainability, self.get_audit_timeline(case_id, security_context), approval)

    def compare_evidence(self, case_id: str, evidence_a: str, evidence_b: str, security_context: Any) -> dict[str, Any]:
        view = self.get_investigation_view(case_id, security_context)
        if view is None:
            raise LookupError("investigation_not_found")
        return self.evidence_comparison_projection.build(case_id, view, evidence_a, evidence_b)

    def get_contradictions(self, case_id: str, security_context: Any) -> dict[str, Any]:
        view = self.get_investigation_view(case_id, security_context)
        if view is None:
            raise LookupError("investigation_not_found")
        projection = self.contradiction_projection.build(case_id, self.get_investigation_explainability(case_id, security_context) or {}, view)
        tenant_id = str(getattr(security_context, "tenant_id", ""))
        review_events = {}
        for event in self.case_lifecycle_repository.list_for_case(case_id, tenant_id=tenant_id):
            if event.get("event_kind") != "contradiction_review":
                continue
            contradiction_id = (event.get("details") or {}).get("contradiction_id")
            if contradiction_id:
                review_events[str(contradiction_id)] = event
        for item in projection.get("items", []):
            event = review_events.get(str(item.get("contradiction_id")))
            if event:
                item["analyst_review_state"] = event.get("state", "unreviewed")
                item["review_reason"] = event.get("reason", "")
                item["reviewed_at"] = event.get("created_at")
                item["reviewer_id"] = event.get("actor_id")
        return projection

    def get_report_export(self, case_id: str, security_context: Any) -> dict[str, Any]:
        view = self.get_investigation_view(case_id, security_context)
        if view is None:
            raise LookupError("investigation_not_found")
        tenant_id = str(getattr(security_context, "tenant_id", ""))
        approval = self.case_lifecycle_repository.list_for_case(case_id, tenant_id=tenant_id)
        approval = [item for item in approval if item.get("event_kind") == "report_approval"]
        return self.report_export_projection.build(case_id, view, self.get_investigation_explainability(case_id, security_context) or {}, self.get_evidence_graph(case_id, security_context) or {}, self.get_audit_timeline(case_id, security_context), approval)

    def get_evidence_graph_workspace(self, case_id: str, security_context: Any) -> dict[str, Any] | None:
        graph = self.get_evidence_graph(case_id, security_context)
        if graph is None:
            return None
        return self.evidence_graph_workspace_projection.build(graph, self.get_contradictions(case_id, security_context))

    def get_report_v2(self, case_id: str, security_context: Any) -> dict[str, Any]:
        view = self.get_investigation_view(case_id, security_context)
        if view is None:
            raise LookupError("investigation_not_found")
        tenant_id = str(getattr(security_context, "tenant_id", ""))
        lifecycle = self.case_lifecycle_repository.list_for_case(case_id, tenant_id=tenant_id)
        approvals = [item for item in lifecycle if item.get("event_kind") == "report_approval"]
        explainability = self.get_investigation_explainability(case_id, security_context) or {}
        graph = self.get_evidence_graph(case_id, security_context) or {}
        contradictions = self.get_contradictions(case_id, security_context)
        return self.report_v2_projection.build(case_id, view, explainability, graph, contradictions, self.get_audit_timeline(case_id, security_context), approvals)

    def get_report_v2_pdf(self, case_id: str, security_context: Any) -> bytes:
        return self.pdf_report_renderer.render(self.get_report_v2(case_id, security_context))

    def review_contradiction(self, case_id: str, contradiction_id: str, state: str, reason: str, *, tenant_id: str, actor_id: str) -> dict[str, Any]:
        if state not in {"acknowledged", "reviewed", "resolved", "additional_evidence_requested"}:
            raise ValueError("invalid_contradiction_review_state")
        current = self.get_contradictions(case_id, type("Context", (), {"tenant_id": str(tenant_id)})())
        contradiction = next((item for item in current.get("items", []) if item.get("contradiction_id") == contradiction_id), None)
        if contradiction is None:
            raise LookupError("contradiction_not_found")
        event = self.case_lifecycle_repository.append(case_id=case_id, investigation_id=case_id, tenant_id=str(tenant_id), actor_id=str(actor_id), event_kind="contradiction_review", state=state, reason=reason, details={"contradiction_id": contradiction_id, "previous_state": contradiction.get("analyst_review_state", "unreviewed")})
        AuditService(database).record("INVESTIGATION_CONTRADICTION_REVIEWED", case_id=str(case_id), user_id=str(actor_id), details={"tenant_id": str(tenant_id), "contradiction_id": contradiction_id, "state": state})
        return event

    def compare_execution_projections(self, execution_a: str, execution_b: str, security_context: Any) -> dict[str, Any] | None:
        tenant_id = getattr(security_context, "tenant_id", None)
        if not tenant_id:
            raise PermissionError("execution tenant authorization is required")
        return self.execution_repository.compare(execution_a, execution_b, tenant_id=str(tenant_id))


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
        correlation_id = kwargs.get("correlation_id")
        observer.event(
            "INVESTIGATION_STARTED",
            case_id=case_id,
            status="started",
            **({"correlation_id": correlation_id} if correlation_id else {}),
        )
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


        tenant_id = kwargs.get("tenant_id")
        actor_id = kwargs.get("actor_id")
        owned_evidence: list[dict[str, Any]] = []
        if tenant_id:
            for item in evidence or []:
                if not isinstance(item, dict) or item.get("tenant_id") != tenant_id:
                    raise PermissionError("evidence tenant does not match investigation tenant")
                if not any(item.get(key) for key in ("evidence_id", "artifact_id", "id", "reference")):
                    raise PermissionError("evidence reference is required")
                owned_evidence.append(dict(item))
        context = self.create_context(
            investigation_id=alert_data.get(
                "investigation_id",
                case_id,
            ),
            artifacts=normalized_artifacts,
            evidence=owned_evidence if tenant_id else evidence,
            iocs=iocs,
            timeline=timeline,
            correlation_id=correlation_id,
        )

        context.tenant_id = tenant_id
        context.actor_id = actor_id
        intelligence_metadata: dict[str, Any] = {}
        if self.threat_intelligence_gateway is not None and iocs:
            if not tenant_id or not actor_id:
                observer.event(
                    "THREAT_INTELLIGENCE_AUTHORIZATION_DENIED",
                    case_id=case_id,
                    tenant_id=tenant_id,
                    actor_id=actor_id,
                    reason="tenant and actor context are required for intelligence lookup",
                    **({"correlation_id": correlation_id} if correlation_id else {}),
                )
                raise PermissionError("tenant and actor context are required for intelligence lookup")
            for item in iocs:
                if not isinstance(item, dict) or not item.get("value"):
                    continue
                from app.intelligence.gateway import IOC, IOCType, LookupRequest
                try:
                    ioc_type = IOCType(str(item.get("type", "unknown")).lower())
                except ValueError:
                    ioc_type = IOCType.UNKNOWN
                key = (ioc_type.value, str(item["value"]).strip().lower(), "default")
                if key in context._queried_intelligence:
                    continue
                context._queried_intelligence.append(key)
                ioc = IOC(key[1], ioc_type)
                request = LookupRequest(
                    tenant_id,
                    actor_id,
                    ioc,
                    correlation_id=correlation_id,
                )
                try:
                    result = self.threat_intelligence_gateway.lookup(request)
                except PermissionError:
                    observer.event(
                        "THREAT_INTELLIGENCE_AUTHORIZATION_DENIED",
                        case_id=case_id,
                        tenant_id=tenant_id,
                        actor_id=actor_id,
                        ioc_type=ioc_type.value,
                        reason="gateway authorization denied",
                        **({"correlation_id": correlation_id} if correlation_id else {}),
                    )
                    raise
                normalized_lookup = self._normalize_intelligence_gateway_result(result)
                normalized_lookup["ioc"] = {"value": ioc.value, "type": ioc.type.value}
                normalized_lookup["fusion"] = self._fuse_intelligence_gateway_result(
                    result,
                    ioc,
                    context,
                )
                intelligence_metadata = self._merge_intelligence_metadata(
                    intelligence_metadata,
                    normalized_lookup,
                )
                payload = {"ioc": item, "tenant_id": tenant_id, **normalized_lookup}
                context.add_evidence(payload, tenant_id)

        orchestrator_kwargs = dict(kwargs)
        orchestrator_kwargs.pop("tenant_id", None)
        orchestrator_kwargs.pop("actor_id", None)
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
            "execution_id": f"EXE-{uuid4().hex}",
            "case_id": case_id,
            "investigation_id": alert_data.get("investigation_id", case_id),
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
            "capabilities": capabilities,
            "results": [],
            "errors": [],
            "tasks": [],
            "workflow": workflow,
            "intelligence": intelligence_metadata,
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
                    "status": intelligence_metadata,
                },
                tenant_context={"tenant_id": tenant_id, "actor_id": actor_id},
                metadata={
                    "actor_id": actor_id,
                    **({"correlation_id": kwargs.get("correlation_id")} if kwargs.get("correlation_id") else {}),
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
                    "status": intelligence_metadata,
                },
                tenant_context={"tenant_id": tenant_id, "actor_id": actor_id},
                metadata={
                    "actor_id": actor_id,
                    **({"correlation_id": kwargs.get("correlation_id")} if kwargs.get("correlation_id") else {}),
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
                tenant_context={"tenant_id": tenant_id, "actor_id": actor_id},
                intelligence_metadata=intelligence_metadata,
                correlation_id=correlation_id,
                owned_evidence=owned_evidence,
                source_timeline=context.timeline,
            )
            if tenant_id:
                self._persist_execution_snapshot(result, tenant_id=str(tenant_id), actor_id=actor_id)
            observer.event(
                "INTELLIGENCE_GENERATED",
                case_id=case_id,
                status=result.status,
                duration_ms=round((time.perf_counter()-started_at)*1000, 2),
                agent_metrics={"tasks": len(execution.get("tasks", [])), "errors": len(execution.get("errors", []))},
                **({"correlation_id": correlation_id} if correlation_id else {}),
            )
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
            tenant_context={"tenant_id": tenant_id, "actor_id": actor_id},
            metadata={
                "actor_id": actor_id,
                **({"correlation_id": kwargs.get("correlation_id")} if kwargs.get("correlation_id") else {}),
            },
        )
        if tenant_id:
            self._persist_execution_snapshot(result, tenant_id=str(tenant_id), actor_id=actor_id)
        observer.event(
            "INVESTIGATION_STARTED",
            case_id=case_id,
            status="failed",
            duration_ms=round((time.perf_counter()-started_at)*1000, 2),
            errors=result.errors,
            **({"correlation_id": correlation_id} if correlation_id else {}),
        )
        return result
