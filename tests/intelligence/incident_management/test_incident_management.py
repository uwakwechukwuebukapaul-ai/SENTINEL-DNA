from services.intelligence.incident_management import IncidentLifecycleService, IncidentManagementRepository
from services.intelligence.investigation.investigation_result import InvestigationResult

def test_lifecycle_transitions():
    service=IncidentLifecycleService("a"); incident=service.create_incident("Phishing", "high"); service.transition_status(incident.incident_id, "TRIAGED", "analyst"); assert service.transition_status(incident.incident_id, "INVESTIGATING").status == "INVESTIGATING"

def test_sla_calculation():
    service=IncidentLifecycleService("a"); incident=service.create_incident("Critical", "critical"); sla=service.calculate_sla(incident.incident_id); assert sla.response_deadline and sla.resolution_deadline

def test_escalation_logic():
    service=IncidentLifecycleService("a"); incident=service.create_incident("Outage", "critical", "critical"); assert service.generate_escalation(incident.incident_id)["recommended"] is True

def test_tenant_isolation():
    repository=IncidentManagementRepository(); incident=IncidentLifecycleService("a", repository).create_incident("Private"); assert IncidentLifecycleService("b", repository).calculate_sla(incident.incident_id) is None

def test_audit_hooks():
    events=[]
    class Audit:
        def record(self, event, **payload): events.append((event, payload))
    service=IncidentLifecycleService("a", audit_logger=Audit()); service.create_incident("Audited"); assert events and events[0][0] == "incident_created"

def test_backward_compatibility():
    result=InvestigationResult(); assert result.incident_management_context is None and "incident_management_context" in result.to_dict()
