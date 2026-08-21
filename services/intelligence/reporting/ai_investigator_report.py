"""Read-only report projection over canonical investigation state."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.core.serialization import serialize


def _items(value: Any) -> list[Any]:
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


@dataclass(frozen=True)
class InvestigationReportProjection:
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

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class AIInvestigatorReportService:
    """Project persisted coordinator/read-model data without executing work."""

    def build(self, coordinator: Any, investigation_id: str, tenant_id: str, context: Any) -> InvestigationReportProjection | None:
        try:
            view = coordinator.get_investigation_view(investigation_id, context)
        except (LookupError, PermissionError, ValueError):
            return None
        if not view:
            return None
        view = serialize(view) or {}
        report = serialize(coordinator.get_report_by_case_id(investigation_id, tenant_id)) or {}
        scoped_intelligence = getattr(coordinator.intelligence_repository, "get_by_case_id_for_tenant", None)
        intelligence_record = scoped_intelligence(investigation_id, tenant_id) if callable(scoped_intelligence) else None
        intelligence = serialize(intelligence_record) or {}
        investigation = view.get("investigation") or {}
        summary = view.get("summary") or {}
        source = {**intelligence, **report}
        risk = report.get("risk") if isinstance(report.get("risk"), dict) else {"score": source.get("risk_score", 0)}
        evidence = report.get("evidence") or intelligence.get("evidence") or view.get("evidence") or []
        reasoning = report.get("reasoning_report") or source.get("reasoning_report") or "No AI reasoning explanation is available."
        return InvestigationReportProjection(
            investigation_id=str(investigation.get("id") or investigation_id), tenant_id=str(tenant_id),
            executive_summary=report.get("summary") or summary.get("decision") or "No executive summary is available.",
            severity=report.get("severity") or source.get("risk_severity") or "unknown",
            confidence=report.get("confidence", summary.get("confidence", source.get("confidence", 0))), risk=risk,
            timeline=_items(report.get("timeline") or intelligence.get("timeline") or view.get("timeline")),
            evidence_summary={"count": len(_items(evidence)), "items": _items(evidence)},
            ioc_intelligence=_items(report.get("provider_observations") or report.get("iocs") or intelligence.get("iocs")),
            mitre_mappings=_items(report.get("mitre") or intelligence.get("mitre_techniques")), ai_reasoning=reasoning,
            recommendations=_items(report.get("recommendations") or intelligence.get("recommendations")),
            analyst_actions=_items(report.get("analyst_actions")),
            relationships=_items(report.get("relationships") or intelligence.get("relationships")),
        )
