from typing import Any
from .models import SOCWorkspaceSnapshot, WorkspaceCaseView, WorkspaceTimelineEntry

class SOCWorkspaceAggregator:
    """Read-only presentation adapter over existing intelligence outputs."""
    def __init__(self, components=None): self.components = components or {}
    def _get(self, name, data):
        value = data.get(name) if isinstance(data, dict) else getattr(data, name, None)
        return value.to_dict() if hasattr(value, "to_dict") else value
    def snapshot(self, investigation_id=None, case_id=None, result=None, tenant_id=None):
        data = result.to_dict() if hasattr(result, "to_dict") else (result or {})
        parts = {name: self._get(name, data) for name in ("evidence_summary", "threat_intelligence_report", "reasoning_report", "decision_report", "detection_intelligence_context", "attack_path_context", "recommendations", "soar_recommendation", "compliance_context")}
        missing = sum(value is None for value in parts.values())
        risk = data.get("risk") or {}
        severity = risk.get("severity", risk.get("level", "unknown")) if isinstance(risk, dict) else risk
        return SOCWorkspaceSnapshot(investigation_id, case_id or data.get("case_id"), severity, data.get("status", "unknown"), data.get("analyst_assignment"), data.get("summary"), parts["evidence_summary"], parts["threat_intelligence_report"], parts["reasoning_report"], parts["decision_report"], parts["detection_intelligence_context"], parts["attack_path_context"], parts["recommendations"], parts["soar_recommendation"], parts["compliance_context"], availability="partial" if missing else "complete")
    def case_view(self, case_id, result=None, tenant_id=None):
        data = result.to_dict() if hasattr(result, "to_dict") else (result or {})
        timeline = [WorkspaceTimelineEntry(**item) if isinstance(item, dict) else item for item in data.get("timeline", [])]
        return WorkspaceCaseView({"case_id": case_id, "tenant_id": tenant_id}, timeline, data.get("evidence", data.get("artifacts", [])), data.get("iocs", data.get("indicators", [])), data.get("mitre", []), data.get("ai_confidence", data.get("confidence")), data.get("risk"), "partial" if not data else "complete")
