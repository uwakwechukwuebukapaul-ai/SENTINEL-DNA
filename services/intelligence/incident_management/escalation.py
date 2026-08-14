from .models import EscalationRule, IncidentRecord, IncidentSLA

class IncidentEscalationEngine:
    def __init__(self, rules=None): self.rules=tuple(rules or (EscalationRule("critical-or-breach", "critical", True),))
    def recommend(self, incident: IncidentRecord, sla: IncidentSLA):
        impact=incident.business_impact.lower(); high=incident.severity.lower() in {"critical", "high"}; breached=sla.response_breached or sla.resolution_breached
        return {"incident_id": incident.incident_id, "recommended": bool(high or breached or impact in {"high", "critical"}), "reasons": [reason for reason, condition in (("high severity", high), ("SLA breach", breached), ("business impact", impact in {"high", "critical"})) if condition], "requires_human_review": True}
