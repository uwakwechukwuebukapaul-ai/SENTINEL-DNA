from flask import Flask

from services.intelligence.command_center.api import create_command_center_blueprint
from services.intelligence.command_center.event_feed import AnalystEventFeed
from services.intelligence.command_center.attention_service import AnalystAttentionService

def sources(tenant, kind, reference):
    rows={
        ("a","investigation","i1"): {"tenant_id":"a","investigation_id":"i1","status":"active","evidence_references":["e1"],"provenance":{"source":"investigation"}},
        ("a","evidence","e1"): {"tenant_id":"a","evidence_id":"e1","status":"available","provenance":{"source":"evidence"}},
    }
    return rows.get((tenant,kind,reference))

def test_workspace_composes_tenant_scoped_investigation_and_evidence():
    feed=AnalystEventFeed(); feed.record("a","investigation_updated","investigation","Updated",related={"investigation_id":"i1"},uncertainty="KNOWN")
    app=Flask(__name__); app.register_blueprint(create_command_center_blueprint(tenant_resolver=lambda:"a",source_resolver=sources,event_feed=feed,attention_service=AnalystAttentionService(feed)))
    response=app.test_client().get("/api/command-center/investigation/i1/workspace")
    assert response.status_code==200 and response.json["investigation"]["investigation_id"]=="i1" and response.json["evidence"][0]["evidence_id"]=="e1"

def test_workspace_isolation_and_missing_investigation():
    app=Flask(__name__); app.register_blueprint(create_command_center_blueprint(tenant_resolver=lambda:"b",source_resolver=sources))
    client=app.test_client()
    assert client.get("/api/command-center/investigation/i1/workspace").status_code==404
    assert client.get("/api/command-center/investigation/missing/workspace").status_code==404

def test_workspace_blueprint_registration_isolated():
    first=Flask("first"); second=Flask("second")
    first.register_blueprint(create_command_center_blueprint(tenant_resolver=lambda:"a",source_resolver=sources))
    second.register_blueprint(create_command_center_blueprint(tenant_resolver=lambda:"a",source_resolver=sources))
    assert first.test_client().get("/api/command-center/investigation/i1/workspace").status_code==200
    assert second.test_client().get("/api/command-center/investigation/i1/workspace").status_code==200
