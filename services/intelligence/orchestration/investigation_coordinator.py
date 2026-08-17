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
from services.intelligence.repository.feedback_repository import InvestigationFeedbackRepository
from services.intelligence.feedback.analytics import FeedbackAnalyticsService
from services.intelligence.decision.engine import DecisionEngine
from services.intelligence.copilot.copilot_engine import InvestigationCopilot
from services.intelligence.reporting.narrative_engine import InvestigationNarrativeEngine
from services.intelligence.threat_intelligence import ThreatCorrelationEngine
from services.intelligence.fusion import ProviderNeutralFusionEngine
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
        self.feedback_analytics = FeedbackAnalyticsService(self.feedback_repository)


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
<<<<<<< HEAD
        owned_evidence: Optional[list[dict[str, Any]]] = None,
=======
>>>>>>> 71a3dc4 (ops: harden production runtime for investigator v2)
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
        result.intelligence["report"] = analyst_report.to_dict()
        return result

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

    def submit_feedback(self, case_id: str, payload: dict[str, Any], *, tenant_id: str, analyst_id: str) -> AnalystFeedback:
        report = self.get_report_by_case_id(case_id, tenant_id)
        if report is None:
            raise LookupError("investigation_not_found")
        if not isinstance(payload, dict):
            raise ValueError("malformed_payload")
        allowed = {"decision", "reason", "finding_id", "recommendation_id"}
        if set(payload) - allowed:
            raise ValueError("invalid_feedback_fields")
        metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
        investigation_id = str(metadata.get("investigation_id") or report.get("investigation_id") or case_id)
        finding_id = payload.get("finding_id")
        if finding_id:
            finding_ids = {str(item.get("finding_id")) for item in report.get("findings", []) or [] if isinstance(item, dict) and item.get("finding_id")}
            if str(finding_id) not in finding_ids:
                raise ValueError("finding_not_found")
        recommendation_id = payload.get("recommendation_id")
        return self.feedback_repository.save(AnalystFeedback(
            investigation_id=investigation_id, case_id=str(case_id), decision=payload.get("decision", ""),
            analyst_id=analyst_id, finding_id=str(finding_id) if finding_id else None,
            recommendation_id=str(recommendation_id) if recommendation_id else None,
            reason=payload.get("reason", ""), tenant_id=tenant_id,
        ))

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
            "case_id": case_id,
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
<<<<<<< HEAD
                owned_evidence=owned_evidence,
=======
>>>>>>> 71a3dc4 (ops: harden production runtime for investigator v2)
            )
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
        observer.event(
            "INVESTIGATION_STARTED",
            case_id=case_id,
            status="failed",
            duration_ms=round((time.perf_counter()-started_at)*1000, 2),
            errors=result.errors,
            **({"correlation_id": correlation_id} if correlation_id else {}),
        )
        return result
