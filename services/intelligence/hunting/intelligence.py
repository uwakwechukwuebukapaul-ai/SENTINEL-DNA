"""Evidence-backed threat-hunting projections over canonical investigation data."""
from __future__ import annotations

import hashlib
from typing import Any, Mapping

from .models import HuntingHypothesis, IOCPivot


_ENTITY_FIELDS = {
    "user": "USER", "account": "ACCOUNT", "host": "HOST", "ip": "IP",
    "domain": "DOMAIN", "file": "FILE",
}


class ThreatHuntingIntelligenceBuilder:
    """Builds deterministic advisory hunt context; it never searches or persists."""

    @staticmethod
    def _mapping(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, Mapping) else {}

    @staticmethod
    def _scope(item: Mapping[str, Any], tenant_id: str, case_id: str) -> bool:
        item_tenant = item.get("tenant_id") or (item.get("tenant_context") or {}).get("tenant_id")
        item_case = item.get("case_id") or item.get("investigation_id")
        return item_tenant == tenant_id and (item_case in (None, case_id))

    @staticmethod
    def _evidence_reference(item: Mapping[str, Any]) -> str | None:
        value = item.get("evidence_id") or item.get("id") or item.get("reference")
        return str(value) if value else None

    def build(
        self,
        *,
        tenant_id: str | None,
        case_id: str,
        evidence: list[Any] | None = None,
        iocs: list[Any] | None = None,
        timeline: list[Any] | None = None,
        relationship_graph: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not tenant_id:
            return {"advisory_only": True, "status": "tenant_context_required", "hypotheses": [], "ioc_pivots": [], "entity_expansion": [], "threat_story": None}
        scoped_evidence = []
        entities: list[dict[str, Any]] = []
        for raw in evidence or []:
            item = self._mapping(raw)
            reference = self._evidence_reference(item)
            provenance = self._mapping(item.get("provenance"))
            source = provenance.get("source") or item.get("source")
            if not reference or not source or not self._scope(item, tenant_id, case_id):
                continue
            scoped_evidence.append(item)
            for field, entity_type in _ENTITY_FIELDS.items():
                value = item.get(field)
                if value is None:
                    continue
                entities.append({
                    "entity_type": entity_type, "entity_id": str(value), "tenant_id": tenant_id,
                    "relationship_type": "EVIDENCE_IDENTIFIES_ENTITY", "evidence_references": [reference],
                    "evidence_source": source, "provenance": provenance, "confidence": 1.0,
                })
        entities = sorted({(item["entity_type"], item["entity_id"], item["evidence_references"][0]): item for item in entities}.values(), key=lambda item: (item["entity_type"], item["entity_id"], item["evidence_references"][0]))

        graph = self._mapping(relationship_graph)
        pivots = []
        for relationship in graph.get("relationships", []) or []:
            item = self._mapping(relationship)
            if item.get("tenant_id") != tenant_id or item.get("case_id") != case_id:
                continue
            source_type, target_type = item.get("source_type"), item.get("target_type")
            if "IOC" not in {source_type, target_type}:
                continue
            refs = tuple(str(ref) for ref in item.get("evidence_refs", []) if ref)
            provenance = self._mapping(item.get("provenance"))
            evidence_source = provenance.get("source")
            if not refs or not evidence_source:
                continue
            ioc_id = str(item.get("source_id") if source_type == "IOC" else item.get("target_id"))
            related = {"entity_type": target_type if source_type == "IOC" else source_type, "entity_id": item.get("target_id") if source_type == "IOC" else item.get("source_id"), "tenant_id": tenant_id, "relationship_type": item.get("relationship_type"), "evidence_references": list(refs), "evidence_source": evidence_source, "provenance": provenance, "confidence": item.get("confidence") if isinstance(item.get("confidence"), (int, float)) else 1.0}
            related_events = [related] if related["entity_type"] == "TIMELINE_EVENT" else []
            related_entities = [] if related_events else [related]
            pivots.append(IOCPivot(ioc_id, tenant_id, tuple(related_entities), tuple(related_events), refs, str(evidence_source), provenance, float(related["confidence"])).to_dict())
        pivots.sort(key=lambda item: (item["ioc_id"], item["evidence_references"]))

        evidence_refs = tuple(sorted({self._evidence_reference(item) for item in scoped_evidence if self._evidence_reference(item)}))
        hypotheses = []
        if evidence_refs:
            sources = sorted({str(self._mapping(item.get("provenance")).get("source") or item.get("source")) for item in scoped_evidence})
            statement = "Investigate whether the evidence-linked indicators and entities represent related suspicious activity."
            digest = hashlib.sha256(f"{tenant_id}|{case_id}|{evidence_refs}".encode()).hexdigest()[:16]
            hypotheses.append(HuntingHypothesis(f"HYP-{digest}", statement, tenant_id, evidence_refs, sources[0], {"sources": sources, "case_id": case_id, "basis": "canonical_evidence"}, 0.8).to_dict())

        timeline_events = []
        for raw in timeline or []:
            item = self._mapping(raw)
            if not self._scope(item, tenant_id, case_id):
                continue
            refs = [str(ref) for ref in item.get("evidence_refs", []) if ref]
            provenance = self._mapping(item.get("provenance"))
            source = provenance.get("source") or item.get("source")
            if refs and source:
                timeline_events.append({"event_id": item.get("event_id"), "event_type": item.get("event_type"), "timestamp": item.get("timestamp"), "tenant_id": tenant_id, "evidence_references": refs, "evidence_source": source, "provenance": provenance, "confidence": item.get("confidence") if isinstance(item.get("confidence"), (int, float)) else 1.0})
        story = None
        if hypotheses or pivots or timeline_events:
            story = {"title": "Potential Threat Story", "advisory_only": True, "tenant_id": tenant_id, "summary": "Evidence-backed hunting context links the listed indicators, entities, and events; analyst review is required.", "hypothesis_ids": [item["hypothesis_id"] for item in hypotheses], "ioc_pivot_count": len(pivots), "timeline_events": timeline_events, "confidence": 0.8 if hypotheses else 0.5}
        return {"advisory_only": True, "status": "available", "tenant_id": tenant_id, "hypotheses": hypotheses, "ioc_pivots": pivots, "entity_expansion": entities, "threat_story": story}
