"""Immutable models for controlled operational pilot validation."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


PILOT_STAGES = (
    "alert_ingestion",
    "coordinator",
    "orchestrator",
    "evidence_retrieval",
    "ioc_enrichment",
    "mitre_mapping",
    "memory_retrieval",
    "organizational_memory_retrieval",
    "reasoning",
    "report_generation",
)


@dataclass(frozen=True)
class PilotAlert:
    tenant_id: str
    alert_id: str
    investigation_id: str
    case_id: str
    scenario_type: str
    title: str
    evidence_ids: tuple[str, ...]
    evidence_sources: tuple[str, ...]
    expected_verdict: str
    authorization_status: str = "blocked_by_policy"
    fail_closed: bool = True
    failure_mode: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PilotFeedback:
    tenant_id: str
    investigation_id: str
    analyst_id: str
    accepted_recommendation: bool
    analyst_confidence: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PilotEvidence:
    evidence_id: str
    tenant_id: str
    investigation_id: str
    source: str
    provenance_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PilotStageTimings:
    values_ms: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {"values_ms": dict(self.values_ms)}


@dataclass(frozen=True)
class PilotExecution:
    alert: PilotAlert
    completed: bool
    successful: bool
    failure_reason: str | None
    evidence: tuple[PilotEvidence, ...]
    investigation_memory_items: int
    organizational_memory_items: int
    memory_context_improved: bool
    feedback: PilotFeedback | None
    stage_timings: PilotStageTimings
    advisory_verdict: str | None
    enforced_verdict: str | None
    authorization_status: str
    fail_closed: bool
    result_schema_unchanged: bool
    provenance_chain: tuple[dict[str, Any], ...]
    audit_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "alert": self.alert.to_dict(),
            "completed": self.completed,
            "successful": self.successful,
            "failure_reason": self.failure_reason,
            "evidence": [item.to_dict() for item in self.evidence],
            "investigation_memory_items": self.investigation_memory_items,
            "organizational_memory_items": self.organizational_memory_items,
            "memory_context_improved": self.memory_context_improved,
            "feedback": self.feedback.to_dict() if self.feedback else None,
            "stage_timings": self.stage_timings.to_dict(),
            "advisory_verdict": self.advisory_verdict,
            "enforced_verdict": self.enforced_verdict,
            "authorization_status": self.authorization_status,
            "fail_closed": self.fail_closed,
            "result_schema_unchanged": self.result_schema_unchanged,
            "provenance_chain": list(self.provenance_chain),
            "audit_hash": self.audit_hash,
        }


@dataclass(frozen=True)
class PilotOperationalMetrics:
    investigations_completed: int
    successful_investigations: int
    failed_investigations: int
    mean_investigation_latency_ms: float
    p50_investigation_latency_ms: float
    p95_investigation_latency_ms: float
    stage_mean_timings_ms: dict[str, float]
    evidence_retrieval_timing_ms: float
    ioc_enrichment_timing_ms: float
    mitre_mapping_timing_ms: float
    memory_retrieval_timing_ms: float
    report_generation_timing_ms: float
    investigation_memory_items: int
    organizational_memory_items: int
    memory_context_reuse_rate: float
    analyst_feedback_captured: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OperationalPilotReport:
    report_version: str
    generated_at: str
    tenant_ids: tuple[str, ...]
    executions: tuple[PilotExecution, ...]
    metrics: PilotOperationalMetrics
    provenance_chain: tuple[dict[str, Any], ...]
    safety_validation: dict[str, bool]
    replay_digest: str
    report_digest: str
    immutable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "generated_at": self.generated_at,
            "tenant_ids": list(self.tenant_ids),
            "executions": [item.to_dict() for item in self.executions],
            "metrics": self.metrics.to_dict(),
            "provenance_chain": list(self.provenance_chain),
            "safety_validation": self.safety_validation,
            "replay_digest": self.replay_digest,
            "report_digest": self.report_digest,
            "immutable": self.immutable,
        }

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


__all__ = [
    "OperationalPilotReport",
    "PILOT_STAGES",
    "PilotAlert",
    "PilotEvidence",
    "PilotExecution",
    "PilotFeedback",
    "PilotOperationalMetrics",
    "PilotStageTimings",
]
