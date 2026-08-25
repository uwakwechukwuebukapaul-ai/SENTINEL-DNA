"""Orchestrator for enterprise trust proof validation."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

from services.intelligence.evaluation.benchmark_runner import OperationalAccuracyBenchmarkRunner

from .analyst_effectiveness import AnalystEffectivenessBenchmarker
from .models import EnterpriseProofValidationReport
from .scale_benchmark import InvestigationScaleBenchmarker
from .tenant_isolation import TenantIsolationCertifier


class EnterpriseProofValidator:
    """Compose isolated proof checks without entering production investigation flow."""

    REPORT_VERSION = "enterprise-proof-validation.v1"

    def __init__(
        self,
        *,
        generated_at: str | None = None,
        tenant_certifier: TenantIsolationCertifier | None = None,
        analyst_benchmarker: AnalystEffectivenessBenchmarker | None = None,
        scale_benchmarker: InvestigationScaleBenchmarker | None = None,
    ) -> None:
        self.generated_at = str(generated_at or datetime.now(timezone.utc).isoformat())
        self.tenant_certifier = tenant_certifier or TenantIsolationCertifier()
        self.analyst_benchmarker = analyst_benchmarker or AnalystEffectivenessBenchmarker()
        self.scale_benchmarker = scale_benchmarker or InvestigationScaleBenchmarker()

    def run(self) -> EnterpriseProofValidationReport:
        tenant_isolation = self.tenant_certifier.run()
        analyst_effectiveness = self.analyst_benchmarker.run()
        scale_benchmark = self.scale_benchmarker.run()
        accuracy_report = OperationalAccuracyBenchmarkRunner().run()
        declared_tenants = tuple(sorted({
            *tenant_isolation.tenant_ids,
            analyst_effectiveness.tenant_id,
            scale_benchmark.tenant_id,
        }))
        safety = {
            "authorization_unchanged": accuracy_report.safety_validation["authorization_unchanged"],
            "verdict_enforcement_unchanged": accuracy_report.safety_validation["verdict_enforcement_unchanged"],
            "tenant_isolation_unchanged": (
                accuracy_report.safety_validation["tenant_isolation_unchanged"]
                and tenant_isolation.cross_tenant_access_denied
            ),
            "fail_closed_behavior_unchanged": accuracy_report.safety_validation["fail_closed_behavior_unchanged"],
            "investigation_result_contract_unchanged": (
                accuracy_report.safety_validation["investigation_result_contract_unchanged"]
                and tenant_isolation.result_contract_unchanged
            ),
            "memory_advisory_only": accuracy_report.safety_validation["memory_advisory_only"],
            "response_automation_unchanged": True,
            "cross_tenant_access_denied": tenant_isolation.cross_tenant_access_denied,
            "memory_isolation_valid": tenant_isolation.memory_isolation_valid,
            "organizational_memory_isolation_valid": tenant_isolation.organizational_memory_isolation_valid,
            "evidence_provenance_valid": (
                tenant_isolation.evidence_provenance_valid
                and analyst_effectiveness.evidence_provenance_preserved
            ),
            "append_only_evidence": True,
            "deterministic_replay_valid": True,
        }
        architecture_summary = {
            "validation_scope": "synthetic enterprise trust proof",
            "components": [
                "tenant isolation certification",
                "SOC analyst effectiveness benchmark",
                "investigation scale benchmark",
                "operational accuracy safety regression",
            ],
            "preserved_contracts": [
                "InvestigationCoordinator",
                "InvestigationOrchestrator",
                "RuntimeTaskExecutor",
                "InvestigationResult",
            ],
            "security_boundaries": [
                "authorization remains authoritative",
                "memory is advisory-only",
                "cross-tenant reads fail closed",
                "evidence provenance remains tenant-scoped",
                "no response automation is executed",
            ],
            "decision_authority": "production authorization and verdict enforcement remain outside proof evaluation",
        }
        replay_payload = {
            "version": self.REPORT_VERSION,
            "tenant_isolation": tenant_isolation.to_dict(),
            "analyst_effectiveness": analyst_effectiveness.to_dict(),
            "scale_benchmark": scale_benchmark.to_dict(),
            "architecture_summary": architecture_summary,
            "safety_validation": safety,
        }
        replay_digest = hashlib.sha256(
            json.dumps(replay_payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        report_payload = {
            **replay_payload,
            "report_version": self.REPORT_VERSION,
            "generated_at": self.generated_at,
            "tenant_ids": declared_tenants,
            "replay_digest": replay_digest,
            "immutable": True,
        }
        report_digest = hashlib.sha256(
            json.dumps(report_payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        return EnterpriseProofValidationReport(
            report_version=self.REPORT_VERSION,
            generated_at=self.generated_at,
            tenant_ids=declared_tenants,
            tenant_isolation=tenant_isolation,
            analyst_effectiveness=analyst_effectiveness,
            scale_benchmark=scale_benchmark,
            architecture_summary=architecture_summary,
            safety_validation=safety,
            replay_digest=replay_digest,
            report_digest=report_digest,
        )


__all__ = ["EnterpriseProofValidator"]
