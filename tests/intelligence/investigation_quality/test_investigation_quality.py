from services.intelligence.investigation_quality import InvestigationQualityRepository, InvestigationQualityService
from services.intelligence.investigation.investigation_result import InvestigationResult

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
