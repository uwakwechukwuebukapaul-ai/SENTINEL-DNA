from datetime import datetime, timezone
from uuid import uuid4
from .escalation import IncidentEscalationEngine
from .lifecycle import IncidentLifecycleEngine
from .models import ClosureReport, IncidentRecord
from .repository import IncidentManagementRepository
from .sla import IncidentSLAEngine

class IncidentLifecycleService:
    def __init__(self, tenant_id=None, repository=None, audit_logger=None): self.tenant_id=tenant_id; self.repository=repository or IncidentManagementRepository(); self.audit_logger=audit_logger; self.lifecycle=IncidentLifecycleEngine(); self.sla=IncidentSLAEngine(); self.escalation=IncidentEscalationEngine()
    def _audit(self, event, **payload):
        if self.audit_logger and hasattr(self.audit_logger, "record"): self.audit_logger.record(event, tenant_id=self.tenant_id, **payload)
    def create_incident(self, title, severity="medium", business_impact="unknown", case_id=None):
        incident=self.repository.save_incident(IncidentRecord(str(uuid4()), self.tenant_id, title, severity, case_id=case_id, business_impact=business_impact)); self._audit("incident_created", incident_id=incident.incident_id); return incident
    def transition_status(self, incident_id, status, actor=None, note=""):
        incident=self.repository.get_incident(self.tenant_id, incident_id)
        if incident is None: return None
        timeline=self.lifecycle.transition(incident, status, actor, note); self.repository.add_timeline(timeline); self._audit("incident_status_transitioned", incident_id=incident_id, status=status); return incident
    def calculate_sla(self, incident_id):
        incident=self.repository.get_incident(self.tenant_id, incident_id)
        if incident is None: return None
        result=self.repository.save_sla(self.sla.calculate(incident)); self._audit("incident_sla_calculated", incident_id=incident_id); return result
    def generate_escalation(self, incident_id):
        incident=self.repository.get_incident(self.tenant_id, incident_id); sla=self.repository.slas.get(incident_id) if incident else None
        if incident is None: return None
        result=self.escalation.recommend(incident, sla or self.sla.calculate(incident)); self._audit("incident_escalation_evaluated", incident_id=incident_id, recommended=result["recommended"]); return result
    def close_incident(self, incident_id, root_cause="unknown", lessons_learned=None, recommendations=None):
        incident=self.transition_status(incident_id, "CLOSED", "system", "closure")
        if incident is None: return None
        report=self.repository.save_closure(ClosureReport(incident_id, self.tenant_id, datetime.now(timezone.utc).isoformat(), root_cause, lessons_learned or [], recommendations or [])); self._audit("incident_closed", incident_id=incident_id); return report
