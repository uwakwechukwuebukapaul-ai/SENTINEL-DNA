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
import hashlib
import json


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
from services.intelligence.feedback.analytics import FeedbackAnalyticsService
from services.intelligence.investigation_quality import InvestigationQualityRepository, InvestigationQualityService
from services.audit.service import AuditService
from services.intelligence.decision.engine import DecisionEngine
from services.intelligence.copilot.copilot_engine import InvestigationCopilot
from services.intelligence.reporting.narrative_engine import InvestigationNarrativeEngine
from services.intelligence.threat_intelligence import ThreatCorrelationEngine
from services.intelligence.fusion import ProviderNeutralFusionEngine
from services.intelligence.investigation.evidence import EvidenceIntelligenceEngine
from services.intelligence.reporting.investigation_projection import InvestigationProjectionBuilder
from services.intelligence.repository.execution_repository import ExecutionEnvelope, ExecutionRepository
from services.intelligence.reporting.execution_projection import ExecutionProjectionBuilder
import time
from datetime import datetime, timezone
from uuid import uuid4


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        execution_repository: Any = None,
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
        self.evidence_engine = EvidenceIntelligenceEngine()
        self.projection_builder = InvestigationProjectionBuilder()
        self.execution_repository = execution_repository or ExecutionRepository()
        self.execution_projection_builder = ExecutionProjectionBuilder()
        if self.runtime is not None and callable(getattr(self.runtime, "register", None)) and not self.runtime.available("evidence_collection"):
            self.runtime.register("evidence_collection", self._execute_evidence_collection)
        self.feedback_repository = InvestigationFeedbackRepository(database)
        self.feedback_service = AnalystFeedbackService(self.feedback_repository, AuditService(database))
        self.feedback_analytics = FeedbackAnalyticsService(self.feedback_repository)
        self.investigation_quality_repository = InvestigationQualityRepository(database)
        self.investigation_read_model_builder = InvestigationReadModelBuilder(
            self.report_repository,
            self.intelligence_repository,
            self.investigation_quality_repository,
            self.feedback_repository,
        )


    # ========================================================
    # Context
    # ========================================================

    def _persist_execution(self, execution: dict[str, Any], *, tenant_id: str | None, actor_id: str | None, investigation_id: str, alert: dict[str, Any], evidence: list[dict[str, Any]], create: bool = False) -> None:
        """Persist only operational references; raw alert/provider payloads stay out of this store."""
        if not tenant_id:
            return
        envelope = ExecutionEnvelope(
            execution_id=str(execution.get("execution_id") or investigation_id),
            tenant_id=str(tenant_id),
            actor_id=str(actor_id) if actor_id else None,
            investigation_id=str(investigation_id),
            alert_reference=str(alert.get("alert_id") or alert.get("reference") or execution.get("case_id") or investigation_id),
            status=str(execution.get("status") or "PENDING").upper(),
            task_states=[{
                "task_id": item.get("task_id"),
                "execution_id": item.get("execution_id"),
                "capability": item.get("capability"),
                "state": str(item.get("execution_state") or item.get("execution_status") or "PENDING").upper(),
                "created_at": item.get("created_at"),
                "started_at": item.get("started_at"),
                "completed_at": item.get("completed_at"),
                "attempt": item.get("attempt", 0),
            } for item in execution.get("tasks", []) if isinstance(item, dict)],
            provider_states=list(execution.get("provider_health", []) or []),
            evidence_references=[str(item.get("evidence_id")) for item in evidence if item.get("evidence_id")],
            started_at=str(execution.get("started_at") or _utc_iso()),
            completed_at=str(execution.get("completed_at")) if execution.get("completed_at") else None,
            failures=[{
                "capability": item.get("capability"),
                "task_id": item.get("task_id"),
                "status": item.get("status"),
                "error_code": item.get("error_code"),
                "error": str(item.get("error") or "")[:256],
            } for item in execution.get("errors", []) if isinstance(item, dict)],
            unavailable_reasons=[{
                "service": item.get("capability") or item.get("service"),
                "reason": str(item.get("error") or item.get("reason") or "Unavailable")[:256],
            } for item in execution.get("errors", []) if isinstance(item, dict) and str(item.get("status", "")).lower() in {"unavailable", "blocked"}],
            created_at=str(execution.get("created_at") or execution.get("started_at") or _utc_iso()),
            queued_at=str(execution.get("queued_at") or execution.get("started_at") or _utc_iso()),
            correlation_id=str(execution.get("correlation_id")) if execution.get("correlation_id") else None,
            state_history=list(execution.get("state_history", []) or []),
        )
        if create:
            self.execution_repository.create(envelope)
        else:
            self.execution_repository.save(envelope)
        if envelope.provider_states:
            self.execution_repository.save_provider_health(execution_id=envelope.execution_id, tenant_id=envelope.tenant_id, snapshots=envelope.provider_states)

    def _transition_execution(self, execution: dict[str, Any], status: str, *, actor_id: str | None = None) -> None:
        """Apply an explicit durable execution transition before persistence."""
        next_status = str(status).upper()
        previous = str(execution.get("status") or "PENDING").upper()
        now = _utc_iso()
        execution["status"] = next_status.lower()
        if next_status == "RUNNING":
            execution["started_at"] = now
        if next_status in {"COMPLETED", "FAILED", "UNAVAILABLE", "BLOCKED"}:
            execution["completed_at"] = now
        history = execution.setdefault("state_history", [])
        if not history or history[-1].get("to") != next_status:
            history.append({
                "from": previous,
                "to": next_status,
                "at": now,
                "actor_id": actor_id,
                "correlation_id": execution.get("correlation_id"),
            })


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
                "evidence_collection",
                "investigation_execution",
                "threat_intelligence",
                "ioc_enrichment",
            ],
        )

    def _execute_evidence_collection(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Runtime capability exposing the already-normalized evidence root."""
        context = payload.get("context")
        evidence = list(getattr(context, "evidence", []) or [])
        return {
            "status": "success",
            "evidence": evidence,
            "findings": [],
            "recommendations": [],
            "confidence": 1.0 if evidence else 0.0,
            "metadata": {
                "engine": "EvidenceIntelligenceEngine",
                "evidence_count": len(evidence),
                "evidence_ids": [item.get("evidence_id") for item in evidence if isinstance(item, dict)],
            },
        }

    @staticmethod
    def _evidence_key(item: Any) -> str:
        return json.dumps(item, sort_keys=True, default=str)

    @staticmethod
    def _evidence_id(case_id: str, item: Any, index: int) -> str:
        digest = hashlib.sha256(
            f"{case_id}|{index}|{json.dumps(item, sort_keys=True, default=str)}".encode("utf-8")
        ).hexdigest()[:20]
        return f"EVD-{digest}"

    def _normalize_evidence(
        self,
        case_id: str,
        alert: dict[str, Any],
        artifacts: Optional[list[dict[str, Any]]],
        evidence: Optional[list[dict[str, Any]]],
        tenant_id: str | None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Normalize all supplied evidence once and assign stable IDs."""
        raw_items: list[Any] = []
        seen: set[str] = set()
        for item in list(artifacts or []) + list(evidence or []):
            key = self._evidence_key(item)
            if key in seen:
                continue
            seen.add(key)
            raw_items.append(item)
        if not raw_items:
            raw_items = [{"type": "alert", "value": alert}]

        collection = self.evidence_engine.normalize(case_id, raw_items)
        normalized: list[dict[str, Any]] = []
        for index, (raw, artifact) in enumerate(zip(raw_items, collection.artifacts)):
            source = raw.get("source", "alert") if isinstance(raw, dict) else "alert"
            original = dict(raw) if isinstance(raw, dict) else {"value": raw}
            item = artifact.to_dict() if hasattr(artifact, "to_dict") else dict(vars(artifact))
            evidence_id = str(original.get("evidence_id") or original.get("artifact_id") or original.get("id") or self._evidence_id(case_id, raw, index))
            collected_at = original.get("collected_at") or original.get("collection_timestamp") or datetime.now(timezone.utc).isoformat()
            raw_digest = hashlib.sha256(self._evidence_key(raw).encode("utf-8")).hexdigest()
            item = {
                **original,
                "evidence_id": evidence_id,
                "type": original.get("type") or item.get("artifact_type", "observation"),
                "value": original.get("value", item.get("value")),
                "source": source,
                "classification": item.get("artifact_type"),
                "indicators": list(item.get("indicators", []) or []),
                "confidence": item.get("confidence", 0),
                "collected_at": collected_at,
                "tenant_id": tenant_id,
                "integrity": {"algorithm": "sha256", "digest": raw_digest, "verified": True},
                "confidence_impact": item.get("confidence", 0),
                "provenance": {
                    **(original.get("provenance") if isinstance(original.get("provenance"), dict) else {}),
                    "source": source,
                    "engine": "EvidenceIntelligenceEngine",
                    "tenant_id": tenant_id,
                },
            }
            normalized.append(item)
        return normalized, collection.metadata


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
        execution_id: str | None = None,
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
                "execution_id": execution_id or context.investigation_id,
            },
            execution_id=execution_id or context.investigation_id,
            metadata={"retry_safe": True, "boundary": "capability_handler"},
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
            "provider_health": [item.to_dict() if hasattr(item, "to_dict") else item for item in getattr(result, "provider_health", ())],
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
        for key in ("provider_results", "observations", "provider_health"):
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
        adapter_mitre = self.mitre_adapter.execute(case_id, alert).get("techniques", [])
        mitre = {
            "case_id": case_id,
            "techniques": list(dict.fromkeys(list(engine_mitre) + list(adapter_mitre))),
        }
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
        source_metadata = alert.get("metadata") if isinstance(alert.get("metadata"), dict) else {}
        normalized_intelligence = InvestigationIntelligence(
            findings=findings,
            recommendations=list(dict.fromkeys(recommendations)),
            risk_score=risk.get("score", 0),
            risk_severity=risk.get("severity", "unknown"),
            confidence=confidence_data["score"],
            mitre_techniques=mitre.get("techniques", []),
            attack_story=attack_story,
            iocs=engine_analysis.get("iocs", []),
            evidence_summary={"count": len(normalized_artifacts), "items": normalized_artifacts},
            timeline=[],
            metadata={
                "case_id": case_id,
                **source_metadata,
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
        report.metadata = {**(report.metadata or {}), **normalized_intelligence.metadata}
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
        evidence_for_reasoning = list(normalized_artifacts) + list(engine_analysis.get("evidence", []) or [])
        investigation_iocs = list(engine_analysis.get("iocs", []) or [])
        if not investigation_iocs:
            investigation_iocs = [
                {"type": "unknown", "value": indicator}
                for item in normalized_artifacts
                for indicator in item.get("indicators", []) or []
            ]
        reasoning_report = self.evidence_reasoner.reason(
            self.create_context(
                investigation_id=case_id,
                artifacts=normalized_artifacts,
                evidence=evidence_for_reasoning,
                iocs=investigation_iocs,
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
                                    iocs=investigation_iocs,
                                    timeline=list(normalized_intelligence.timeline or []),
                                    tenant_id=scoped_tenant_id),
                evidence_for_reasoning, investigation_iocs, None)
        except Exception:
            pass
        result = InvestigationResult(
            success=True,
            status="completed",
            message="Investigation completed.",
            case_id=case_id,
            execution_id=execution.get("execution_id"),
            plan=plan,
            plan_name=plan.plan_name,
            execution=execution,
            results=list(execution["results"]),
            artifacts=normalized_artifacts,
            evidence=normalized_artifacts,
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
                                    iocs=investigation_iocs,
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
        result.metadata["execution_envelope"] = {
            "execution_id": execution.get("execution_id"),
            "status": execution.get("status"),
            "started_at": execution.get("started_at"),
            "completed_at": execution.get("completed_at"),
        }
        result.metadata["provider_health_summary"] = list(execution.get("provider_health", []) or [])
        result.metadata["task_lifecycle_summary"] = {
            "total": len(execution.get("tasks", []) or []),
            "states": {state: sum(1 for task in execution.get("tasks", []) or [] if str(task.get("execution_state") or task.get("execution_status", "")).upper() == state) for state in ("PENDING", "RUNNING", "SUCCESS", "FAILED", "UNAVAILABLE", "BLOCKED")},
        }
        result.metadata["evidence_provenance_summary"] = {
            "count": len(normalized_artifacts),
            "evidence_ids": [item.get("evidence_id") for item in normalized_artifacts if item.get("evidence_id")],
            "tenant_id": scoped_tenant_id,
        }
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
                                    iocs=investigation_iocs,
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
        result.projection = self.projection_builder.build(
            result,
            alert=alert,
            tenant_id=scoped_tenant_id,
        )
        result.intelligence["projection"] = result.projection.to_dict()
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
            execution = self.get_execution_projection_for_investigation(str(case_id), str(tenant_id))
            if execution:
                payload["execution"] = execution
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

    def list_execution_projections(self, security_context: Any, *, limit: int = 50) -> list[dict[str, Any]]:
        tenant_id = getattr(security_context, "tenant_id", None)
        if not tenant_id or getattr(security_context, "error", None):
            raise PermissionError("execution tenant authorization is required")
        return [self._build_execution_projection(item, str(tenant_id)) for item in self.execution_repository.list_for_tenant(str(tenant_id), limit=limit)]

    def get_execution_projection(self, execution_id: str, security_context: Any) -> dict[str, Any] | None:
        tenant_id = getattr(security_context, "tenant_id", None)
        if not tenant_id or getattr(security_context, "error", None):
            raise PermissionError("execution tenant authorization is required")
        envelope = self.execution_repository.get(str(execution_id), str(tenant_id))
        if envelope is None:
            return None
        return self._build_execution_projection(envelope, str(tenant_id))

    def get_execution_projection_for_investigation(self, investigation_id: str, tenant_id: str) -> dict[str, Any] | None:
        records = self.execution_repository.list_for_tenant(str(tenant_id), investigation_id=str(investigation_id), limit=1)
        return self._build_execution_projection(records[0], str(tenant_id)) if records else None

    def _build_execution_projection(self, envelope: dict[str, Any], tenant_id: str) -> dict[str, Any]:
        if str(envelope.get("tenant_id")) != str(tenant_id):
            raise PermissionError("execution tenant ownership is required")
        case_id = str(envelope.get("investigation_id"))
        report = self.get_report_by_case_id(case_id, tenant_id) or {}
        intelligence = self.intelligence_repository.get_by_case_id_for_tenant(case_id, tenant_id) if callable(getattr(self.intelligence_repository, "get_by_case_id_for_tenant", None)) else {}
        providers = self.execution_repository.provider_health_for_execution(str(envelope.get("execution_id")), str(tenant_id))
        return self.execution_projection_builder.build(envelope, providers=providers, report=report, intelligence=intelligence).to_dict()

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
        """Return a tenant-scoped projection of persisted investigations."""
        investigations = []
        for report in self.report_repository.get_all():
            if not isinstance(report, dict):
                continue
            owner = (report.get("tenant_context") or {}).get("tenant_id") or (report.get("metadata") or {}).get("tenant_id")
            if str(owner or "") != str(tenant_id):
                continue
            case_id = str(report.get("case_id") or report.get("investigation_id") or "")
            scoped_intelligence = getattr(self.intelligence_repository, "get_by_case_id_for_tenant", None)
            intelligence = (scoped_intelligence(case_id, tenant_id) if callable(scoped_intelligence) else None) or {}
            evidence = report.get("evidence") or (intelligence.get("evidence_summary") or {}).get("items") or []
            iocs = report.get("iocs") or intelligence.get("iocs") or []
            timeline = report.get("timeline") or intelligence.get("timeline") or []
            mitre = report.get("mitre") or intelligence.get("mitre_techniques") or []
            execution = self.get_execution_projection_for_investigation(case_id, str(tenant_id))
            last_activity = max((str(item.get("timestamp") or item.get("created_at") or "") for item in timeline if isinstance(item, dict)), default=str(report.get("created_at") or ""))
            investigations.append({
                "case_id": case_id, "status": report.get("status", "unknown"),
                "title": report.get("title") or case_id,
                "severity": report.get("severity") or intelligence.get("risk_severity", "unknown"),
                "risk_score": report.get("risk_score", intelligence.get("risk_score", 0)),
                "confidence": report.get("confidence", intelligence.get("confidence", 0)),
                "evidence_count": len(evidence),
                "ioc_count": len(iocs),
                "last_activity": last_activity,
                "mitre_techniques": mitre,
                "timeline": timeline,
                "iocs": iocs,
                "execution": execution,
            })
        active = [item for item in investigations if str(item["status"]).lower() in {"active", "investigating", "in_progress", "open"}]
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        threat = max((str(item.get("severity") or "").lower() for item in investigations), key=lambda value: severity_order.get(value, 0), default="")
        risk_labels = ("critical", "high", "medium", "low")
        risk_distribution = {label: 0 for label in risk_labels}
        risk_distribution["unscored"] = 0
        status_distribution: dict[str, int] = {}
        severity_distribution: dict[str, int] = {}
        ioc_reputation: dict[str, int] = {}
        mitre_coverage: dict[str, int] = {}
        confidence_distribution = {"High": 0, "Medium": 0, "Low": 0, "Unavailable": 0}
        activity: list[dict[str, Any]] = []
        for item in investigations:
            status = str(item.get("status") or "unknown").replace("_", " ").title()
            severity = str(item.get("severity") or "unknown").lower()
            status_distribution[status] = status_distribution.get(status, 0) + 1
            severity_distribution[severity.title()] = severity_distribution.get(severity.title(), 0) + 1
            try:
                score = float(item.get("risk_score") or 0)
            except (TypeError, ValueError):
                score = 0
            if score > 0:
                risk_distribution["critical" if score >= 80 else "high" if score >= 60 else "medium" if score >= 30 else "low"] += 1
            else:
                risk_distribution["unscored"] += 1
            try:
                confidence = float(item.get("confidence") or 0)
                confidence = confidence * 100 if 0 < confidence <= 1 else confidence
            except (TypeError, ValueError):
                confidence = 0
            if confidence > 0:
                confidence_distribution["High" if confidence >= 80 else "Medium" if confidence >= 50 else "Low"] += 1
            else:
                confidence_distribution["Unavailable"] += 1
            for ioc in item.get("iocs") or []:
                if not isinstance(ioc, dict):
                    continue
                reputation = ioc.get("reputation") or ioc.get("intelligence_status") or "unavailable"
                key = str(reputation).replace("_", " ").title()
                ioc_reputation[key] = ioc_reputation.get(key, 0) + 1
            for technique in item.get("mitre_techniques") or []:
                technique_id = technique.get("id") if isinstance(technique, dict) else str(technique)
                if technique_id:
                    mitre_coverage[str(technique_id)] = mitre_coverage.get(str(technique_id), 0) + 1
            for event in item.get("timeline") or []:
                if isinstance(event, dict):
                    activity.append({"case_id": item["case_id"], "timestamp": event.get("timestamp") or event.get("created_at"), "label": event.get("event_type") or event.get("description") or "Investigation event"})
        activity = sorted(activity, key=lambda value: str(value.get("timestamp") or ""), reverse=True)[:12]
        total_confidence = [float(item["confidence"]) for item in investigations if isinstance(item.get("confidence"), (int, float)) and float(item["confidence"]) > 0]
        return {
            "investigations": investigations,
            "active_investigations": active,
            "recent_alerts": investigations[:10],
            "overview": {
                "threat_level": threat.title() if threat else "No active signal",
                "active_investigations": len(active),
                "critical_high_alerts": sum(1 for item in investigations if str(item.get("severity", "")).lower() in {"critical", "high"}),
                "evidence_collected": sum(item["evidence_count"] for item in investigations),
                "ioc_intelligence": sum(item["ioc_count"] for item in investigations),
                "investigation_confidence": round(sum(total_confidence) / len(total_confidence) * 100) if total_confidence else None,
            },
            "visualizations": {
                "activity": activity,
                "risk_distribution": [{"label": label.title(), "count": count} for label, count in risk_distribution.items() if count or label == "unscored"],
                "status_distribution": [{"label": label, "count": count} for label, count in sorted(status_distribution.items())],
                "severity_distribution": [{"label": label, "count": count} for label, count in sorted(severity_distribution.items())],
                "ioc_reputation_distribution": [{"label": label, "count": count} for label, count in sorted(ioc_reputation.items())] or [{"label": "Unavailable", "count": 0}],
                "confidence_distribution": [{"label": label, "count": count} for label, count in confidence_distribution.items() if count or label == "Unavailable"],
                "mitre_coverage": [{"label": label, "count": count} for label, count in sorted(mitre_coverage.items())],
            },
        }

    def submit_feedback(self, case_id: str, payload: dict[str, Any], *, tenant_id: str, analyst_id: str) -> AnalystFeedback:
        report = self.get_report_by_case_id(case_id, tenant_id)
        if report is None:
            raise LookupError("investigation_not_found")
        metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
        investigation_id = str(metadata.get("investigation_id") or report.get("investigation_id") or case_id)
        feedback = self.feedback_service.record(
            investigation_id=investigation_id,
            case_id=str(case_id),
            tenant_id=str(tenant_id),
            analyst_id=str(analyst_id),
            payload=payload,
            report=report,
        )
        ObservabilityService().event(
            "investigation_feedback_recorded",
            investigation_id=investigation_id,
            case_id=str(case_id),
            tenant_id=str(tenant_id),
            feedback_decision=feedback.decision,
        )
        return feedback

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
        execution_id = str(kwargs.get("execution_id") or uuid4())
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


        plan = self.create_plan(
            case_id,
            alert_data,
        )


        tenant_id = kwargs.get("tenant_id")
        actor_id = kwargs.get("actor_id")
        owned_evidence: list[dict[str, Any]] = []
        if tenant_id:
            for item in list(artifacts or []):
                if isinstance(item, dict) and item.get("tenant_id") not in (None, tenant_id):
                    raise PermissionError("artifact tenant does not match investigation tenant")
            for item in evidence or []:
                if not isinstance(item, dict) or item.get("tenant_id") != tenant_id:
                    raise PermissionError("evidence tenant does not match investigation tenant")
                if not any(item.get(key) for key in ("evidence_id", "artifact_id", "id", "reference")):
                    raise PermissionError("evidence reference is required")
                owned_evidence.append(dict(item))
        normalized_artifacts, evidence_metadata = self._normalize_evidence(
            case_id, alert_data, artifacts, evidence, tenant_id
        )
        normalized_iocs = list(iocs or [])
        integrity_digests = {
            str(item.get("integrity", {}).get("digest", "")).lower()
            for item in normalized_artifacts
            if isinstance(item, dict) and isinstance(item.get("integrity"), dict)
        }
        for item in normalized_artifacts:
            for indicator in item.get("indicators", []) or []:
                if str(indicator).lower() in integrity_digests:
                    continue
                if indicator and not any(
                    isinstance(existing, dict)
                    and str(existing.get("value", "")).lower() == str(indicator).lower()
                    for existing in normalized_iocs
                ):
                    normalized_iocs.append({"type": "unknown", "value": indicator})
        normalized_iocs = [
            item for item in normalized_iocs
            if not (isinstance(item, dict) and str(item.get("value", "")).lower() in integrity_digests)
        ]
        context = self.create_context(
            investigation_id=alert_data.get(
                "investigation_id",
                case_id,
            ),
            artifacts=normalized_artifacts,
            evidence=normalized_artifacts,
            iocs=normalized_iocs,
            timeline=timeline,
            correlation_id=correlation_id,
        )

        context.tenant_id = tenant_id
        context.actor_id = actor_id
        intelligence_metadata: dict[str, Any] = {}
        investigation_id = str(alert_data.get("investigation_id") or case_id)
        capabilities = self._get_plan_capabilities(plan)
        queued_at = _utc_iso()
        execution = {
            "case_id": case_id,
            "execution_id": execution_id,
            "created_at": queued_at,
            "queued_at": queued_at,
            "started_at": queued_at,
            "status": "queued",
            "correlation_id": correlation_id,
            "capabilities": capabilities,
            "results": [],
            "errors": [],
            "tasks": [],
            "workflow": None,
            "intelligence": intelligence_metadata,
            "provider_health": [],
            "evidence": normalized_artifacts,
            "evidence_metadata": evidence_metadata,
            "state_history": [{
                "from": None,
                "to": "QUEUED",
                "at": queued_at,
                "actor_id": actor_id,
                "correlation_id": correlation_id,
            }],
        }
        self._persist_execution(
            execution,
            tenant_id=tenant_id,
            actor_id=actor_id,
            investigation_id=investigation_id,
            alert=alert_data,
            evidence=normalized_artifacts,
            create=True,
        )
        if self.threat_intelligence_gateway is not None and normalized_iocs:
            if not tenant_id or not actor_id:
                observer.event(
                    "THREAT_INTELLIGENCE_AUTHORIZATION_DENIED",
                    case_id=case_id,
                    tenant_id=tenant_id,
                    actor_id=actor_id,
                    reason="tenant and actor context are required for intelligence lookup",
                    **({"correlation_id": correlation_id} if correlation_id else {}),
                )
                execution["errors"].append({
                    "status": "failed",
                    "error_code": "intelligence_authorization_denied",
                    "error": "Tenant and actor context are required for intelligence lookup",
                })
                self._transition_execution(execution, "FAILED", actor_id=actor_id)
                self._persist_execution(execution, tenant_id=tenant_id, actor_id=actor_id, investigation_id=investigation_id, alert=alert_data, evidence=normalized_artifacts)
                raise PermissionError("tenant and actor context are required for intelligence lookup")
            for item in normalized_iocs:
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
                    case_id=case_id,
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
                    execution["errors"].append({
                        "status": "failed",
                        "error_code": "intelligence_authorization_denied",
                        "error": "Threat intelligence authorization denied",
                    })
                    self._transition_execution(execution, "FAILED", actor_id=actor_id)
                    self._persist_execution(execution, tenant_id=tenant_id, actor_id=actor_id, investigation_id=investigation_id, alert=alert_data, evidence=normalized_artifacts)
                    raise
                normalized_lookup = self._normalize_intelligence_gateway_result(result)
                normalized_lookup["provider_health"] = [item.to_dict() if hasattr(item, "to_dict") else item for item in getattr(result, "provider_health", ())]
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
        try:
            workflow = self.orchestrator.investigate(
                case_id=case_id,
                artifacts=normalized_artifacts,
                alert=alert_data,
                **orchestrator_kwargs,
            )
        except Exception as exc:
            execution["errors"].append({
                "status": "failed",
                "error_code": "orchestration_failed",
                "error": "Investigation orchestration failed",
                "exception_type": type(exc).__name__,
            })
            self._transition_execution(execution, "FAILED", actor_id=actor_id)
            self._persist_execution(execution, tenant_id=tenant_id, actor_id=actor_id, investigation_id=investigation_id, alert=alert_data, evidence=normalized_artifacts)
            raise


        execution["workflow"] = workflow
        execution["intelligence"] = intelligence_metadata
        execution["provider_health"] = list(intelligence_metadata.get("provider_health", []) or [])
        self._persist_execution(execution, tenant_id=tenant_id, actor_id=actor_id, investigation_id=investigation_id, alert=alert_data, evidence=normalized_artifacts)


        # ----------------------------------------------------
        # Runtime validation
        # ----------------------------------------------------


        if self.runtime is None:

            execution["errors"].append({
                "status": "failed",
                "error_code": "runtime_unavailable",
                "error": "Runtime task executor is not configured.",
            })
            self._transition_execution(execution, "FAILED", actor_id=actor_id)
            self._persist_execution(execution, tenant_id=tenant_id, actor_id=actor_id, investigation_id=investigation_id, alert=alert_data, evidence=normalized_artifacts)

            return InvestigationResult(
                success=False,
                status="failed",
                message="Runtime task executor is not configured.",
                error="Runtime task executor is not configured.",
                case_id=case_id,
                plan=plan,
                execution_id=execution_id,
                plan_name=plan.plan_name,
                execution=execution,
                results=[],
                artifacts=normalized_artifacts,
                evidence=normalized_artifacts,
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
            execution["errors"].append({
                "status": "failed",
                "error_code": "runtime_capability_missing",
                "error": error_message,
            })
            self._transition_execution(execution, "FAILED", actor_id=actor_id)
            self._persist_execution(execution, tenant_id=tenant_id, actor_id=actor_id, investigation_id=investigation_id, alert=alert_data, evidence=normalized_artifacts)

            return InvestigationResult(
                success=False,
                status="failed",
                message="Missing runtime capabilities.",
                error=error_message,
                case_id=case_id,
                plan=plan,
                execution_id=execution_id,
                plan_name=plan.plan_name,
                execution=execution,
                results=[],
                artifacts=normalized_artifacts,
                evidence=normalized_artifacts,
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


        self._transition_execution(execution, "RUNNING", actor_id=actor_id)
        self._persist_execution(execution, tenant_id=tenant_id, actor_id=actor_id, investigation_id=investigation_id, alert=alert_data, evidence=normalized_artifacts)

        for capability in capabilities:

            task = self._create_runtime_task(
                case_id=case_id,
                alert=alert_data,
                plan=plan,
                capability=capability,
                context=context,
                execution_id=execution_id,
            )
            task.queue()
            execution["tasks"].append(task.to_dict())
            self._persist_execution(execution, tenant_id=tenant_id, actor_id=actor_id, investigation_id=investigation_id, alert=alert_data, evidence=normalized_artifacts)


            try:

                result = self.runtime.execute(
                    task
                )

                task_status = getattr(task, "execution_status", "pending")
                result_status = getattr(result, "status", None)
                if hasattr(result_status, "value"):
                    result_status = result_status.value
                if isinstance(result, dict):
                    result_status = result.get("status", result_status)
                if task_status in {"pending", "queued"} and result is not None and result_status not in {"failed", "unavailable", "blocked"}:
                    # Preserve compatibility with runtime adapters that return
                    # a result without mutating the Task lifecycle themselves.
                    task.complete(result)
                    task_status = "success"
                execution["results"].append(
                    {
                        "capability": capability,
                        "task_id": task.task_id,
                        "execution_id": task.execution_id,
                        "status": task_status,
                        "result": result.to_dict() if hasattr(result, "to_dict") else result,
                    }
                )
                if task_status != "success":
                    failure = result.to_dict() if hasattr(result, "to_dict") else (result if isinstance(result, dict) else {})
                    execution["errors"].append({
                        "capability": capability,
                        "task_id": task.task_id,
                        "execution_id": task.execution_id,
                        "status": task_status,
                        "error": failure.get("error", task.error or "Runtime capability did not complete successfully"),
                        "error_code": failure.get("error_code", "runtime_execution_failed"),
                    })


            except Exception as exc:

                execution["errors"].append(
                    {
                        "capability": capability,
                        "task_id": task.task_id,
                        "execution_id": task.execution_id,
                        "status": "failed",
                        "error_code": "runtime_exception",
                        "error": "Runtime capability raised an exception",
                        "exception_type": type(exc).__name__,
                    }
                )


            execution["tasks"][-1] = task.to_dict()
            self._persist_execution(execution, tenant_id=tenant_id, actor_id=actor_id, investigation_id=investigation_id, alert=alert_data, evidence=normalized_artifacts)


        success = not bool(
            execution["errors"]
        )


        self._transition_execution(execution, "COMPLETED" if success else "FAILED", actor_id=actor_id)
        execution["provider_health"] = list(execution.get("provider_health", []) or [])
        self._persist_execution(execution, tenant_id=tenant_id, actor_id=actor_id, investigation_id=investigation_id, alert=alert_data, evidence=normalized_artifacts)


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
            execution_id=execution_id,
            plan_name=plan.plan_name,
            execution=execution,
            results=list(execution["results"]),
            errors=list(execution["errors"]),
            artifacts=normalized_artifacts,
            evidence=normalized_artifacts,
            findings=[],
            intelligence={"workflow": workflow},
            tenant_context={"tenant_id": tenant_id, "actor_id": actor_id},
            metadata={
                "actor_id": actor_id,
                **({"correlation_id": kwargs.get("correlation_id")} if kwargs.get("correlation_id") else {}),
            },
        )
        result.metadata["execution_envelope"] = {
            "execution_id": execution_id,
            "status": execution.get("status"),
            "started_at": execution.get("started_at"),
            "completed_at": execution.get("completed_at"),
        }
        result.metadata["provider_health_summary"] = list(execution.get("provider_health", []) or [])
        result.metadata["task_lifecycle_summary"] = {"total": len(execution.get("tasks", []) or []), "states": {state: sum(1 for task in execution.get("tasks", []) or [] if str(task.get("execution_state") or task.get("execution_status", "")).upper() == state) for state in ("PENDING", "RUNNING", "SUCCESS", "FAILED", "UNAVAILABLE", "BLOCKED")}}
        result.metadata["evidence_provenance_summary"] = {"count": len(normalized_artifacts), "evidence_ids": [item.get("evidence_id") for item in normalized_artifacts if item.get("evidence_id")], "tenant_id": tenant_id}
        observer.event(
            "INVESTIGATION_STARTED",
            case_id=case_id,
            status="failed",
            duration_ms=round((time.perf_counter()-started_at)*1000, 2),
            errors=result.errors,
            **({"correlation_id": correlation_id} if correlation_id else {}),
        )
        return result
