from services.intelligence.platform_fabric import PlatformIntelligenceService
def sources(tenant="t"):
    return {"investigation":[{"id":"i1","entity_type":"investigation","severity":"high","confidence":.8}],"evidence":[{"id":"e1","entity_type":"evidence","severity":"medium"}],"governance_decision":[{"id":"g1","entity_type":"governance_decision","severity":"high","requires_human_review":True}]}
def test_normalization_aggregation_provenance_and_queue():
    s=PlatformIntelligenceService(); snap=s.build_snapshot("t",sources()); assert len(snap.records)==3 and len(snap.relationships)==1 and snap.attention_queue[0].requires_human_review and snap.records[0].provenance["source_subsystem"]=="investigation"
def test_tenant_isolation_and_history():
    s=PlatformIntelligenceService(); s.build_snapshot("a",sources()); s.build_snapshot("b",sources()); assert all(x.tenant_id=="a" for x in s.unified_intelligence("a")) and all(x.tenant_id=="b" for x in s.attention_queue("b")) and len(s.historical_snapshots("a"))==1
def test_partial_failure_missing_data_and_no_mutation():
    class Broken:
        subsystem="broken"
        def normalize(self,*args): raise RuntimeError("unavailable")
    s=PlatformIntelligenceService(adapters={"broken":Broken()}); payload={"id":"x","entity_type":"incident"}; snap=s.build_snapshot("t",{"broken":[payload],"incident":[payload]}); assert snap.availability["broken"]["available"] is False and payload=={"id":"x","entity_type":"incident"} and all(x.advisory for x in snap.attention_queue)
