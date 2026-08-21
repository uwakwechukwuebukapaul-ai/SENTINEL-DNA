"""Lifecycle contracts for persisted provider observations.

Lifecycle metadata is deliberately separate from ProviderObservation content
integrity.  The observation digest remains a digest of immutable provider
content; lifecycle transitions are recorded in the repository audit table.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Mapping

from .canonical import canonical_json, sha256_digest
from .evidence.tenant_bound_adapter import TenantBoundEvidenceAdapter


LIFECYCLE_SCHEMA_VERSION = "provider-observation-lifecycle-v1"
AUDIT_SCHEMA_VERSION = "provider-observation-lifecycle-audit-v1"


class ProviderObservationLifecycleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"


class ProviderObservationLifecycleError(ValueError):
    """Raised when lifecycle state or transition validation fails."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: Any, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ProviderObservationLifecycleError(f"lifecycle {field} is invalid") from exc
    if parsed.tzinfo is None:
        raise ProviderObservationLifecycleError(f"lifecycle {field} must be timezone-aware")
    return parsed


def _timestamp(value: datetime, field: str = "timestamp") -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ProviderObservationLifecycleError(f"lifecycle {field} must be timezone-aware")
    return value.isoformat()


def _safe_text(value: Any, field: str, *, required: bool = True, limit: int = 512) -> str | None:
    if value is None and not required:
        return None
    safe = TenantBoundEvidenceAdapter()._safe_value(str(value), key=field) if value is not None else None
    if not isinstance(safe, str) or not safe.strip() or len(safe.strip()) > limit:
        raise ProviderObservationLifecycleError(f"lifecycle {field} is invalid")
    return safe.strip()


def _safe_reason(value: Any) -> str:
    return _safe_text(value, "reason", limit=512) or ""


@dataclass(frozen=True)
class ProviderObservationRetentionPolicy:
    """Explicit, injectable freshness and retention boundaries.

    ``None`` disables a boundary.  No production duration is invented here;
    callers must supply policy values from their existing configuration layer.
    """

    stale_after_seconds: int | None = None
    retention_seconds: int | None = None
    audit_retention_seconds: int | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "stale_after_seconds",
            "retention_seconds",
            "audit_retention_seconds",
        ):
            value = getattr(self, field_name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise ProviderObservationLifecycleError(f"retention {field_name} is invalid")

    @staticmethod
    def _observed_at(observation: Any) -> datetime:
        return _parse_timestamp(observation.observed_at, "observed_at")

    def stale_at(self, observation: Any) -> datetime | None:
        candidates: list[datetime] = []
        normalized = observation.normalized_observation
        provider_expiry = normalized.get("expires_at") if isinstance(normalized, Mapping) else None
        if provider_expiry:
            candidates.append(_parse_timestamp(provider_expiry, "provider_expiration"))
        if self.stale_after_seconds is not None:
            candidates.append(self._observed_at(observation) + timedelta(seconds=self.stale_after_seconds))
        return min(candidates) if candidates else None

    def expires_at(self, observation: Any) -> datetime | None:
        if self.retention_seconds is None:
            return None
        return self._observed_at(observation) + timedelta(seconds=self.retention_seconds)

    def classify(self, observation: Any, as_of: datetime) -> ProviderObservationLifecycleStatus:
        reference = _parse_timestamp(_timestamp(as_of), "as_of")
        retention_boundary = self.expires_at(observation)
        if retention_boundary is not None and reference >= retention_boundary:
            return ProviderObservationLifecycleStatus.EXPIRED
        stale_boundary = self.stale_at(observation)
        if observation.status == "stale" or (stale_boundary is not None and reference >= stale_boundary):
            return ProviderObservationLifecycleStatus.STALE
        return ProviderObservationLifecycleStatus.ACTIVE


@dataclass(frozen=True)
class ProviderObservationLifecycleRecord:
    observation_id: str
    tenant_id: str
    case_id: str
    correlation_id: str | None
    actor_id: str | None
    provider_name: str
    status: str
    observed_at: str
    stale_at: str | None
    expires_at: str | None
    invalidated_at: str | None
    invalidated_by: str | None
    invalidation_reason: str | None
    updated_at: str
    schema_version: str = LIFECYCLE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _safe_text(self.observation_id, "observation_id")
        _safe_text(self.tenant_id, "tenant_id")
        _safe_text(self.case_id, "case_id")
        _safe_text(self.provider_name, "provider_name")
        if self.status not in {item.value for item in ProviderObservationLifecycleStatus}:
            raise ProviderObservationLifecycleError("lifecycle status is invalid")
        _parse_timestamp(self.observed_at, "observed_at")
        _parse_timestamp(self.updated_at, "updated_at")
        for field_name in ("stale_at", "expires_at", "invalidated_at"):
            value = getattr(self, field_name)
            if value is not None:
                _parse_timestamp(value, field_name)
        for field_name in ("correlation_id", "actor_id", "invalidated_by", "invalidation_reason"):
            value = getattr(self, field_name)
            if value is not None:
                _safe_text(value, field_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "correlation_id": self.correlation_id,
            "actor_id": self.actor_id,
            "provider_name": self.provider_name,
            "status": self.status,
            "observed_at": self.observed_at,
            "stale_at": self.stale_at,
            "expires_at": self.expires_at,
            "invalidated_at": self.invalidated_at,
            "invalidated_by": self.invalidated_by,
            "invalidation_reason": self.invalidation_reason,
            "updated_at": self.updated_at,
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class ProviderObservationLifecycleEvent:
    audit_event_id: str
    observation_id: str
    tenant_id: str
    case_id: str
    previous_status: str
    new_status: str
    actor_id: str
    correlation_id: str
    timestamp: str
    reason: str
    event_type: str
    schema_version: str = AUDIT_SCHEMA_VERSION
    event_digest: str = ""

    @classmethod
    def create(
        cls,
        *,
        observation_id: str,
        tenant_id: str,
        case_id: str,
        previous_status: str,
        new_status: str,
        actor_id: str,
        correlation_id: str,
        timestamp: datetime,
        reason: str,
        event_type: str,
    ) -> "ProviderObservationLifecycleEvent":
        values = {
            "observation_id": _safe_text(observation_id, "observation_id"),
            "tenant_id": _safe_text(tenant_id, "tenant_id"),
            "case_id": _safe_text(case_id, "case_id"),
            "previous_status": _safe_text(previous_status, "previous_status"),
            "new_status": _safe_text(new_status, "new_status"),
            "actor_id": _safe_text(actor_id, "actor_id"),
            "correlation_id": _safe_text(correlation_id, "correlation_id"),
            "timestamp": _timestamp(timestamp),
            "reason": _safe_reason(reason),
            "event_type": _safe_text(event_type, "event_type"),
        }
        identity = {"schema_version": AUDIT_SCHEMA_VERSION, **values}
        digest = sha256_digest(identity)
        return cls(
            audit_event_id=f"POLE-{digest[:24]}",
            **values,
            event_digest=digest,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "audit_event_id": self.audit_event_id,
            "observation_id": self.observation_id,
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "reason": self.reason,
            "event_type": self.event_type,
        }

    def verify(self) -> bool:
        if self.schema_version != AUDIT_SCHEMA_VERSION:
            raise ProviderObservationLifecycleError("lifecycle audit schema is invalid")
        if self.previous_status not in {item.value for item in ProviderObservationLifecycleStatus}:
            raise ProviderObservationLifecycleError("lifecycle audit previous status is invalid")
        if self.new_status not in {item.value for item in ProviderObservationLifecycleStatus}:
            raise ProviderObservationLifecycleError("lifecycle audit new status is invalid")
        expected_digest = sha256_digest({"schema_version": self.schema_version, **{key: value for key, value in self._payload().items() if key not in {"audit_event_id", "schema_version"}}})
        if self.event_digest != expected_digest or self.audit_event_id != f"POLE-{expected_digest[:24]}":
            raise ProviderObservationLifecycleError("lifecycle audit integrity verification failed")
        return True

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "event_digest": self.event_digest}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProviderObservationLifecycleEvent":
        required = (
            "audit_event_id", "observation_id", "tenant_id", "case_id",
            "previous_status", "new_status", "actor_id", "correlation_id",
            "timestamp", "reason", "event_type", "event_digest",
        )
        if not isinstance(value, Mapping) or any(not value.get(key) for key in required):
            raise ProviderObservationLifecycleError("lifecycle audit event is incomplete")
        event = cls(
            audit_event_id=_safe_text(value["audit_event_id"], "audit_event_id"),
            observation_id=_safe_text(value["observation_id"], "observation_id"),
            tenant_id=_safe_text(value["tenant_id"], "tenant_id"),
            case_id=_safe_text(value["case_id"], "case_id"),
            previous_status=_safe_text(value["previous_status"], "previous_status"),
            new_status=_safe_text(value["new_status"], "new_status"),
            actor_id=_safe_text(value["actor_id"], "actor_id"),
            correlation_id=_safe_text(value["correlation_id"], "correlation_id"),
            timestamp=_safe_text(value["timestamp"], "timestamp"),
            reason=_safe_reason(value["reason"]),
            event_type=_safe_text(value["event_type"], "event_type"),
            schema_version=value.get("schema_version", AUDIT_SCHEMA_VERSION),
            event_digest=_safe_text(value["event_digest"], "event_digest"),
        )
        event.verify()
        return event
