from flask import Flask
from services.intelligence.command_center import CommandCenterRepository, SOCCommandCenterService, CommandCenterPresentationService
from services.intelligence.command_center.api import create_command_center_blueprint
from services.intelligence.investigation.investigation_result import InvestigationResult

def rows(): return [{"tenant_id":"a","investigation_id":"i1","case_id":"c1","status":"active","risk":{"severity":"critical"},"evidence":[{"id":"e1"}],"mitre":["T1059"],"threat_intelligence_report":{"threat_score":80},"vulnerabilities":[{}],"attack_paths":[{}]}]
def test_aggregation_correctness():
    snapshot=SOCCommandCenterService(CommandCenterRepository(rows()),tenant_id="a").get_snapshot(); assert snapshot.executive_posture.critical_investigations==1 and snapshot.threat_posture.mitre_techniques==["T1059"] and snapshot.threat_posture.threat_score==80
def test_tenant_isolation(): assert SOCCommandCenterService(CommandCenterRepository(rows()),tenant_id="b").get_snapshot().investigations==[]
def test_partial_failure_handling(): assert SOCCommandCenterService(CommandCenterRepository()).get_snapshot().availability=="partial"
def test_decisions_require_human_approval():
    row={"tenant_id":"a","decision_id":"d1","decision_type":"soar_approval","title":"Contain host"}; assert SOCCommandCenterService(CommandCenterRepository(rows(),[row]),tenant_id="a").get_pending_decisions()[0].requires_human_approval is True
def test_backward_compatibility():
    result=InvestigationResult(); assert result.command_center_context is None and "command_center_context" in result.to_dict()

def test_presentation_context_is_advisory_and_tts_independent():
    context=CommandCenterPresentationService().build_context("a",{"subsystem_availability":{"Evidence":"DEGRADED"}})
    assert context["tenant_id"]=="a" and context["advisory"] and context["requires_human_review"] and context["copilot_context"]["tts_enabled"] is False

def test_api_requires_existing_authenticated_tenant_resolver():
    app=Flask(__name__); app.register_blueprint(create_command_center_blueprint(CommandCenterPresentationService(), tenant_resolver=lambda:"a")); response=app.test_client().get("/api/command-center")
    assert response.status_code==200 and response.json["tenant_id"]=="a"
