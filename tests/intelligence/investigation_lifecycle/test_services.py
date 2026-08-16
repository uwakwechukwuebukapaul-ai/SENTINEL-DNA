from services.intelligence.investigation_lifecycle.lifecycle_intelligence_service import LifecycleIntelligenceService
from services.intelligence.investigation_lifecycle.investigation_progress_service import InvestigationProgressService
from services.intelligence.investigation_lifecycle.investigation_quality_service import InvestigationQualityService
from services.intelligence.investigation_lifecycle.analyst_workflow_service import AnalystWorkflowService
from services.intelligence.investigation_lifecycle.investigation_metrics_service import InvestigationMetricsService
def test_lifecycle_services_are_deterministic_and_advisory():
    for service,key in ((LifecycleIntelligenceService(),'lifecycle'),(InvestigationProgressService(),'progress'),(InvestigationQualityService(),'quality'),(AnalystWorkflowService(),'workflow')):
        a=service.derive('a','c')[key];b=service.derive('a','c')[key];c=service.derive('b','c')[key];ident=next(k for k in a if k.endswith('_id'));assert a[ident]==b[ident] and a[ident]!=c[ident];assert a['advisory_only']
def test_metrics_explicitly_report_insufficient_history():
    assert InvestigationMetricsService().derive('t')['metrics']['lifecycle_duration_interpretation']=='insufficient_history'
