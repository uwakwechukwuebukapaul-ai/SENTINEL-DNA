from services.intelligence.detection_platform.detection_intelligence_service import DetectionIntelligenceService
from services.intelligence.detection_platform.coverage_intelligence_service import CoverageIntelligenceService
from services.intelligence.detection_platform.detection_quality_service import DetectionQualityService
from services.intelligence.detection_platform.detection_gap_analysis_service import DetectionGapAnalysisService
def test_services_are_deterministic_tenant_scoped_and_insufficient_safe():
    for service,key in ((DetectionIntelligenceService(),'intelligence'),(CoverageIntelligenceService(),'coverage'),(DetectionQualityService(),'quality'),(DetectionGapAnalysisService(),'gaps')):
        a=service.derive('a')[key]; b=service.derive('a')[key]; c=service.derive('b')[key]
        ident=next(k for k in a if k.endswith('_id')); assert a[ident]==b[ident] and a[ident]!=c[ident]; assert a['advisory_only']
def test_gap_analysis_preserves_review_boundary():
    value=DetectionGapAnalysisService().derive('t')['gaps']; assert 'human analyst review required' in value['analyst_review_priorities']; assert 'insufficient' in value['evidence_strength']
