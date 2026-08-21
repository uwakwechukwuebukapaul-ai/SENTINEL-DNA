"""Tenant-scoped, analyst-safe projection for provider observation lifecycle data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .canonical import freeze, thaw
from .provider_observation import (
    ProviderObservation,
    ProviderObservationIntegrityError,
)
from .provider_observation_lifecycle import (
    ProviderObservationLifecycleEvent,
    ProviderObservationLifecycleRecord,
    ProviderObservationLifecycleStatus,
)


class ProviderObservationProjectionError(ValueError):
    """Raised when a provider observation cannot be safely projected."""


@dataclass(frozen=True)
class ProviderObservationAuditProjection:
    """Safe, immutable lifecycle-audit representation for analysts."""

    audit_event_id: str
    previous_status: str
    new_status: str
    actor_id: str
    timestamp: str
    reason: str
    correlation_id: str

    @classmethod
    def from_event(cls, event: ProviderObservationLifecycleEvent) -> "ProviderObservationAuditProjection":
        event.verify()
        return cls(
            audit_event_id=event.audit_event_id,
            previous_status=event.previous_status,
            new_status=event.new_status,
            actor_id=event.actor_id,
            timestamp=event.timestamp,
            reason=event.reason,
            correlation_id=event.correlation_id,
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "audit_event_id": self.audit_event_id,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "actor_id": self.actor_id,
            "timestamp": self.timestamp,
            "reason": self.reason,
            "correlation_id": self.correlation_id,
        }


@dataclass(frozen=True)
class ProviderObservationAnalystProjection:
    """Read-only safe DTO; raw ProviderObservation data never leaves this boundary."""

    observation_id: str
    case_id: str
    provider: str | None
    observation_type: str | None
    status: str
    lifecycle_status: str
    observed_at: str | None
    stale_at: str | None
    expires_at: str | None
    invalidated_at: str | None
    invalidated_by: str | None
    invalidation_reason: str | None
    correlation_id: str | None
    provenance: Mapping[str, Any]
    provenance_status: str
    integrity_status: str
    integrity_digest: str | None
    evidence_references: tuple[str, ...]
    replay_eligible: bool
    lifecycle_audit: tuple[ProviderObservationAuditProjection, ...]

    @staticmethod
    def _provenance(observation: ProviderObservation) -> tuple[dict[str, Any], str]:
        value = observation.provenance
        if not isinstance(value, Mapping):
            return {"status": "unavailable"}, "unavailable"
        provider = value.get("provider")
        source = value.get("source")
        if provider != observation.provider_name or not isinstance(source, str) or not source.strip():
            return {"status": "invalid"}, "invalid"
        summary: dict[str, Any] = {
            "provider": provider,
            "source": source,
            "observation_type": observation.observation_type,
            "status": "verified",
        }
        if observation.provider_version:
            summary["provider_version"] = observation.provider_version
        return summary, "verified"

    @classmethod
    def from_record(
        cls,
        observation: ProviderObservation,
        lifecycle: ProviderObservationLifecycleRecord,
        events: Iterable[ProviderObservationLifecycleEvent] = (),
    ) -> "ProviderObservationAnalystProjection":
        if lifecycle.observation_id != observation.observation_id:
            raise ProviderObservationProjectionError("provider observation lifecycle identity mismatch")
        if lifecycle.tenant_id != observation.tenant_id or lifecycle.case_id != observation.case_id:
            raise ProviderObservationProjectionError("provider observation lifecycle scope mismatch")
        if lifecycle.provider_name != observation.provider_name:
            raise ProviderObservationProjectionError("provider observation provider mismatch")
        try:
            observation.verify()
        except ProviderObservationIntegrityError:
            # Keep the response safe if a caller supplies a tampered in-memory
            # object to this adapter.  Repository-backed reads fail closed before
            # reaching this branch.
            return cls(
                observation_id=str(observation.observation_id),
                case_id=str(observation.case_id),
                provider=None,
                observation_type=None,
                status="invalid",
                lifecycle_status="INVALIDATED",
                observed_at=None,
                stale_at=None,
                expires_at=None,
                invalidated_at=None,
                invalidated_by=None,
                invalidation_reason=None,
                correlation_id=None,
                provenance=freeze({"status": "unavailable"}),
                provenance_status="unavailable",
                integrity_status="invalid",
                integrity_digest=None,
                evidence_references=(),
                replay_eligible=False,
                lifecycle_audit=(),
            )
        provenance, provenance_status = cls._provenance(observation)
        audit_items = []
        for event in sorted(events, key=lambda item: (item.timestamp, item.audit_event_id)):
            if (
                event.observation_id != observation.observation_id
                or event.tenant_id != observation.tenant_id
                or event.case_id != observation.case_id
            ):
                raise ProviderObservationProjectionError("provider observation audit scope mismatch")
            audit_items.append(ProviderObservationAuditProjection.from_event(event))
        audit = tuple(audit_items)
        lifecycle_status = lifecycle.status
        return cls(
            observation_id=observation.observation_id,
            case_id=observation.case_id,
            provider=observation.provider_name,
            observation_type=observation.observation_type,
            status=observation.status,
            lifecycle_status=lifecycle.status,
            observed_at=observation.observed_at,
            stale_at=lifecycle.stale_at,
            expires_at=lifecycle.expires_at,
            invalidated_at=lifecycle.invalidated_at,
            invalidated_by=lifecycle.invalidated_by,
            invalidation_reason=lifecycle.invalidation_reason,
            correlation_id=observation.correlation_id,
            provenance=freeze(provenance),
            provenance_status=provenance_status,
            integrity_status="verified",
            integrity_digest=observation.integrity_digest,
            evidence_references=tuple(sorted(observation.evidence_references)),
            replay_eligible=lifecycle_status in {
                ProviderObservationLifecycleStatus.ACTIVE.value,
                ProviderObservationLifecycleStatus.STALE.value,
            },
            lifecycle_audit=audit,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "case_id": self.case_id,
            "provider": self.provider,
            "observation_type": self.observation_type,
            "status": self.status,
            "observed_at": self.observed_at,
            "lifecycle": {
                "status": self.lifecycle_status,
                "stale_at": self.stale_at,
                "expires_at": self.expires_at,
                "invalidated_at": self.invalidated_at,
                "invalidated_by": self.invalidated_by,
                "invalidation_reason": self.invalidation_reason,
            },
            "correlation_id": self.correlation_id,
            "provenance": thaw(self.provenance),
            "provenance_status": self.provenance_status,
            "integrity": {
                "status": self.integrity_status,
                "verified": self.integrity_status == "verified",
                "digest": self.integrity_digest,
            },
            "integrity_status": self.integrity_status,
            "integrity_verified": self.integrity_status == "verified",
            "integrity_digest": self.integrity_digest,
            "evidence_references": list(self.evidence_references),
            "replay_eligible": self.replay_eligible,
            "lifecycle_audit": [event.to_dict() for event in self.lifecycle_audit],
        }

class ProviderObservationAnalystProjectionService:
    """Authorized adapter from repository records to analyst-safe DTOs."""

    def __init__(self, repository: Any):
        self.repository = repository

    def for_case(
        self,
        *,
        tenant_id: str,
        case_id: str,
        actor_id: str,
        authorization_context: Any,
    ) -> list[dict[str, Any]]:
        records = self.repository.get_analyst_records_for_tenant(
            tenant_id=tenant_id,
            case_id=case_id,
            actor_id=actor_id,
            authorization_context=authorization_context,
        )
        return [
            ProviderObservationAnalystProjection.from_record(observation, lifecycle, events).to_dict()
            for observation, lifecycle, events in records
        ]

    def for_case_page(
        self,
        *,
        tenant_id: str,
        case_id: str,
        actor_id: str,
        authorization_context: Any,
        page_size: int,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Return one authorized live keyset page without changing the list contract."""
        page = self.repository.get_analyst_page_for_tenant(
            tenant_id=tenant_id,
            case_id=case_id,
            actor_id=actor_id,
            authorization_context=authorization_context,
            page_size=page_size,
            cursor=cursor,
        )
        observations = [
            ProviderObservationAnalystProjection.from_record(observation, lifecycle, events).to_dict()
            for observation, lifecycle, events in page.records
        ]
        return {
            "provider_observations": observations,
            "pagination": {
                "page_size": page.page_size,
                "has_more": page.has_more,
                "next_cursor": page.next_cursor,
                "ordering": page.ordering,
                "complete": page.complete,
            },
        }


__all__ = [
    "ProviderObservationAnalystProjection",
    "ProviderObservationAnalystProjectionService",
    "ProviderObservationAuditProjection",
    "ProviderObservationProjectionError",
]
