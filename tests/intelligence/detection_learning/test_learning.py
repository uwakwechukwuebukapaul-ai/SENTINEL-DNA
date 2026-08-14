from services.intelligence.detection_learning import DetectionLearningService
def svc():
 s=DetectionLearningService(); s.record_feedback(tenant_id="t",detection_id="d",analyst_verdict="true_positive",true_positive=True); s.record_feedback(tenant_id="t",detection_id="d",analyst_verdict="false_positive",false_positive=True,tuning_notes="tune"); return s
def test_feedback_storage(): assert len(svc().repository.list_feedback("t"))==2
def test_detection_metrics(): assert svc().analyze("t")["metrics"]["precision"]==.5
def test_optimizer(): assert svc().analyze("t")["recommendations"]
def test_learning_cycle(): assert svc().analyze("t")["automatic_changes"] is False
def test_backward_compatibility(): assert "detection_learning_context" in __import__('services.intelligence.investigation.investigation_result',fromlist=['InvestigationResult']).InvestigationResult().to_dict()
