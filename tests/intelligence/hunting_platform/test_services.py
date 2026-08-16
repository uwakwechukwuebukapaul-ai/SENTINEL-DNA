from services.intelligence.hunting_platform.hunting_intelligence_service import HuntingIntelligenceService
from services.intelligence.hunting_platform.hunt_prioritization_service import HuntPrioritizationService
from services.intelligence.hunting_platform.hunt_effectiveness_service import HuntEffectivenessService
from services.intelligence.hunting_platform.hunt_gap_analysis_service import HuntGapAnalysisService
def test_hunting_services_are_deterministic_and_insufficient_safe():
    for service,key in ((HuntingIntelligenceService(),'intelligence'),(HuntPrioritizationService(),'prioritization'),(HuntEffectivenessService(),'effectiveness'),(HuntGapAnalysisService(),'gaps')):
        a=service.derive('a')[key]; b=service.derive('a')[key]; c=service.derive('b')[key]; ident=next(k for k in a if k.endswith('_id')); assert a[ident]==b[ident] and a[ident]!=c[ident]; assert a['advisory_only']
def test_effectiveness_uses_association_language():
    v=HuntEffectivenessService().derive('t')['effectiveness']; assert 'insufficient_history' in v['trend_interpretation']
