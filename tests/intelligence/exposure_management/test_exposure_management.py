from services.intelligence.exposure_management import ExposureManagementService, ExposureRepository
from services.intelligence.investigation.investigation_result import InvestigationResult

def test_exposure_scoring():
    exposure=ExposureManagementService("a").analyze_exposure("asset-1", asset_criticality="critical", vulnerability_severity="critical", exploit_likelihood=1, attack_path_reachability=1, threat_activity=1, compliance_impact=1, business_impact="critical")
    assert exposure.score >= 80 and exposure.severity == "critical"

def test_prioritization_and_recommendations():
    service=ExposureManagementService("a"); service.analyze_exposure("asset-1", asset_criticality="critical", vulnerability_severity="high", business_impact="high"); assert service.prioritize_risk()[0].priority in {"P1", "P2"}; assert service.generate_recommendations()[0].advisory_only

def test_tenant_isolation():
    repository=ExposureRepository(); ExposureManagementService("a", repository).analyze_exposure("asset-1"); assert ExposureManagementService("b", repository).prioritize_risk() == []

def test_backward_compatibility():
    result=InvestigationResult(); assert result.exposure_management_context is None and "exposure_management_context" in result.to_dict()
