from services.intelligence.compliance_governance import Control
from services.intelligence.compliance_monitoring import ComplianceMonitoringService
def test_monitor_drift_evidence_and_readiness():
    s=ComplianceMonitoringService(); old=[Control("c","f","t","C",status="implemented")]; new=[Control("c","f","t","C",status="failed")]; assert s.record_snapshot("t","f",old).coverage==1.0; assert s.detect_drift("t","f",old,new)[0].severity=="high"; s.record_evidence("t","f","c","ref"); assert s.audit_readiness("t","f",new).readiness_score==1.0
def test_tenant_isolation():
    s=ComplianceMonitoringService(); s.record_evidence("t1","f","c","r"); assert s.repository.list_evidence("t2")==[] and s.audit_readiness("t2","f",[]).evidence_count==0
