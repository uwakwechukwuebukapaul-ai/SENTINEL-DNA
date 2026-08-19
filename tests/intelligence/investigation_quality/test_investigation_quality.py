from services.intelligence.investigation_quality import InvestigationQualityRepository, InvestigationQualityService
from services.intelligence.investigation.investigation_result import InvestigationResult
from database.connection import DatabaseConnection

def rich(): return {"evidence":[{"id":"e1"}],"indicators":[{"value":"evil.test"}],"threat_intelligence_report":{},"reasoning_report":{},"mitre":["T1059"],"timeline":[{"id":"t1"},{"id":"t2"}],"confidence":.8}
def test_quality_scoring(): assert InvestigationQualityService("a").assess_investigation("i1",rich()).overall_score > 50
def test_tenant_isolation():
    repo=InvestigationQualityRepository(); InvestigationQualityService("a",repo).assess_investigation("i1",rich()); assert InvestigationQualityService("b",repo).generate_recommendations("i1") == []
def test_recommendations_advisory():
    service=InvestigationQualityService("a"); service.assess_investigation("i1",{}); assert service.generate_recommendations("i1") and all(item.requires_human_review for item in service.generate_recommendations("i1"))
def test_benchmark():
    service=InvestigationQualityService("a"); service.assess_investigation("i1",{}); service.assess_investigation("i2",rich()); assert service.benchmark_quality().investigation_count == 2
def test_backward_compatibility():
    result=InvestigationResult(); assert result.investigation_quality_context is None and "investigation_quality_context" in result.to_dict()

def test_quality_persists_across_repository_restart(tmp_path):
    first = InvestigationQualityRepository(DatabaseConnection(tmp_path / "quality.db"))
    result = {"case_id": "case-1", "tenant_context": {"tenant_id": "tenant-a", "actor_id": "actor-a"}, "evidence": [{"id": "e-1"}], "artifacts": [{"id": "a-1"}], "confidence": 0.8}
    assessment = InvestigationQualityService("tenant-a", first).assess_investigation("inv-1", result)
    restarted = InvestigationQualityRepository(DatabaseConnection(tmp_path / "quality.db"))
    loaded = restarted.get_assessment("tenant-a", "inv-1")
    assert loaded.quality_id == assessment.quality_id
    assert loaded.evidence_refs == ["e-1"] and loaded.artifact_refs == ["a-1"]
    assert loaded.provenance["actor_id"] == "actor-a"

def test_quality_repository_is_tenant_scoped(tmp_path):
    repository = InvestigationQualityRepository(DatabaseConnection(tmp_path / "quality.db"))
    InvestigationQualityService("tenant-a", repository).assess_investigation("inv-1", {"case_id": "case-1"})
    assert repository.get_assessment("tenant-b", "inv-1") is None
