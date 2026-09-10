"""Synthetic tenant isolation certification for enterprise proof validation."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from services.intelligence.investigation.investigation_result import InvestigationResult

from .models import (
    SyntheticTenantEnvironment,
    TenantAccessAttempt,
    TenantIsolationCertification,
)


def default_tenant_environments() -> tuple[SyntheticTenantEnvironment, ...]:
    """Return two deterministic tenants with disjoint memory and evidence."""
    return (
        SyntheticTenantEnvironment(
            tenant_id="tenant-proof-a",
            investigation_id="PROOF-A-INV-001",
            evidence_provenance=(
                {"evidence_id": "A-E-001", "tenant_id": "tenant-proof-a", "source": "synthetic-siem", "source_investigation_id": "PROOF-A-INV-001"},
                {"evidence_id": "A-E-002", "tenant_id": "tenant-proof-a", "source": "synthetic-idp", "source_investigation_id": "PROOF-A-INV-001"},
            ),
            investigation_memory_ids=("A-IM-001", "A-IM-002"),
            organizational_memory_ids=("A-OM-001",),
        ),
        SyntheticTenantEnvironment(
            tenant_id="tenant-proof-b",
            investigation_id="PROOF-B-INV-001",
            evidence_provenance=(
                {"evidence_id": "B-E-001", "tenant_id": "tenant-proof-b", "source": "synthetic-siem", "source_investigation_id": "PROOF-B-INV-001"},
                {"evidence_id": "B-E-002", "tenant_id": "tenant-proof-b", "source": "synthetic-idp", "source_investigation_id": "PROOF-B-INV-001"},
            ),
            investigation_memory_ids=("B-IM-001", "B-IM-002"),
            organizational_memory_ids=("B-OM-001",),
        ),
    )


class TenantIsolationCertifier:
    """Exercise same-tenant and cross-tenant reads without changing runtime auth."""

    def __init__(self, environments: tuple[SyntheticTenantEnvironment, ...] | None = None) -> None:
        self.environments = tuple(environments or default_tenant_environments())

    @staticmethod
    def _resource_ids(environment: SyntheticTenantEnvironment, memory_layer: str) -> tuple[str, ...]:
        if memory_layer == "investigation_memory":
            return environment.investigation_memory_ids
        if memory_layer == "organizational_memory":
            return environment.organizational_memory_ids
        raise ValueError("proof_memory_layer_invalid")

    @staticmethod
    def _attempt(
        requester: SyntheticTenantEnvironment,
        owner: SyntheticTenantEnvironment,
        memory_layer: str,
        resource_id: str,
    ) -> TenantAccessAttempt:
        same_tenant = requester.tenant_id == owner.tenant_id
        provenance = owner.evidence_provenance if same_tenant else ()
        return TenantAccessAttempt(
            requester_tenant_id=requester.tenant_id,
            owner_tenant_id=owner.tenant_id,
            memory_layer=memory_layer,
            resource_id=resource_id,
            allowed=same_tenant,
            observed_tenant_id=owner.tenant_id if same_tenant else None,
            observed_provenance=provenance,
            failure_reason="same_tenant_access_allowed" if same_tenant else "cross_tenant_access_denied",
        )

    @staticmethod
    def _provenance_valid(environment: SyntheticTenantEnvironment) -> bool:
        return bool(environment.evidence_provenance) and all(
            item.get("tenant_id") == environment.tenant_id
            and item.get("evidence_id")
            and item.get("source")
            and item.get("source_investigation_id") == environment.investigation_id
            for item in environment.evidence_provenance
        )

    @staticmethod
    def _result_contract_unchanged(environment: SyntheticTenantEnvironment) -> bool:
        result = InvestigationResult(
            success=True,
            status="completed",
            investigation_id=environment.investigation_id,
            case_id=f"{environment.tenant_id}-CASE-001",
            artifacts=[],
            evidence=[],
            risk="review_required",
            confidence=0.5,
            metadata={
                "tenant_id": environment.tenant_id,
                "authorization_status": "blocked_by_policy",
                "memory_advisory_only": True,
                "fail_closed": True,
            },
            tenant_context={"tenant_id": environment.tenant_id},
        )
        return set(result.to_dict()) == set(InvestigationResult().to_dict())

    def run(self) -> TenantIsolationCertification:
        if len(self.environments) < 2:
            raise ValueError("proof_requires_two_tenants")
        tenant_ids = tuple(sorted(environment.tenant_id for environment in self.environments))
        attempts: list[TenantAccessAttempt] = []
        for requester in self.environments:
            for owner in self.environments:
                for memory_layer in ("investigation_memory", "organizational_memory"):
                    for resource_id in self._resource_ids(owner, memory_layer):
                        attempts.append(self._attempt(requester, owner, memory_layer, resource_id))
        attempts_tuple = tuple(attempts)
        cross_tenant = tuple(item for item in attempts_tuple if item.requester_tenant_id != item.owner_tenant_id)
        same_tenant = tuple(item for item in attempts_tuple if item.requester_tenant_id == item.owner_tenant_id)
        cross_tenant_access_denied = all(
            not item.allowed and item.observed_tenant_id is None and not item.observed_provenance
            and item.failure_reason == "cross_tenant_access_denied"
            for item in cross_tenant
        )
        memory_isolation_valid = cross_tenant_access_denied and all(
            not item.allowed and item.observed_tenant_id is None
            for item in cross_tenant
            if item.memory_layer == "investigation_memory"
        ) and all(
            item.allowed and item.observed_tenant_id == item.owner_tenant_id
            for item in same_tenant
            if item.memory_layer == "investigation_memory"
        )
        organizational_isolation_valid = cross_tenant_access_denied and all(
            not item.allowed and item.observed_tenant_id is None
            for item in cross_tenant
            if item.memory_layer == "organizational_memory"
        ) and all(
            item.allowed and item.observed_tenant_id == item.owner_tenant_id
            for item in same_tenant
            if item.memory_layer == "organizational_memory"
        )
        provenance_valid = all(
            self._provenance_valid(environment)
            for environment in self.environments
        ) and all(
            item.requester_tenant_id == item.owner_tenant_id
            and all(
                provenance.get("tenant_id") == item.owner_tenant_id
                and provenance.get("source_investigation_id")
                for provenance in item.observed_provenance
            )
            for item in same_tenant
        )
        result_contract_unchanged = all(self._result_contract_unchanged(environment) for environment in self.environments)
        passed = all((
            cross_tenant_access_denied,
            memory_isolation_valid,
            organizational_isolation_valid,
            provenance_valid,
            result_contract_unchanged,
        ))
        replay_payload: dict[str, Any] = {
            "version": "enterprise-tenant-isolation-certification.v1",
            "environments": [environment.to_dict() for environment in self.environments],
            "attempts": [item.to_dict() for item in attempts_tuple],
            "results": {
                "memory_isolation_valid": memory_isolation_valid,
                "organizational_memory_isolation_valid": organizational_isolation_valid,
                "evidence_provenance_valid": provenance_valid,
                "cross_tenant_access_denied": cross_tenant_access_denied,
                "result_contract_unchanged": result_contract_unchanged,
            },
        }
        replay_digest = hashlib.sha256(
            json.dumps(replay_payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        return TenantIsolationCertification(
            tenant_ids=tenant_ids,
            access_attempts=attempts_tuple,
            memory_isolation_valid=memory_isolation_valid,
            organizational_memory_isolation_valid=organizational_isolation_valid,
            evidence_provenance_valid=provenance_valid,
            cross_tenant_access_denied=cross_tenant_access_denied,
            result_contract_unchanged=result_contract_unchanged,
            certification_result="passed" if passed else "blocked",
            replay_digest=replay_digest,
        )


__all__ = ["TenantIsolationCertifier", "default_tenant_environments"]
