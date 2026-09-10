"""Stable models used by the billing entitlement validation harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BillingValidationScenario:
    scenario_id: str
    title: str
    tenant_ids: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class BillingValidationReport:
    report_version: str
    generated_at: str
    validation_result: str
    scenarios: tuple[dict[str, Any], ...]
    metrics: dict[str, int]
    security_invariants: dict[str, bool]
    evidence_policy: dict[str, Any]
    replay_digest: str
    report_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "generated_at": self.generated_at,
            "validation_result": self.validation_result,
            "scenarios": list(self.scenarios),
            "metrics": dict(sorted(self.metrics.items())),
            "security_invariants": dict(sorted(self.security_invariants.items())),
            "evidence_policy": dict(self.evidence_policy),
            "replay_digest": self.replay_digest,
            "report_digest": self.report_digest,
        }

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


@dataclass(frozen=True)
class _InvestigationFixture:
    investigation_id: str
    evidence_id: str
    tenant_id: str
    evidence_digest: str
    provenance_digest: str


@dataclass(frozen=True)
class _IdentitySnapshot:
    tenant_id: str
    actor_id: str
    tenant_status: str
    actor_status: str
    membership_role: str
    membership_status: str


@dataclass(frozen=True)
class _EntitlementSnapshot:
    tenant_id: str
    subscription_status: str | None
    plan_id: str
    capabilities: tuple[str, ...]


@dataclass(frozen=True)
class _Observation:
    identity: _IdentitySnapshot
    entitlement: _EntitlementSnapshot
    investigation: _InvestigationFixture
    access_decisions: dict[str, bool]
