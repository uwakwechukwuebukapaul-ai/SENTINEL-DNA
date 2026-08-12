"""Tenant-aware application service wrapping the frozen investigation core."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from time import perf_counter

from sentinel_dna.case_management.case_store import CaseStore
from sentinel_dna.evidence.evidence_engine import EvidenceEngine
from sentinel_dna.investigation import InvestigationCoordinator, InvestigationResult
from sentinel_dna.saas.auth import AuthService
from sentinel_dna.saas.billing import BillingService
from sentinel_dna.saas.identity import Role
from sentinel_dna.saas.usage import UsageMeter
from sentinel_dna.observability import ServiceMetrics


class TenantInvestigationService:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = data_dir
        self.auth = AuthService(str(data_dir))
        self.usage = UsageMeter(str(data_dir))
        self.billing = BillingService(str(data_dir))
        self.coordinator = InvestigationCoordinator(data_dir)
        self.case_store = CaseStore(data_dir)
        self.evidence_engine = EvidenceEngine(data_dir)
        self.metrics = ServiceMetrics()

    def investigate(
        self,
        user_id: str,
        tenant_id: str,
        case_id: str,
        alert: dict[str, Any],
    ) -> InvestigationResult:
        self.auth.require_minimum_role(user_id, tenant_id, Role.ANALYST)
        self.billing.enforce_entitlement(tenant_id, "investigation_started")
        try:
            existing_case = self.case_store.get(case_id)
        except FileNotFoundError:
            existing_case = None
        if existing_case is not None and existing_case.tenant_id != tenant_id:
            raise PermissionError("case is not available in this tenant")
        self.usage.record_event(tenant_id, "investigation_started", user_id=user_id, resource_type="case", resource_id=case_id)
        started = perf_counter()
        try:
            result = self.coordinator.investigate(case_id, alert)
        except Exception:
            self.metrics.record_investigation("failed", (perf_counter() - started) * 1000)
            raise
        self.metrics.record_investigation("completed", (perf_counter() - started) * 1000)
        case = self.case_store.get(case_id)
        case.tenant_id = tenant_id
        case.owner_user_id = user_id
        self.case_store.save(case)
        for evidence_id in case.evidence_ids:
            evidence = self.evidence_engine.get(evidence_id)
            evidence.tenant_id = tenant_id
            evidence.owner_user_id = user_id
            self.evidence_engine.save(evidence)
        self.usage.record_event(
            tenant_id,
            "evidence_processed",
            quantity=len(result.results.get("evidence", [])),
            user_id=user_id,
            resource_type="case",
            resource_id=case_id,
        )
        self.usage.record_event(
            tenant_id,
            "ioc_enrichment",
            quantity=len(result.results.get("iocs", [])),
            user_id=user_id,
            resource_type="case",
            resource_id=case_id,
        )
        self.usage.record_event(tenant_id, "report_generated", user_id=user_id, resource_type="case", resource_id=case_id)
        self.usage.record_event(tenant_id, "investigation_completed", user_id=user_id, resource_type="case", resource_id=case_id)
        return result

    def get_case(self, user_id: str, tenant_id: str, case_id: str):
        self.auth.require_tenant_access(user_id, tenant_id)
        return self.case_store.get_for_tenant(case_id, tenant_id)

    def get_evidence(self, user_id: str, tenant_id: str, evidence_id: str):
        self.auth.require_tenant_access(user_id, tenant_id)
        return self.evidence_engine.get_for_tenant(evidence_id, tenant_id)
