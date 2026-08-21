"""Normalize compatibility investigation results into canonical artifacts."""

from __future__ import annotations

from typing import Any

from .models import InvestigationArtifact


class InvestigationArtifactBuilder:
    def build(self, result: Any) -> list[InvestigationArtifact]:
        data = result.to_dict() if hasattr(result, "to_dict") else dict(result or {})
        investigation_id = str(data.get("investigation_id") or data.get("case_id") or "")
        case_id = str(data.get("case_id") or investigation_id)
        tenant_context = data.get("tenant_context") if isinstance(data.get("tenant_context"), dict) else {}
        tenant_id = tenant_context.get("tenant_id")
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        normalized = (data.get("intelligence") or {}).get("normalized", {}) if isinstance(data.get("intelligence"), dict) else {}
        artifacts: list[InvestigationArtifact] = []

        def add(artifact_type: str, payload: dict[str, Any], *, refs=(), provenance=None, confidence=None, source="investigation_result"):
            artifacts.append(InvestigationArtifact.create(
                investigation_id=investigation_id, case_id=case_id, tenant_id=tenant_id,
                artifact_type=artifact_type, payload=payload, evidence_refs=list(refs),
                provenance=provenance or {}, confidence=confidence, source=source, ordinal=len(artifacts),
            ))

        for finding in data.get("findings", []) or []:
            item = finding.to_dict() if hasattr(finding, "to_dict") else (dict(finding) if isinstance(finding, dict) else {"description": str(finding)})
            refs = item.get("evidence_refs") or item.get("evidence_references") or []
            confidence = item.get("confidence", data.get("confidence"))
            provenance = item.get("intelligence_provenance") or item.get("provenance") or {"source": item.get("source", "investigation_result")}
            add("finding", {key: item[key] for key in ("title", "description", "severity", "category") if key in item}, refs=refs, provenance=provenance, confidence=confidence, source=str(item.get("source") or item.get("reasoning_type") or "investigation_result"))

        for recommendation in data.get("recommendations", []) or []:
            item = recommendation.to_dict() if hasattr(recommendation, "to_dict") else recommendation
            if isinstance(item, dict):
                payload = {key: item[key] for key in ("title", "description", "priority") if key in item}
                refs = item.get("evidence_refs") or item.get("evidence_references") or []
                provenance = item.get("provenance") or {"source": item.get("source", "investigation_result")}
            else:
                payload, refs, provenance = {"title": str(item), "description": str(item), "priority": "unknown"}, [], {"source": "investigation_result"}
            add("recommendation", payload, refs=refs, provenance=provenance, confidence=data.get("confidence"), source=str(provenance.get("source", "investigation_result")))

        iocs = data.get("iocs") or normalized.get("iocs", []) or []
        for item in iocs:
            raw = item.to_dict() if hasattr(item, "to_dict") else (dict(item) if isinstance(item, dict) else {"value": item})
            value = raw.get("value") or raw.get("indicator") or ""
            payload = {"ioc_id": str(raw.get("ioc_id") or raw.get("id") or ""), "ioc_type": str(raw.get("ioc_type") or raw.get("indicator_type") or raw.get("type") or "unknown"), "value": str(value)}
            provenance = raw.get("provenance") or raw.get("sources") or {"source": raw.get("source", "investigation_result")}
            add("ioc", payload, refs=raw.get("evidence_refs", []), provenance=provenance if isinstance(provenance, dict) else {"source": str(provenance)}, confidence=raw.get("confidence"), source="ioc_intelligence")

        techniques = data.get("mitre") or normalized.get("mitre_techniques", []) or []
        if isinstance(techniques, dict):
            techniques = techniques.get("techniques", [])
        for item in techniques:
            raw = item.to_dict() if hasattr(item, "to_dict") else (dict(item) if isinstance(item, dict) else {"technique_id": item})
            technique_id = str(raw.get("technique_id") or raw.get("id") or raw.get("value") or "")
            add("mitre_technique", {"technique_id": technique_id, "name": raw.get("name", "")}, refs=raw.get("evidence_refs", []), provenance=raw.get("provenance") or {"source": "mitre_adapter"}, confidence=raw.get("confidence", data.get("confidence")), source="mitre_adapter")

        timeline = data.get("timeline") or normalized.get("timeline", []) or []
        if isinstance(timeline, dict):
            timeline = timeline.get("events", [])
        for item in timeline:
            raw = item.to_dict() if hasattr(item, "to_dict") else (dict(item) if isinstance(item, dict) else {"description": str(item)})
            add("timeline_event", {key: raw.get(key, "") for key in ("event_id", "timestamp", "event_type", "description")}, refs=raw.get("evidence_refs", []), provenance=raw.get("provenance") or {"source": raw.get("source", "timeline_engine")}, confidence=raw.get("confidence", data.get("confidence")), source=str(raw.get("source", "timeline_engine")))

        risk = data.get("risk")
        if risk is not None:
            add("risk_assessment", dict(risk) if isinstance(risk, dict) else {"value": risk}, provenance={"source": "risk_adapter"}, confidence=(risk.get("confidence") if isinstance(risk, dict) else data.get("confidence")), source="risk_adapter")
        if data.get("confidence") is not None:
            add("confidence_assessment", {"score": data.get("confidence")}, provenance={"source": "confidence_resolver"}, confidence=data.get("confidence"), source="confidence_resolver")
        return artifacts
