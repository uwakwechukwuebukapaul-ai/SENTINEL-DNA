from services.intelligence.command_center import AnalystEventFeed, AnalystAttentionService

def test_event_to_attention_priority_provenance_and_clustering():
    feed=AnalystEventFeed(); feed.record("a","risk_increased","RISK","Risk increased",source_domain="risk",source_reference="r1",severity="high",priority="critical",confidence=.8,provenance={"source":"risk"},timestamp="2026-01-01T00:00:00Z"); feed.record("a","risk_increased","RISK","Risk increased",source_domain="risk",source_reference="r1",severity="high",priority="critical",timestamp="2026-01-02T00:00:00Z")
    service=AnalystAttentionService(feed); items=service.derive("a"); assert len(items)==1 and items[0].authoritative_priority=="critical" and items[0].provenance and items[0].recurring_count==2

def test_attention_tenant_state_and_uncertainty_boundaries():
    feed=AnalystEventFeed(); event=feed.record("a","evidence_unavailable","EVIDENCE","Evidence unavailable",source_domain="evidence",source_reference="e1",uncertainty="source_unavailable"); service=AnalystAttentionService(feed); item=service.derive("a")[0]
    assert item.requires_human_review and item.advisory and item.uncertainty=="source_unavailable" and service.get_attention("b",item.attention_id) is None
    assert service.acknowledge_attention("a",item.attention_id).state=="acknowledged" and service.get_attention("b",item.attention_id) is None
