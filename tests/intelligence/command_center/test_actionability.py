from types import SimpleNamespace
from flask import Flask
from services.intelligence.command_center.actionability_service import AnalystActionabilityService
from services.intelligence.command_center.api import create_command_center_blueprint

def workspace(**overrides):
    data=dict(tenant_id="a", investigation={"investigation_id":"i1","confidence":0.5}, attention={"attention_id":"at1","priority":"high","confidence":0.6}, events=[{"event_id":"e1","confidence":0.6,"provenance":{"source":"feed"}}], evidence=[{"evidence_id":"missing","status":"unavailable"}], decision={"decision_context_id":"d1","decision_state":"pending_review","uncertainty":True,"confidence":0.5}, navigation={"investigation":{"type":"investigation","reference":"i1"}}, provenance={"source":"test"}, uncertainty="evidence_unavailable", requires_human_review=True)
    data.update(overrides); return SimpleNamespace(**data)

def test_actionability_is_deterministic_and_advisory():
    service=AnalystActionabilityService(); first=[x.to_dict() for x in service.derive(workspace())]; second=[x.to_dict() for x in service.derive(workspace())]
    assert first==second and [x["category"] for x in first][:3]==["missing_evidence","high_attention","unresolved_decision"] and all(x["advisory_only"] for x in first)

def test_actionability_does_not_mutate_workspace_and_preserves_review():
    source=workspace(); before=source.__dict__.copy(); result=AnalystActionabilityService().derive(source)
    assert source.__dict__==before and any(x.reason=="human_review_required" for x in result)

def test_actionability_api_is_tenant_scoped_and_registration_safe():
    class Workspace:
        def build(self, tenant, investigation): return workspace(tenant_id=tenant) if tenant=="a" and investigation=="i1" else None
    first=Flask("one"); second=Flask("two")
    first.register_blueprint(create_command_center_blueprint(tenant_resolver=lambda:"a", investigation_workspace_service=Workspace()))
    second.register_blueprint(create_command_center_blueprint(tenant_resolver=lambda:"b", investigation_workspace_service=Workspace()))
    assert first.test_client().get("/api/command-center/investigation/i1/next-steps").status_code==200
    assert second.test_client().get("/api/command-center/investigation/i1/next-steps").status_code==404
