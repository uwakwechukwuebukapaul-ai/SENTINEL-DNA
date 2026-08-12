"""Billing reconciliation contract for provider-backed subscriptions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sentinel_dna.saas.billing import BillingConfigurationError, BillingService


@dataclass(frozen=True)
class ReconciliationFinding:
    tenant_id: str
    severity: str
    reason: str
    local_status: str | None
    provider_status: str | None
    metadata: dict[str, Any]


class BillingReconciliationWorker:
    def __init__(self, billing: BillingService) -> None:
        self.billing = billing

    def reconcile_tenant(self, tenant_id: str) -> list[ReconciliationFinding]:
        local = self.billing.get_subscription(tenant_id)
        findings: list[ReconciliationFinding] = []
        if local is None:
            finding = ReconciliationFinding(tenant_id, "warning", "missing_local_subscription", None, None, {})
            self.billing.audit_reconciliation_required(tenant_id, finding.reason)
            return [finding]
        if not local.provider_subscription_id:
            finding = ReconciliationFinding(tenant_id, "warning", "missing_provider_subscription", local.status, None, {"subscription_id": local.subscription_id})
            self.billing.audit_reconciliation_required(tenant_id, finding.reason, finding.metadata)
            return [finding]
        try:
            provider = self.billing.provider.retrieve_subscription(local.provider_subscription_id)
        except BillingConfigurationError:
            raise
        provider_status = provider.get("status")
        if provider_status != local.status:
            finding = ReconciliationFinding(
                tenant_id,
                "critical" if provider_status in {"canceled", "unpaid", "past_due"} else "warning",
                "subscription_status_drift",
                local.status,
                provider_status,
                {"subscription_id": local.subscription_id, "provider_subscription_id": local.provider_subscription_id},
            )
            findings.append(finding)
            self.billing.audit_reconciliation_required(tenant_id, finding.reason, finding.metadata)
        if provider_status in {"canceled", "unpaid", "past_due"} and local.status in {"active", "trialing"}:
            finding = ReconciliationFinding(
                tenant_id,
                "critical",
                "commercial_access_requires_review",
                local.status,
                provider_status,
                {"subscription_id": local.subscription_id, "provider_subscription_id": local.provider_subscription_id},
            )
            findings.append(finding)
            self.billing.audit_reconciliation_required(tenant_id, finding.reason, finding.metadata)
        return findings
