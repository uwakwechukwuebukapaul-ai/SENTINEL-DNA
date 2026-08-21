"""Stable, evidence-backed investigation artifact contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from services.intelligence.investigation.canonical import canonical_json, sha256_digest


ARTIFACT_TYPES = frozenset({
    "finding", "recommendation", "ioc", "mitre_technique",
    "timeline_event", "risk_assessment", "confidence_assessment",
})


@dataclass(frozen=True)
class InvestigationArtifact:
    artifact_id: str
    investigation_id: str
    case_id: str
    tenant_id: str | None
    artifact_type: str
    payload: dict[str, Any]
    evidence_refs: tuple[str, ...]
    provenance: dict[str, Any]
    confidence: float | None
    source: str
    created_at: str

    @classmethod
    def create(
        cls,
        *,
        investigation_id: str,
        case_id: str,
        tenant_id: str | None,
        artifact_type: str,
        payload: dict[str, Any],
        evidence_refs: list[str] | tuple[str, ...] = (),
        provenance: dict[str, Any] | None = None,
        confidence: float | None = None,
        source: str = "investigation_artifact_builder",
        created_at: str | None = None,
        ordinal: int = 0,
    ) -> "InvestigationArtifact":
        if artifact_type not in ARTIFACT_TYPES:
            raise ValueError("unsupported investigation artifact type")
        investigation_id = str(investigation_id or "").strip()
        case_id = str(case_id or "").strip()
        if not investigation_id or not case_id:
            raise ValueError("investigation_id and case_id are required")
        refs = tuple(sorted({str(ref) for ref in evidence_refs if ref}))
        safe_confidence = None if confidence is None else max(0.0, min(1.0, float(confidence)))
        safe_payload = dict(payload or {})
        safe_provenance = dict(provenance or {})
        identity = {
            "investigation_id": investigation_id,
            "case_id": case_id,
            "tenant_id": tenant_id,
            "artifact_type": artifact_type,
            "payload": safe_payload,
            "evidence_refs": refs,
            "provenance": safe_provenance,
            "confidence": safe_confidence,
            "source": str(source or "investigation_artifact_builder"),
            "ordinal": int(ordinal),
        }
        artifact_id = "ART-" + sha256_digest(identity)[:24]
        return cls(
            artifact_id=artifact_id,
            investigation_id=investigation_id,
            case_id=case_id,
            tenant_id=str(tenant_id) if tenant_id else None,
            artifact_type=artifact_type,
            payload=safe_payload,
            evidence_refs=refs,
            provenance=safe_provenance,
            confidence=safe_confidence,
            source=str(source or "investigation_artifact_builder"),
            created_at=created_at or datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "investigation_id": self.investigation_id,
            "case_id": self.case_id,
            "tenant_id": self.tenant_id,
            "artifact_type": self.artifact_type,
            "payload": dict(self.payload),
            "evidence_refs": list(self.evidence_refs),
            "provenance": dict(self.provenance),
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at,
        }
