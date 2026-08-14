from services.intelligence.threat_hunting import ThreatHuntingService, ThreatHuntingRepository
from services.intelligence.investigation.investigation_result import InvestigationResult

def test_hypothesis_generation_and_mitre_mapping():
    service=ThreatHuntingService("a"); hypothesis=service.create_hypothesis(threat_intelligence=["T1059", "malware"], attack_paths=[], detection_gaps=[], behavior_anomalies=[]); assert "T1059" in hypothesis.mitre_techniques

def test_tenant_isolation():
    repository=ThreatHuntingRepository(); a=ThreatHuntingService("a", repository); b=ThreatHuntingService("b", repository); hypothesis=a.create_hypothesis(); assert b.execute_hunt(a.generate_queries(hypothesis)[0]) is None

def test_hunting_results():
    service=ThreatHuntingService("a"); hypothesis=service.create_hypothesis(behavior_anomalies=["identity"]); query=service.generate_queries(hypothesis)[0]; result=service.execute_hunt(query, "identity activity"); assert result and service.collect_results(query.query_id).query_id == query.query_id

def test_backward_compatibility():
    result=InvestigationResult(); assert result.threat_hunting_context is None and "threat_hunting_context" in result.to_dict()
