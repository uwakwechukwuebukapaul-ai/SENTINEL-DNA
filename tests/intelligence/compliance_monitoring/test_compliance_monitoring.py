from services.intelligence.compliance_governance import Control
from services.intelligence.compliance_monitoring import ComplianceMonitoringService
from services.intelligence.compliance_monitoring.models import EvidenceRecord
from services.intelligence.investigation.investigation_result import InvestigationResult
from datetime import datetime, timezone, timedelta
def test_monitor_drift_evidence_and_readiness():
    s=ComplianceMonitoringService(); old=[Control("c","f","t","C",status="implemented")]; new=[Control("c","f","t","C",status="failed")]; assert s.record_snapshot("t","f",old).coverage==1.0; assert s.detect_drift("t","f",old,new)[0].severity=="high"; s.record_evidence("t","f","c","ref"); assert s.audit_readiness("t","f",new).readiness_score==1.0
def test_tenant_isolation():
    s=ComplianceMonitoringService(); s.record_evidence("t1","f","c","r"); assert s.repository.list_evidence("t2")==[] and s.audit_readiness("t2","f",[]).evidence_count==0

def test_evidence_validity_availability_freshness_and_expiration():
    s=ComplianceMonitoringService(); old=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat(); expired=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
    s.record_evidence("t","f","valid","v",expires_at=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat())
    s.record_evidence("t","f","invalid","i",valid=False)
    s.record_evidence("t","f","unavailable","u",available=False)
    s.record_evidence("t","f","expired","e",expires_at=expired)
    result=s.audit_readiness("t","f",[type("C",(),{"control_id":x})() for x in ("valid","invalid","unavailable","expired")])
    assert result.covered_controls==1 and result.completeness_score==.25 and result.availability_score==.75 and result.freshness_score==.25

def test_historical_posture_and_snapshot_comparison():
    s=ComplianceMonitoringService(); controls=[type("C",(),{"control_id":"c","status":"implemented"})()]; first=s.record_snapshot("t","f",controls); controls[0].status="failed"; second=s.record_snapshot("t","f",controls)
    assert s.historical_posture("t","f")==[first,second] and s.compare_snapshots("t","f",first,second)["coverage_change"]==-1.0

def test_gap_lifecycle_and_advisory_recommendations():
    s=ComplianceMonitoringService(); old=[type("C",(),{"control_id":"c","status":"implemented"})()]; new=[type("C",(),{"control_id":"c","status":"failed"})()]; s.detect_drift("t","f",old,new)
    lifecycle=s.gap_lifecycle("t","f",["c","new"]); summary=s.audit_summary("t","f",[type("C",(),{"control_id":"new"})()])
    assert lifecycle["recurring"]==["c"] and lifecycle["new"]==["new"] and lifecycle["deteriorating"]==["c"] and lifecycle["requires_human_review"]
    assert summary["advisory"] and summary["recommendations"][0]["requires_human_review"]

def test_investigation_result_compliance_monitoring_backward_compatibility():
    result=InvestigationResult(compliance_monitoring_context={"advisory":True})
    assert result.to_dict()["compliance_monitoring_context"]=={"advisory":True}
