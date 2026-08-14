from .models import DecisionQueueItem, ExecutivePostureSummary, InvestigationOverview, SOCCommandSnapshot, ThreatPostureView

class SOCCommandCenterAggregator:
    """Deterministic, read-only aggregation across existing intelligence outputs."""
    def __init__(self, components=None): self.components = components or {}
    def _overview(self, row):
        evidence = row.get("evidence", row.get("artifacts", [])) or []
        risk = row.get("risk") or {}
        severity = risk.get("severity", risk.get("level", row.get("severity", "unknown"))) if isinstance(risk, dict) else risk
        return InvestigationOverview(str(row.get("investigation_id", "")), row.get("case_id"), row.get("status", "unknown"), severity, row.get("summary"), len(evidence), row.get("ai_confidence", row.get("confidence")), risk)
    def aggregate(self, tenant_id=None, investigations=None, decisions=None):
        rows = investigations or []; items = []
        for row in rows:
            try: items.append(self._overview(row))
            except Exception: continue
        techniques = sorted({str(t) for row in rows for t in (row.get("mitre", []) or [])})
        threat_scores = [float((row.get("threat_intelligence_report") or {}).get("threat_score", 0)) for row in rows if isinstance(row.get("threat_intelligence_report"), dict)]
        posture = ThreatPostureView(sum(threat_scores) / len(threat_scores) if threat_scores else 0.0, techniques, sum(len(row.get("vulnerabilities", []) or []) for row in rows), sum(len(row.get("attack_paths", []) or []) for row in rows), "partial" if not rows else "complete")
        queue = [DecisionQueueItem(**{key: value for key, value in item.items() if key in DecisionQueueItem.__dataclass_fields__}) for item in (decisions or [])]
        executive = ExecutivePostureSummary(len(items), sum(item.severity == "critical" for item in items), len(queue), posture.threat_score, {"available": any("detection" in row for row in rows)}, {"available": any("agent" in row for row in rows)}, "partial" if not rows else "complete")
        return SOCCommandSnapshot(tenant_id, investigations=items, threat_posture=posture, executive_posture=executive, pending_decisions=queue, availability="partial" if not rows else "complete")
