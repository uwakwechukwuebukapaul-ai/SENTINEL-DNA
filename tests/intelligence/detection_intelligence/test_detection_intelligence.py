from services.intelligence.detection_intelligence import DetectionIntelligenceService
def test_detection_discovery(): assert DetectionIntelligenceService().analyze(investigations="phishing credential")["candidates"]
def test_behavior_analysis(): assert DetectionIntelligenceService().analytics.analyze("failed login")["user_anomalies"]
def test_attack_mapping(): assert "T1566.002" in DetectionIntelligenceService().analyze(investigations="phishing")["candidates"][0]["mitre_techniques"]
def test_coverage_analysis(): assert DetectionIntelligenceService().coverage.analyze(["T1566"],["T1566","T1059"])["visibility_gaps"]==["T1059"]
def test_recommendations(): assert DetectionIntelligenceService().analyze(investigations="malware")["recommendations"]
def test_backward_compatibility(): assert "detection_intelligence_context" in __import__('services.intelligence.investigation.investigation_result',fromlist=['InvestigationResult']).InvestigationResult().to_dict()
