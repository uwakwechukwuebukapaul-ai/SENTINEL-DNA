"""Immutable models used by the enterprise proof validation layer."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SyntheticTenantEnvironment:
    tenant_id: str
    investigation_id: str
    evidence_provenance: tuple[dict[str, Any], ...]
    investigation_memory_ids: tuple[str, ...]
    organizational_memory_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TenantAccessAttempt:
    requester_tenant_id: str
    owner_tenant_id: str
    memory_layer: str
    resource_id: str
    allowed: bool
    observed_tenant_id: str | None
    observed_provenance: tuple[dict[str, Any], ...]
    failure_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TenantIsolationCertification:
    tenant_ids: tuple[str, ...]
    access_attempts: tuple[TenantAccessAttempt, ...]
    memory_isolation_valid: bool
    organizational_memory_isolation_valid: bool
    evidence_provenance_valid: bool
    cross_tenant_access_denied: bool
    result_contract_unchanged: bool
    certification_result: str
    replay_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_ids": list(self.tenant_ids),
            "access_attempts": [item.to_dict() for item in self.access_attempts],
            "memory_isolation_valid": self.memory_isolation_valid,
            "organizational_memory_isolation_valid": self.organizational_memory_isolation_valid,
            "evidence_provenance_valid": self.evidence_provenance_valid,
            "cross_tenant_access_denied": self.cross_tenant_access_denied,
            "result_contract_unchanged": self.result_contract_unchanged,
            "certification_result": self.certification_result,
            "replay_digest": self.replay_digest,
        }


@dataclass(frozen=True)
class AnalystEffectivenessCase:
    scenario_id: str
    tenant_id: str
    baseline_investigation_time_ms: float
    enhanced_investigation_time_ms: float
    baseline_ai_confidence: float
    enhanced_ai_confidence: float
    baseline_analyst_confidence: float
    enhanced_analyst_confidence: float
    recommendation_present: bool
    recommendation_accepted: bool
    baseline_false_escalation: bool
    enhanced_false_escalation: bool
    evidence_provenance_preserved: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnalystEffectivenessBenchmark:
    tenant_id: str
    cases: tuple[AnalystEffectivenessCase, ...]
    investigation_time_reduction_ms: float
    investigation_time_reduction_rate: float
    analyst_confidence_improvement: float
    ai_confidence_improvement: float
    recommendation_acceptance_rate: float
    false_escalations_baseline: int
    false_escalations_enhanced: int
    false_escalation_reduction: int
    evidence_provenance_preserved: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "cases": [item.to_dict() for item in self.cases],
            "investigation_time_reduction_ms": self.investigation_time_reduction_ms,
            "investigation_time_reduction_rate": self.investigation_time_reduction_rate,
            "analyst_confidence_improvement": self.analyst_confidence_improvement,
            "recommendation_acceptance_rate": self.recommendation_acceptance_rate,
            "false_escalations_baseline": self.false_escalations_baseline,
            "false_escalations_enhanced": self.false_escalations_enhanced,
            "false_escalation_reduction": self.false_escalation_reduction,
            "evidence_provenance_preserved": self.evidence_provenance_preserved,
        }


@dataclass(frozen=True)
class ScaleBenchmarkPoint:
    investigation_count: int
    baseline_p50_latency_ms: float
    baseline_p95_latency_ms: float
    enhanced_p50_latency_ms: float
    enhanced_p95_latency_ms: float
    baseline_memory_kb: float
    enhanced_memory_kb: float
    memory_overhead_kb: float
    memory_overhead_rate: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InvestigationScaleBenchmark:
    tenant_id: str
    points: tuple[ScaleBenchmarkPoint, ...]
    timing_model: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "points": [item.to_dict() for item in self.points],
            "timing_model": self.timing_model,
        }


@dataclass(frozen=True)
class EnterpriseProofValidationReport:
    report_version: str
    generated_at: str
    tenant_ids: tuple[str, ...]
    tenant_isolation: TenantIsolationCertification
    analyst_effectiveness: AnalystEffectivenessBenchmark
    scale_benchmark: InvestigationScaleBenchmark
    billing_entitlement: dict[str, Any]
    architecture_summary: dict[str, Any]
    safety_validation: dict[str, bool]
    replay_digest: str
    report_digest: str
    immutable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "generated_at": self.generated_at,
            "tenant_ids": list(self.tenant_ids),
            "tenant_isolation": self.tenant_isolation.to_dict(),
            "analyst_effectiveness": self.analyst_effectiveness.to_dict(),
            "scale_benchmark": self.scale_benchmark.to_dict(),
            "billing_entitlement": self.billing_entitlement,
            "architecture_summary": self.architecture_summary,
            "safety_validation": self.safety_validation,
            "replay_digest": self.replay_digest,
            "report_digest": self.report_digest,
            "immutable": self.immutable,
        }

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


__all__ = [
    "AnalystEffectivenessBenchmark",
    "AnalystEffectivenessCase",
    "EnterpriseProofValidationReport",
    "InvestigationScaleBenchmark",
    "ScaleBenchmarkPoint",
    "SyntheticTenantEnvironment",
    "TenantAccessAttempt",
    "TenantIsolationCertification",
]
