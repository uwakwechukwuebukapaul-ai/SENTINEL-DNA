from services.intelligence.security_posture import SecurityPostureRepository, SecurityPostureService
from services.intelligence.investigation.investigation_result import InvestigationResult

def signals(value=80): return {domain: value for domain in ("detection_coverage", "vulnerability_exposure", "attack_surface_risk", "compliance_posture", "incident_trends", "response_capability")}

def test_posture_calculation_and_scoring_accuracy():
    posture=SecurityPostureService("a").calculate_posture(signals()); assert posture.overall_score == 80 and len(posture.domain_scores) == 6

def test_recommendations():
    service=SecurityPostureService("a"); service.calculate_posture({"detection_coverage": 20}); recommendations=service.generate_recommendations(); assert recommendations and recommendations[0].advisory_only

def test_tenant_isolation():
    repository=SecurityPostureRepository(); SecurityPostureService("a", repository).calculate_posture(signals()); assert SecurityPostureService("b", repository).generate_recommendations() == []

def test_backward_compatibility():
    result=InvestigationResult(); assert result.security_posture_context is None and "security_posture_context" in result.to_dict()
