from services.intelligence.investigation_platform.evidence_reasoning_service import EvidenceReasoningService
from services.intelligence.investigation_platform.threat_assessment_service import ThreatAssessmentService
from services.intelligence.investigation_platform.investigation_planning_service import InvestigationPlanningService
from services.intelligence.investigation_platform.investigation_summary_service import InvestigationSummaryService
def test_investigation_services_are_deterministic_and_advisory():
    for service,key in ((EvidenceReasoningService(),'reasoning'),(ThreatAssessmentService(),'assessment'),(InvestigationPlanningService(),'plan'),(InvestigationSummaryService(),'summary')):
        a=service.derive('a','c')[key];b=service.derive('a','c')[key];c=service.derive('b','c')[key];ident=next(k for k in a if k.endswith('_id'));assert a[ident]==b[ident] and a[ident]!=c[ident];assert a['advisory_only']
