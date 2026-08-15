from flask import Flask
from services.intelligence.command_center import DrillDownService, NavigationBuilder
from services.intelligence.command_center.api import create_command_center_blueprint

def resolver(tenant, kind, reference):
    rows={("a","investigation","i1"): {"tenant_id":"a","investigation_id":"i1","evidence_references":["e1"],"provenance":{"source":"investigation"}},("b","evidence","e1"): {"tenant_id":"b","evidence_id":"e1"}}
    return rows.get((tenant,kind,reference))

def test_navigation_and_cross_tenant_reference():
    target=NavigationBuilder().target("a","INVESTIGATION","i1",parent={"breadcrumb":[{"type":"ATTENTION","id":"a1"}]})
    assert [x["type"] for x in target.breadcrumb]==["ATTENTION","INVESTIGATION"] and DrillDownService(resolver).investigation("a","i1")["tenant_id"]=="a" and DrillDownService(resolver).evidence("a","e1")["status"]=="unavailable"

def test_api_detail_authentication_and_not_found_boundary():
    app=Flask(__name__); app.register_blueprint(create_command_center_blueprint(tenant_resolver=lambda:"a", source_resolver=resolver)); client=app.test_client()
    assert client.get("/api/command-center/investigations/i1").status_code==200 and client.get("/api/command-center/evidence/e1").status_code==200
    app2=Flask(__name__); app2.register_blueprint(create_command_center_blueprint(source_resolver=resolver)); assert app2.test_client().get("/api/command-center/investigations/i1").status_code==400
