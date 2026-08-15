from flask import Flask
from services.intelligence.command_center import AnalystEventFeed
from services.intelligence.command_center.api import create_command_center_blueprint

def test_event_feed_filters_order_deduplicates_and_isolates():
    feed=AnalystEventFeed(); a=feed.record("a","risk_increased","RISK","Risk increased",source_domain="risk",source_reference="r1",severity="high",timestamp="2026-01-02T00:00:00Z",provenance={"source":"risk"},navigation_target={"target_type":"risk"}); feed.record("a","risk_increased","RISK","Risk increased",source_domain="risk",source_reference="r1",severity="high",timestamp="2026-01-02T00:00:00Z")
    feed.record("b","risk_increased","RISK","Other",source_domain="risk",source_reference="r2",timestamp="2026-01-03T00:00:00Z")
    assert len(feed.events("a",severity="high"))==1 and feed.events("a")[0].provenance and feed.events("b")[0].tenant_id=="b" and feed.events("a",since="2026-01-01T00:00:00Z")[0].event_id==a.event_id

def test_acknowledgement_is_not_resolution_and_unavailable_context_is_safe():
    feed=AnalystEventFeed(); event=feed.record("a","evidence_unavailable","EVIDENCE","Evidence unavailable",source_reference="e1",uncertainty="UNKNOWN"); feed.acknowledge("a",event.event_id)
    assert feed.get("a",event.event_id).acknowledgement=="acknowledged" and feed.copilot_context("a",event.event_id)["tts_enabled"] is False and feed.get("b",event.event_id) is None

def test_polling_api_requires_tenant_resolver_and_preserves_event_context():
    feed=AnalystEventFeed(); event=feed.record("a","investigation_updated","INVESTIGATION","Investigation updated",source_reference="i1",confidence=.8)
    app=Flask(__name__); app.register_blueprint(create_command_center_blueprint(tenant_resolver=lambda:"a",event_feed=feed)); response=app.test_client().get("/api/command-center/events"); assert response.status_code==200 and response.json["events"][0]["event_id"]==event.event_id
