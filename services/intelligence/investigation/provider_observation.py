"""Trusted, normalized provider observations for Investigator V1 replay."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from .canonical import canonical_json, freeze, sha256_digest, thaw
from .evidence.tenant_bound_adapter import TenantBoundEvidenceAdapter


OBSERVATION_SCHEMA_VERSION = "provider-observation-v1"
_ALLOWED_STATUS = frozenset({"success", "partial", "stale", "unavailable", "invalid"})
_PROVENANCE_KEYS = frozenset(
    {
        "source",
        "source_reference",
        "provider",
        "provider_version",
        "observation_type",
        "gateway_correlation_id",
    }
)


class ProviderObservationIntegrityError(ValueError):
    """Raised when a provider observation is missing, unsafe, or modified."""


def _safe_text(value: Any, field: str) -> str:
    safe = TenantBoundEvidenceAdapter()._safe_value(str(value), key=field) if value is not None else None
    if not isinstance(safe, str) or not safe.strip():
        raise ProviderObservationIntegrityError(f"provider observation {field} is invalid")
    return safe.strip()


def _iso(value: Any, field: str) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ProviderObservationIntegrityError(f"provider observation {field} must be timezone-aware")
    return value.isoformat()


def _safe_sequence(value: Any, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise ProviderObservationIntegrityError(f"provider observation {field} is invalid")
    values = []
    for item in value:
        values.append(_safe_text(item, field))
    return tuple(sorted(set(values)))


def _datetime_from_iso(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ProviderObservationIntegrityError(f"provider observation {field} is invalid") from exc
    if parsed.tzinfo is None:
        raise ProviderObservationIntegrityError(f"provider observation {field} must be timezone-aware")
    return parsed


def _without_none(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _without_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, (list, tuple)):
        return [_without_none(item) for item in value]
    return value


@dataclass(frozen=True)
class ProviderObservation:
    """Immutable normalized provider output suitable for tenant-scoped replay."""

    observation_id: str
    tenant_id: str
    case_id: str
    correlation_id: str | None
    actor_id: str | None
    provider_name: str
    provider_version: str | None
    observation_type: str
    source: str
    source_reference: str
    observed_at: str
    status: str
    normalized_observation: Mapping[str, Any]
    provenance: Mapping[str, Any]
    evidence_references: tuple[str, ...]
    integrity_digest: str
    schema_version: str = OBSERVATION_SCHEMA_VERSION
    invalidated: bool = False

    @classmethod
    def from_provider_result(
        cls,
        provider_result: Any,
        *,
        audit: Any,
        tenant_id: str,
        case_id: str,
        actor_id: str,
        correlation_id: str | None,
    ) -> "ProviderObservation":
        provider = getattr(provider_result, "provider", None)
        provider_name = _safe_text(getattr(provider, "name", None), "provider_name")
        provider_version = getattr(provider, "version", None)
        if provider_version is not None:
            provider_version = _safe_text(provider_version, "provider_version")
        if getattr(audit, "tenant_id", tenant_id) != tenant_id:
            raise ProviderObservationIntegrityError("provider observation tenant mismatch")
        if getattr(audit, "actor_id", actor_id) != actor_id:
            raise ProviderObservationIntegrityError("provider observation actor mismatch")
        contacted_providers = tuple(getattr(audit, "contacted_providers", ()) or ())
        if contacted_providers and provider_name not in contacted_providers:
            raise ProviderObservationIntegrityError("provider observation provider is not in gateway audit")
        audit_correlation = getattr(audit, "correlation_id", None)
        if correlation_id and audit_correlation not in (None, correlation_id):
            raise ProviderObservationIntegrityError("provider observation correlation mismatch")

        observation = getattr(provider_result, "observation", None)
        error = getattr(provider_result, "error", None)
        if observation is not None:
            observed_provider = getattr(observation, "provider", None)
            if getattr(observed_provider, "name", None) != provider_name:
                raise ProviderObservationIntegrityError("provider observation identity mismatch")
            observed_at = _iso(getattr(observation, "retrieved_at", None), "observed_at")
            source_reference = getattr(observation, "provider_record", None) or f"gateway:{provider_name}"
            status = "stale" if getattr(observation, "stale", False) else str(getattr(observation, "provider_status", "success")).lower()
            if getattr(observation, "partial", False) and status == "success":
                status = "partial"
            normalized = cls._normalize_observation(observation)
            if normalized.get("ioc") != cls._normalize_ioc(getattr(audit, "ioc", None)):
                raise ProviderObservationIntegrityError("provider observation IOC mismatch")
        else:
            observed_at = _iso(getattr(audit, "completed_at", None), "observed_at")
            source_reference = f"gateway:{provider_name}"
            code = getattr(getattr(error, "code", None), "value", getattr(error, "code", "unavailable"))
            status = "invalid" if str(code) == "normalization_error" else "unavailable"
            normalized = {
                "ioc": cls._normalize_ioc(getattr(audit, "ioc", None)),
                "error": {
                    "code": _safe_text(code, "error_code"),
                    "retryable": bool(getattr(error, "retryable", False)),
                },
            }
        if status not in _ALLOWED_STATUS:
            raise ProviderObservationIntegrityError("provider observation status is invalid")

        source = "threat_intelligence_gateway"
        provenance = {
            "source": source,
            "source_reference": _safe_text(source_reference, "source_reference"),
            "provider": provider_name,
            "observation_type": "threat_intelligence",
            **({"provider_version": provider_version} if provider_version else {}),
            **({"gateway_correlation_id": correlation_id} if correlation_id else {}),
        }
        identity = {
            "tenant_id": str(tenant_id),
            "case_id": str(case_id),
            "correlation_id": correlation_id,
            "actor_id": str(actor_id),
            "provider_name": provider_name,
            "provider_version": provider_version,
            "observation_type": "threat_intelligence",
            "source_reference": provenance["source_reference"],
            "observed_at": observed_at,
            "status": status,
            "ioc": normalized.get("ioc", {}),
            "normalized_observation": normalized,
        }
        observation_id = f"PO-{sha256_digest(identity)[:24]}"
        evidence_references = (f"provider-observation:{observation_id}",)
        candidate = cls(
            observation_id=observation_id,
            tenant_id=str(tenant_id),
            case_id=str(case_id),
            correlation_id=correlation_id,
            actor_id=str(actor_id),
            provider_name=provider_name,
            provider_version=provider_version,
            observation_type="threat_intelligence",
            source=source,
            source_reference=provenance["source_reference"],
            observed_at=observed_at,
            status=status,
            normalized_observation=freeze(normalized),
            provenance=freeze(provenance),
            evidence_references=evidence_references,
            integrity_digest="pending",
        )
        return replace(candidate, integrity_digest=sha256_digest(candidate._content_payload()))

    @staticmethod
    def _normalize_ioc(ioc: Any) -> dict[str, str]:
        if ioc is None:
            raise ProviderObservationIntegrityError("provider observation IOC is required")
        return {
            "type": _safe_text(getattr(getattr(ioc, "type", None), "value", getattr(ioc, "type", None)), "ioc_type"),
            "value": _safe_text(getattr(ioc, "value", None), "ioc_value"),
        }

    @classmethod
    def _normalize_observation(cls, observation: Any) -> dict[str, Any]:
        normalized: dict[str, Any] = {
            "ioc": cls._normalize_ioc(getattr(observation, "ioc", None)),
            "provider_record": (
                _safe_text(observation.provider_record, "provider_record")
                if observation.provider_record
                else None
            ),
            "reputation": (
                _safe_text(observation.reputation, "reputation")
                if observation.reputation
                else None
            ),
            "malicious_score": observation.malicious_score,
            "suspicious_score": observation.suspicious_score,
            "confidence": observation.confidence,
            "observation_count": observation.observation_count,
            "tags": _safe_sequence(observation.tags, "tags"),
            "malware_families": _safe_sequence(observation.malware_families, "malware_families"),
            "threat_actors": _safe_sequence(observation.threat_actors, "threat_actors"),
            "campaigns": _safe_sequence(observation.campaigns, "campaigns"),
            "related_infrastructure": _safe_sequence(observation.related_infrastructure, "related_infrastructure"),
            "attack_techniques": _safe_sequence(observation.attack_techniques, "attack_techniques"),
            "source_timestamp": _iso(observation.source_timestamp, "source_timestamp") if observation.source_timestamp else None,
            "expires_at": _iso(observation.expires_at, "expires_at") if observation.expires_at else None,
            "provider_status": _safe_text(observation.provider_status, "provider_status"),
            "partial": bool(observation.partial),
        }
        return normalized

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "correlation_id": self.correlation_id,
            "actor_id": self.actor_id,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "observation_type": self.observation_type,
            "source_reference": self.source_reference,
            "observed_at": self.observed_at,
            "status": self.status,
            "ioc": self.normalized_observation.get("ioc", {}),
            "normalized_observation": self.normalized_observation,
        }

    def _content_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "observation_id": self.observation_id,
            "identity": self._identity_payload(),
            "observed_at": self.observed_at,
            "status": self.status,
            "normalized_observation": self.normalized_observation,
            "provenance": self.provenance,
            "evidence_references": self.evidence_references,
        }

    def verify(self) -> bool:
        if self.invalidated:
            raise ProviderObservationIntegrityError("provider observation is invalidated")
        if self.schema_version != OBSERVATION_SCHEMA_VERSION:
            raise ProviderObservationIntegrityError("provider observation schema is invalid")
        if self.status not in _ALLOWED_STATUS:
            raise ProviderObservationIntegrityError("provider observation status is invalid")
        if self.evidence_references != (f"provider-observation:{self.observation_id}",):
            raise ProviderObservationIntegrityError("provider observation evidence reference is invalid")
        if (
            self.provenance.get("provider") != self.provider_name
            or self.provenance.get("source") != self.source
            or self.provenance.get("source_reference") != self.source_reference
        ):
            raise ProviderObservationIntegrityError("provider observation provenance is inconsistent")
        expected_id = f"PO-{sha256_digest(self._identity_payload())[:24]}"
        if self.observation_id != expected_id:
            raise ProviderObservationIntegrityError("provider observation identity is invalid")
        expected_digest = sha256_digest(self._content_payload())
        if self.integrity_digest != expected_digest:
            raise ProviderObservationIntegrityError("provider observation integrity digest mismatch")
        return True

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProviderObservation":
        if not isinstance(value, Mapping):
            raise ProviderObservationIntegrityError("provider observation must be structured")
        required = ("observation_id", "tenant_id", "case_id", "provider_name", "observation_type", "source", "source_reference", "observed_at", "status", "normalized_observation", "provenance", "evidence_references", "integrity_digest")
        if any(not value.get(key) for key in required):
            raise ProviderObservationIntegrityError("provider observation is incomplete")
        normalized = value["normalized_observation"]
        provenance = value["provenance"]
        if not isinstance(normalized, Mapping) or not isinstance(provenance, Mapping):
            raise ProviderObservationIntegrityError("provider observation data is invalid")
        safe_normalized = TenantBoundEvidenceAdapter()._safe_mapping(normalized)
        safe_provenance = TenantBoundEvidenceAdapter()._safe_mapping(provenance)
        if canonical_json(_without_none(normalized)) != canonical_json(_without_none(safe_normalized)):
            raise ProviderObservationIntegrityError("provider observation contains sensitive data")
        if canonical_json(provenance) != canonical_json({key: item for key, item in safe_provenance.items() if key in _PROVENANCE_KEYS}):
            raise ProviderObservationIntegrityError("provider observation provenance is invalid")
        candidate = cls(
            observation_id=_safe_text(value["observation_id"], "observation_id"),
            tenant_id=_safe_text(value["tenant_id"], "tenant_id"),
            case_id=_safe_text(value["case_id"], "case_id"),
            correlation_id=_safe_text(value["correlation_id"], "correlation_id") if value.get("correlation_id") else None,
            actor_id=_safe_text(value["actor_id"], "actor_id") if value.get("actor_id") else None,
            provider_name=_safe_text(value["provider_name"], "provider_name"),
            provider_version=_safe_text(value["provider_version"], "provider_version") if value.get("provider_version") else None,
            observation_type=_safe_text(value["observation_type"], "observation_type"),
            source=_safe_text(value["source"], "source"),
            source_reference=_safe_text(value["source_reference"], "source_reference"),
            observed_at=_safe_text(value["observed_at"], "observed_at"),
            status=_safe_text(value["status"], "status"),
            normalized_observation=freeze(normalized),
            provenance=freeze({key: item for key, item in safe_provenance.items() if key in _PROVENANCE_KEYS}),
            evidence_references=tuple(sorted(set(_safe_text(item, "evidence_reference") for item in value["evidence_references"]))),
            integrity_digest=_safe_text(value["integrity_digest"], "integrity_digest"),
            schema_version=value.get("schema_version", OBSERVATION_SCHEMA_VERSION),
            invalidated=bool(value.get("invalidated", False)),
        )
        if (
            candidate.provenance.get("provider") != candidate.provider_name
            or candidate.provenance.get("source") != candidate.source
            or candidate.provenance.get("source_reference") != candidate.source_reference
        ):
            raise ProviderObservationIntegrityError("provider observation provenance is inconsistent")
        candidate.verify()
        return candidate

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "correlation_id": self.correlation_id,
            "actor_id": self.actor_id,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "observation_type": self.observation_type,
            "source": self.source,
            "source_reference": self.source_reference,
            "observed_at": self.observed_at,
            "status": self.status,
            "normalized_observation": thaw(self.normalized_observation),
            "provenance": thaw(self.provenance),
            "evidence_references": list(self.evidence_references),
            "integrity_digest": self.integrity_digest,
            "schema_version": self.schema_version,
            "invalidated": self.invalidated,
        }

    def to_evidence(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_references[0],
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
            "source": self.source,
            "source_type": "provider_observation",
            "evidence_type": self.observation_type,
            "status": self.status,
            "provenance": {
                "source": self.source,
                "source_type": "provider_observation",
                "observation_id": self.observation_id,
                "observation_digest": self.integrity_digest,
                "provider_name": self.provider_name,
                **({"provider_version": self.provider_version} if self.provider_version else {}),
            },
            "value": thaw(self.normalized_observation),
        }
