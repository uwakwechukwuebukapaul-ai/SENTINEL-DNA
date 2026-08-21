"""Advisory, evidence-backed intelligence projection for investigations.

This module composes existing intelligence services.  It neither executes
actions nor learns from investigations; every item remains traceable to the
canonical result, memory record, or relationship graph.
"""
from __future__ import annotations

from typing import Any
from services.intelligence.hunting import ThreatHuntingIntelligenceBuilder
from services.intelligence.detection_intelligence import DetectionInvestigationIntelligenceBuilder


def build_advisory_intelligence_bundle(
    *,
    case_id: str,
    tenant_id: str | None,
    historical_records: list[Any],
    plan: Any,
    relationship_graph: dict[str, Any] | None,
    quality_assessment: Any = None,
    evidence: list[Any] | None = None,
    iocs: list[Any] | None = None,
    timeline: list[Any] | None = None,
    mitre_techniques: list[Any] | None = None,
) -> dict[str, Any]:
    """Return a deterministic, presentation-safe advisory intelligence view."""
    history = []
    for record in historical_records:
        data = record.to_dict() if hasattr(record, "to_dict") else dict(record)
        if tenant_id and data.get("tenant_id") != tenant_id:
            continue
        history.append({
            "memory_id": data.get("memory_id"),
            "case_id": data.get("case_id"),
            "scenario": data.get("scenario"),
            "risk_level": data.get("risk_level"),
            "confidence": data.get("confidence"),
            "timestamp": data.get("created_at"),
            "evidence_references": list((data.get("evidence_summary") or {}).get("references") or []),
            "explanation": (data.get("reasoning_summary") or {}).get("summary") or "Historical investigation record.",
        })
    history.sort(key=lambda item: (item.get("timestamp") or "", item.get("memory_id") or ""), reverse=True)

    plan_data = plan.public() if hasattr(plan, "public") else dict(plan or {})
    graph = relationship_graph if isinstance(relationship_graph, dict) else {}
    relationships = []
    for item in graph.get("relationships", []) or []:
        if not isinstance(item, dict):
            continue
        evidence_refs = list(item.get("evidence_refs") or [])
        if not evidence_refs:
            continue
        relationships.append({
            "source": {"type": item.get("source_type"), "id": item.get("source_id")},
            "target": {"type": item.get("target_type"), "id": item.get("target_id")},
            "relationship_type": item.get("relationship_type"),
            "evidence_references": evidence_refs,
            "evidence_source": (item.get("provenance") or {}).get("source"),
            "timestamp": item.get("timestamp"),
            "explanation": "Explicit relationship supported by the listed evidence.",
        })

    assessment = quality_assessment.to_dict() if hasattr(quality_assessment, "to_dict") else dict(quality_assessment or {})
    quality = {
        "evidence_coverage": assessment.get("evidence_score"),
        "reasoning_completeness": assessment.get("reasoning_score"),
        "confidence_quality": assessment.get("confidence_score"),
        "historical_relevance": 100 if history else 0,
        "analyst_usefulness": 100 if plan_data.get("tasks") and relationships else 50 if plan_data.get("tasks") or relationships else 0,
    }
    hunting_intelligence = ThreatHuntingIntelligenceBuilder().build(
        tenant_id=tenant_id, case_id=case_id, evidence=evidence, iocs=iocs,
        timeline=timeline, relationship_graph=graph,
    )
    detection_intelligence = DetectionInvestigationIntelligenceBuilder().build(
        tenant_id=tenant_id, case_id=case_id, evidence=evidence, timeline=timeline,
        mitre_techniques=mitre_techniques,
    )
    return {
        "advisory_only": True,
        "tenant_id": tenant_id,
        "case_id": case_id,
        "historical_context": {"similar_investigations": history, "recurring_indicators": []},
        "relationship_intelligence": {"related_entities": [], "relationships": relationships},
        "threat_hunting_intelligence": hunting_intelligence,
        "detection_intelligence": detection_intelligence,
        "planning_intelligence": {
            "recommended_steps": list(plan_data.get("tasks") or plan_data.get("steps") or []),
            "reasoning": plan_data.get("objective") or "Deterministic investigation plan.",
            "confidence": plan_data.get("confidence"),
        },
        "copilot_context": {
            "supported_questions": [
                "Why is this risky?", "What evidence supports this?",
                "Have we seen this before?", "What should I investigate next?",
            ],
            "evidence_references": sorted({ref for item in relationships for ref in item["evidence_references"]}),
        },
        "intelligence_quality": quality,
    }
