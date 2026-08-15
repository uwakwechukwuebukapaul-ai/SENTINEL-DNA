from services.automation_intelligence import AutomationIntelligenceService
def test_learning_performance_and_advisory_recommendation():
    s=AutomationIntelligenceService(); s.record_experience("t1","w","phishing","high","success","APPROVED"); s.record_experience("t1","w","phishing","high","failed","REJECTED"); p=s.measure_performance("t1","w"); assert p.execution_count==2 and p.success_rate==.5; assert all(x.requires_human_review for x in s.recommend_improvements("t1","w"))
def test_tenant_isolation():
    s=AutomationIntelligenceService(); s.record_experience("t1","w", "malware", "high"); assert s.repository.list_experiences("t2")==[] and s.similar_experiences("t2","malware","high")==[]
