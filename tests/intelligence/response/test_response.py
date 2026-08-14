from services.intelligence.response import IncidentResponseService
from services.intelligence.investigation.investigation_result import InvestigationResult

def test_playbook_generation():
    plan = IncidentResponseService("a").create_plan({"summary": "phishing credential attack"})
    assert plan.incident_type == "phishing" and plan.actions

def test_approval_enforcement():
    service = IncidentResponseService("a"); plan = service.create_plan({"summary": "malware"}); request = service.request_approval(plan.plan_id, "analyst")
    assert service.execute(plan.plan_id, request.request_id).status == "blocked"

def test_tenant_isolation():
    service = IncidentResponseService("a"); plan = service.create_plan({"summary": "phishing"})
    assert IncidentResponseService("b", service.repository).request_approval(plan.plan_id, "other") is None

def test_execution_simulation():
    service = IncidentResponseService("a"); plan = service.create_plan({"summary": "malware"}); request = service.request_approval(plan.plan_id, "analyst"); service.approval.decide(request, "manager", "approved"); result = service.execute(plan.plan_id, request.request_id)
    assert result.simulated is True and result.status == "simulated"

def test_backward_compatibility():
    result = InvestigationResult()
    assert result.response_context is None and "response_context" in result.to_dict()
