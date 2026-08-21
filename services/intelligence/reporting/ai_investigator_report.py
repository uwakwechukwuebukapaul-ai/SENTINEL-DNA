"""Read-only V4 report projection over canonical investigation outputs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.core.serialization import serialize
from services.intelligence.reporting.investigation_report import InvestigationReportGenerator


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


def _first(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return default


@dataclass(frozen=True)
class InvestigationReportProjection:
    """Stable analyst report contract assembled from existing read-only outputs."""

    investigation_id: str
    tenant_id: str
    executive_summary: Any
    severity: Any
    confidence: Any
    risk: Any
    timeline: list[Any]
    evidence_summary: Any
    ioc_intelligence: list[Any]
    mitre_mappings: list[Any]
    ai_reasoning: Any
    recommendations: list[Any]
    analyst_actions: list[Any]
    relationships: list[Any]
    report: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "investigation_id": self.investigation_id,
            "tenant_id": self.tenant_id,
            "executive_summary": self.executive_summary,
            "severity": self.severity,
            "confidence": self.confidence,
            "risk": self.risk,
            "timeline": self.timeline,
            "evidence_summary": self.evidence_summary,
            "ioc_intelligence": self.ioc_intelligence,
            "mitre_mappings": self.mitre_mappings,
            "ai_reasoning": self.ai_reasoning,
            "recommendations": self.recommendations,
            "analyst_actions": self.analyst_actions,
            "relationships": self.relationships,
            "report": self.report,
        }


class AIInvestigatorReportService:
    """Compose a report without executing or duplicating investigation workflow."""

    def __init__(self, report_generator: InvestigationReportGenerator | None = None):
        self.report_generator = report_generator or InvestigationReportGenerator()

    def build(self, coordinator: Any, investigation_id: str, tenant_id: str, security_context: Any) -> InvestigationReportProjection | None:
        try:
            snapshot = coordinator.get_investigation_view(investigation_id, security_context)
        except (LookupError, PermissionError, ValueError):
            return None
        if not snapshot:
            return None
        snapshot = serialize(snapshot) or {}
        report_source = serialize(coordinator.get_report_by_case_id(investigation_id, tenant_id)) or {}
        intelligence = serialize(coordinator.intelligence_repository.get_by_case_id(investigation_id)) or {}
        investigation = snapshot.get("investigation") or {}
        summary = snapshot.get("summary") or {}
        source = {**intelligence, **report_source}
        source.setdefault("case_id", investigation.get("case_id") or investigation_id)
        source.setdefault("status", investigation.get("status"))
        source.setdefault("confidence", summary.get("confidence"))
        source.setdefault("risk_score", summary.get("risk"))
        source.setdefault("findings", snapshot.get("findings", []))
        source.setdefault("evidence", snapshot.get("evidence", []))
        source.setdefault("mitre", snapshot.get("mitre", []))
        source.setdefault("timeline", snapshot.get("timeline", []))
        source.setdefault("recommendations", snapshot.get("recommendations", []))

        # Use the canonical report model; this adapter only projects its result.
        report = self.report_generator.generate_from_read_model(snapshot)
        report_data = serialize(report) or {}
        risk = _first(report_source.get("risk"), source.get("risk"), {"score": report_data.get("risk_score", 0)}, default={})
        provider_observations = _first(
            source.get("provider_observations"),
            source.get("threat_intelligence_report"),
            (source.get("intelligence") or {}).get("provider_observations") if isinstance(source.get("intelligence"), dict) else None,
            default=[],
        )
        relationships = _first(
            report_source.get("relationships"),
            intelligence.get("relationships"),
            source.get("relationship_graph"),
            source.get("security_graph_context"),
            default=[],
        )
        evidence = _list(_first(report_source.get("evidence"), snapshot.get("evidence"), intelligence.get("evidence"), default=[]))
        recommendations = _list(_first(report_source.get("recommendations"), snapshot.get("recommendations"), default=[]))
        actions = _list(_first(report_source.get("analyst_actions"), source.get("analyst_actions"), report_source.get("governance", {}).get("analyst_actions") if isinstance(report_source.get("governance"), dict) else None, default=[]))
        reasoning = _first(report_source.get("reasoning_report"), source.get("reasoning_report"), source.get("reasoning"), default="No AI reasoning explanation is available.")
        executive_summary = _first(report_source.get("summary"), summary.get("decision"), reasoning.get("summary") if isinstance(reasoning, dict) else None, default="No executive summary is available.")
        evidence_summary = _first(report_source.get("evidence_summary"), source.get("evidence_summary"), {"count": len(evidence), "references": evidence}, default={})
        severity = _first(report_source.get("severity"), source.get("risk_severity"), risk.get("severity") if isinstance(risk, dict) else None, default="unknown")
        confidence = _first(report_source.get("confidence"), summary.get("confidence"), source.get("confidence"), default=0)
        timeline = _list(_first(report_source.get("timeline"), snapshot.get("timeline"), source.get("timeline"), default=[]))
        mitre = _list(_first(report_source.get("mitre"), snapshot.get("mitre"), source.get("mitre_techniques"), default=[]))
        return InvestigationReportProjection(
            investigation_id=str(investigation.get("id") or investigation_id), tenant_id=str(tenant_id),
            executive_summary=executive_summary, severity=severity, confidence=confidence, risk=risk,
            timeline=timeline, evidence_summary=evidence_summary, ioc_intelligence=_list(provider_observations) or _list(source.get("iocs") or snapshot.get("iocs")),
            mitre_mappings=mitre, ai_reasoning=reasoning, recommendations=recommendations,
            analyst_actions=actions, relationships=_list(relationships), report=report_data,
        )
