"""Consumer-facing projections over canonical investigation artifacts."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def project_artifacts(artifacts: list[dict[str, Any]] | None) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for artifact in artifacts or []:
        if isinstance(artifact, dict):
            payload = dict(artifact.get("payload") or {})
            payload.setdefault("artifact_id", artifact.get("artifact_id"))
            payload.setdefault("evidence_refs", artifact.get("evidence_refs", []))
            payload.setdefault("provenance", artifact.get("provenance", {}))
            payload.setdefault("confidence", artifact.get("confidence"))
            grouped[str(artifact.get("artifact_type"))].append(payload)
    confidence = grouped.get("confidence_assessment", [])
    risk = grouped.get("risk_assessment", [])
    return {
        "findings": grouped.get("finding", []),
        "recommendations": grouped.get("recommendation", []),
        "iocs": grouped.get("ioc", []),
        "mitre": grouped.get("mitre_technique", []),
        "timeline": grouped.get("timeline_event", []),
        "risk": risk[0] if risk else {},
        "confidence": (confidence[0].get("score") if confidence else None),
        "artifacts": artifacts or [],
    }
