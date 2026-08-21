from services.intelligence.investigation.intelligence_bundle import build_advisory_intelligence_bundle
from services.intelligence.memory import MemoryService
from services.intelligence.memory.repository import InvestigationMemoryRepository
from services.intelligence.planning.planner import InvestigationPlanner


def test_memory_history_is_tenant_scoped_and_bundle_is_evidence_backed():
    memory = MemoryService(InvestigationMemoryRepository())
    for tenant_id, case_id in (("tenant-a", "old-a"), ("tenant-b", "old-b")):
        memory.store_investigation_memory(
            {"case_id": case_id, "tenant_id": tenant_id, "evidence": [{"evidence_id": case_id}]},
            {"summary": "Recorded finding"}, {"status": "completed", "confidence": 0.8},
        )
    history = memory.retrieve_similar_investigations("security_investigation", tenant_id="tenant-a")
    bundle = build_advisory_intelligence_bundle(
        case_id="current", tenant_id="tenant-a", historical_records=history,
        plan=InvestigationPlanner().plan("current", {"type": "suspicious login"}),
        relationship_graph={"relationships": [{"source_type": "EVIDENCE", "source_id": "E-1", "target_type": "IOC", "target_id": "IOC:ip:1.2.3.4", "relationship_type": "EVIDENCE_SUPPORTS_IOC", "evidence_refs": ["E-1"], "provenance": {"source": "gateway"}}]},
        quality_assessment={"evidence_score": 100, "reasoning_score": 100, "confidence_score": 80},
    )
    assert [item.case_id for item in history] == ["old-a"]
    assert bundle["advisory_only"] is True
    assert bundle["historical_context"]["similar_investigations"][0]["case_id"] == "old-a"
    assert bundle["relationship_intelligence"]["relationships"][0]["evidence_references"] == ["E-1"]
    assert bundle["planning_intelligence"]["recommended_steps"]
