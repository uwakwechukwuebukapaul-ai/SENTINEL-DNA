"""Immutable, deterministic input snapshots for Investigator V1."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .canonical import canonical_json as _canonical
from .canonical import freeze as _freeze
from .canonical import sha256_digest
from .canonical import thaw as _thaw
from .evidence.tenant_bound_adapter import TenantBoundEvidenceAdapter


SNAPSHOT_VERSION = "investigator-v1-input-snapshot-1"
_MISSING = object()


class SnapshotIntegrityError(ValueError):
    """Raised when a trusted investigation snapshot cannot be verified."""


def _safe_input(value: Any, *, key: str) -> Any:
    adapter = TenantBoundEvidenceAdapter()
    safe = adapter._safe_value(value, key=key)
    if safe is None and value is not None:
        raise SnapshotIntegrityError(f"snapshot {key} cannot be trusted")
    return safe


def _safe_mapping(value: Any, *, key: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise SnapshotIntegrityError(f"snapshot {key} must be structured")
    safe = _safe_input(value, key=key)
    if not isinstance(safe, Mapping):
        raise SnapshotIntegrityError(f"snapshot {key} cannot be trusted")
    return dict(safe)


def _deterministic_sequence(value: Any, *, key: str) -> list[Any]:
    safe = _safe_input(list(value or []), key=key)
    if not isinstance(safe, list):
        raise SnapshotIntegrityError(f"snapshot {key} cannot be trusted")
    ordered = sorted(safe, key=_canonical)
    unique: dict[str, Any] = {}
    for item in ordered:
        unique.setdefault(_canonical(item), item)
    return list(unique.values())


@dataclass(frozen=True)
class InvestigationSnapshot:
    """The exact safe, trusted input envelope used for an investigation."""

    snapshot_id: str
    digest: str
    case_id: str
    tenant_id: str
    actor_id: str | None
    correlation_id: str | None
    evidence: tuple[Mapping[str, Any], ...]
    artifacts: tuple[Any, ...]
    alert: Mapping[str, Any]
    iocs: tuple[Any, ...]
    timeline: tuple[Any, ...]
    investigation_config: Mapping[str, Any]
    invalidated: bool = False
    invalidation_reason: str | None = None
    provider_observation_references: tuple[str, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        case_id: str,
        tenant_id: str,
        actor_id: str | None,
        correlation_id: str | None,
        evidence: Any,
        artifacts: Any,
        alert: Any,
        iocs: Any,
        timeline: Any,
        plan: Any,
        intelligence_metadata: Mapping[str, Any] | None = None,
        provider_observation_references: Any = None,
    ) -> "InvestigationSnapshot":
        case = str(case_id or "").strip()
        tenant = str(tenant_id or "").strip()
        if not case or not tenant:
            raise SnapshotIntegrityError("snapshot tenant and case are required")

        safe_evidence = _safe_input(list(evidence or []), key="evidence")
        if not isinstance(safe_evidence, list) or any(not isinstance(item, Mapping) for item in safe_evidence):
            raise SnapshotIntegrityError("snapshot evidence cannot be trusted")
        references = [str(item.get("evidence_id") or "").strip() for item in safe_evidence]
        if any(not reference for reference in references):
            raise SnapshotIntegrityError("snapshot evidence reference is required")
        if len(set(references)) != len(references):
            raise SnapshotIntegrityError("snapshot duplicate evidence reference")
        if references != sorted(references):
            raise SnapshotIntegrityError("snapshot evidence ordering is not deterministic")

        safe_artifacts = _deterministic_sequence(artifacts, key="artifacts")
        safe_alert = _safe_mapping(alert or {}, key="alert")
        safe_iocs = _deterministic_sequence(iocs, key="iocs")
        safe_timeline = _deterministic_sequence(timeline, key="timeline")
        safe_plan = _safe_mapping(
            plan.to_dict() if hasattr(plan, "to_dict") else plan or {},
            key="plan",
        )
        safe_intelligence = cls._safe_intelligence_metadata(intelligence_metadata or {})
        provider_references = tuple(sorted(set(str(item) for item in (provider_observation_references or []))))
        if any(not item for item in provider_references):
            raise SnapshotIntegrityError("snapshot provider observation reference is invalid")
        config = {
            "normalization_version": SNAPSHOT_VERSION,
            "plan": safe_plan,
            "intelligence": safe_intelligence,
        }

        snapshot = cls(
            snapshot_id="pending",
            digest="pending",
            case_id=case,
            tenant_id=tenant,
            actor_id=str(actor_id) if actor_id else None,
            correlation_id=str(correlation_id) if correlation_id else None,
            evidence=tuple(_freeze(item) for item in safe_evidence),
            artifacts=tuple(_freeze(item) for item in (safe_artifacts or [])),
            alert=_freeze(safe_alert),
            iocs=tuple(_freeze(item) for item in (safe_iocs or [])),
            timeline=tuple(_freeze(item) for item in (safe_timeline or [])),
            investigation_config=_freeze(config),
            provider_observation_references=provider_references,
        )
        digest = sha256_digest(snapshot._payload())
        snapshot = cls(
            **{
                **snapshot.__dict__,
                "snapshot_id": f"IS-{digest[:16]}",
                "digest": digest,
            }
        )
        snapshot.verify()
        return snapshot

    @staticmethod
    def _safe_intelligence_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
        allowed: dict[str, Any] = {}
        for key in (
            "statuses",
            "disposition",
            "intelligence_provenance",
            "fusion",
            "fusion_results",
        ):
            if key not in value:
                continue
            if key in {"statuses", "fusion_results"}:
                allowed[key] = _deterministic_sequence(value[key], key=key)
            else:
                allowed[key] = value[key]
        safe = _safe_input(allowed, key="intelligence_metadata")
        return dict(safe) if isinstance(safe, Mapping) else {}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InvestigationSnapshot":
        """Rehydrate only a snapshot whose stored digest still verifies."""
        if not isinstance(value, Mapping):
            raise SnapshotIntegrityError("snapshot must be structured")
        if value.get("snapshot_version") != SNAPSHOT_VERSION:
            raise SnapshotIntegrityError("unsupported investigation snapshot version")
        if value.get("invalidated"):
            raise SnapshotIntegrityError("investigation snapshot is invalidated")

        raw_evidence = list(value.get("evidence") or [])
        raw_artifacts = list(value.get("artifacts") or [])
        raw_alert = value.get("alert") or {}
        raw_iocs = list(value.get("iocs") or [])
        raw_timeline = list(value.get("timeline") or [])
        raw_config = value.get("investigation_config") or {}
        evidence = _safe_input(raw_evidence, key="evidence")
        artifacts = _safe_input(raw_artifacts, key="artifacts")
        alert = _safe_mapping(raw_alert, key="alert")
        iocs = _safe_input(raw_iocs, key="iocs")
        timeline = _safe_input(raw_timeline, key="timeline")
        config = _safe_mapping(raw_config, key="investigation_config")
        provider_references = tuple(sorted(set(str(item) for item in (value.get("provider_observation_references") or []))))
        if any(not item for item in provider_references):
            raise SnapshotIntegrityError("snapshot provider observation reference is invalid")
        for key, raw, safe in (
            ("evidence", raw_evidence, evidence),
            ("artifacts", raw_artifacts, artifacts),
            ("alert", raw_alert, alert),
            ("iocs", raw_iocs, iocs),
            ("timeline", raw_timeline, timeline),
            ("investigation_config", raw_config, config),
        ):
            if _canonical(raw) != _canonical(safe):
                raise SnapshotIntegrityError(f"snapshot {key} contains untrusted fields")
        if artifacts != sorted(artifacts, key=_canonical):
            raise SnapshotIntegrityError("snapshot artifacts ordering is not deterministic")
        if iocs != sorted(iocs, key=_canonical):
            raise SnapshotIntegrityError("snapshot iocs ordering is not deterministic")
        if timeline != sorted(timeline, key=_canonical):
            raise SnapshotIntegrityError("snapshot timeline ordering is not deterministic")
        evidence_references = [str(item.get("evidence_id") or "") for item in evidence]
        if (
            evidence_references != sorted(evidence_references)
            or len(set(evidence_references)) != len(evidence_references)
        ):
            raise SnapshotIntegrityError("snapshot evidence ordering is not deterministic")
        snapshot = cls(
            snapshot_id=str(value.get("snapshot_id") or ""),
            digest=str(value.get("digest") or ""),
            case_id=str(value.get("case_id") or ""),
            tenant_id=str(value.get("tenant_id") or ""),
            actor_id=str(value["actor_id"]) if value.get("actor_id") else None,
            correlation_id=str(value["correlation_id"]) if value.get("correlation_id") else None,
            evidence=tuple(_freeze(item) for item in (evidence or [])),
            artifacts=tuple(_freeze(item) for item in (artifacts or [])),
            alert=_freeze(alert),
            iocs=tuple(_freeze(item) for item in (iocs or [])),
            timeline=tuple(_freeze(item) for item in (timeline or [])),
            investigation_config=_freeze(config),
            provider_observation_references=provider_references,
        )
        snapshot.verify()
        return snapshot

    def _payload(self) -> dict[str, Any]:
        payload = {
            "snapshot_version": SNAPSHOT_VERSION,
            "case_id": self.case_id,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
            "evidence": self.evidence,
            "artifacts": self.artifacts,
            "alert": self.alert,
            "iocs": self.iocs,
            "timeline": self.timeline,
            "investigation_config": self.investigation_config,
        }
        if self.provider_observation_references:
            payload["provider_observation_references"] = self.provider_observation_references
        return payload

    def verify(self) -> bool:
        if self.invalidated:
            raise SnapshotIntegrityError("investigation snapshot is invalidated")
        expected_digest = sha256_digest(self._payload())
        if self.digest != expected_digest or self.snapshot_id != f"IS-{expected_digest[:16]}":
            raise SnapshotIntegrityError("investigation snapshot integrity verification failed")
        return True

    def verify_scope(
        self,
        *,
        tenant_id: str,
        case_id: str,
        actor_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self.verify()
        if str(tenant_id or "") != self.tenant_id:
            raise PermissionError("snapshot tenant does not match investigation tenant")
        if str(case_id or "") != self.case_id:
            raise PermissionError("snapshot case does not match investigation case")
        if actor_id and self.actor_id and str(actor_id) != self.actor_id:
            raise PermissionError("snapshot actor does not match investigation actor")
        if correlation_id and self.correlation_id and str(correlation_id) != self.correlation_id:
            raise PermissionError("snapshot correlation does not match investigation correlation")

    def replay_inputs(
        self,
        *,
        tenant_id: str,
        case_id: str,
        actor_id: str | None = None,
        correlation_id: str | None = None,
        evidence: Any = _MISSING,
    ) -> dict[str, Any]:
        """Return verified inputs, optionally checking current evidence identity."""
        self.verify_scope(
            tenant_id=tenant_id,
            case_id=case_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
        )
        if evidence is not _MISSING:
            normalized = TenantBoundEvidenceAdapter().adapt(
                evidence,
                case_id=self.case_id,
                tenant_id=self.tenant_id,
                actor_id=self.actor_id,
                correlation_id=self.correlation_id,
            )
            if _canonical(normalized) != _canonical(self.evidence):
                raise SnapshotIntegrityError("replay evidence does not match trusted snapshot")
        return {
            "case_id": self.case_id,
            "alert": _thaw(self.alert),
            "artifacts": _thaw(self.artifacts),
            "evidence": _thaw(self.evidence),
            "iocs": _thaw(self.iocs),
            "timeline": _thaw(self.timeline),
            "tenant_id": self.tenant_id,
            "actor_id": actor_id or self.actor_id,
            "correlation_id": correlation_id or self.correlation_id,
            "provider_observation_references": list(self.provider_observation_references),
        }

    def invalidate(self, reason: str) -> "InvestigationSnapshot":
        return InvestigationSnapshot(
            **{
                **self.__dict__,
                "invalidated": True,
                "invalidation_reason": str(reason or "snapshot invalidated"),
            }
        )

    def to_dict(self) -> dict[str, Any]:
        payload = _thaw(self._payload())
        payload.update(
            {
                "snapshot_version": SNAPSHOT_VERSION,
                "snapshot_id": self.snapshot_id,
                "digest": self.digest,
                "invalidated": self.invalidated,
                "invalidation_reason": self.invalidation_reason,
                "provider_observation_references": list(self.provider_observation_references),
            }
        )
        return payload

    def metadata(self) -> dict[str, Any]:
        return {
            "investigation_snapshot": self.to_dict(),
            "investigation_snapshot_digest": self.digest,
        }
