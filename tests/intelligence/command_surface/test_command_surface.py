from services.intelligence.command_surface import CommandSurfaceService

def test_snapshot_attention_decisions_and_evidence_boundary():
    s=CommandSurfaceService(); snap=s.build_snapshot("a", {"subsystem_availability":{"Evidence":"DEGRADED","Risk":"AVAILABLE"},"attention":[{"severity":"critical","category":"RISK","evidence_references":["e1"],"provenance":{"source":"risk"}}],"decisions":[{"category":"GOVERNANCE","title":"Review governance decision","confidence":None}]})
    assert snap.tenant_id=="a" and snap.attention_items[0].priority=="high" and snap.decision_items[0].uncertainty=="UNKNOWN"
    assert s.get_subsystem_status("a")["Evidence"]=="DEGRADED" and s.normalize_evidence({})["available"] is False

def test_tenant_isolation_history_determinism_and_human_boundary():
    s=CommandSurfaceService(); s.build_attention_queue("a",[{"tenant_id":"a","severity":"high"},{"tenant_id":"b","severity":"critical"}]); s.build_snapshot("a",{"attention":[{"tenant_id":"a","severity":"high"}]})
    assert len(s.get_attention_items("a"))==1 and s.get_attention_items("b")==[] and len(s.get_historical_snapshot("a"))==1
    x=s.get_attention_items("a")[0]; assert x.requires_human_review and x.advisory if hasattr(x,"advisory") else x.requires_human_review
