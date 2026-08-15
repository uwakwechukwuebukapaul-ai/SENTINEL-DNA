from .repository import ComplianceMonitoringRepository
from .monitor import ComplianceMonitor
from .drift import DriftDetector
from .evidence import EvidenceTracker
from .audit import AuditIntelligence
class ComplianceMonitoringService:
    def __init__(self,repository=None,audit=None): self.repository=repository or ComplianceMonitoringRepository(); self.monitor=ComplianceMonitor(); self.drift=DriftDetector(); self.evidence=EvidenceTracker(); self.audit_engine=AuditIntelligence(); self.audit=audit
    def record_snapshot(self,tenant_id,framework_id,controls):
        x=self.monitor.snapshot(tenant_id,framework_id,controls); self.repository.save_snapshot(x); return x
    def record_evidence(self,tenant_id,framework_id,control_id,reference,source="",**kwargs):
        x=self.evidence.record(tenant_id,framework_id,control_id,reference,source,**kwargs); self.repository.save_evidence(x); return x
    def detect_drift(self,tenant_id,framework_id,previous,current):
        result=self.drift.compare(tenant_id,framework_id,previous,current)
        for x in result:self.repository.save_drift(x)
        return result
    def historical_posture(self,tenant_id,framework_id):
        return sorted(self.repository.list_snapshots(tenant_id,framework_id),key=lambda x:x.observed_at)
    def compare_snapshots(self,tenant_id,framework_id,previous,current):
        return {"tenant_id":tenant_id,"framework_id":framework_id,"coverage_change":round(current.coverage-previous.coverage,2),"status_change":previous.status!=current.status,"previous":previous.to_dict(),"current":current.to_dict(),"advisory":True}
    def gap_lifecycle(self,tenant_id,framework_id,current_gap_ids):
        prior={x.control_id for x in self.repository.list_drifts(tenant_id,framework_id)}
        current=set(current_gap_ids)
        return {"new":sorted(current-prior),"resolved":sorted(prior-current),"recurring":sorted(current&prior),"deteriorating":sorted(current&prior),"requires_human_review":True}
    def audit_readiness(self,tenant_id,framework_id,controls): return self.evidence.readiness(tenant_id,framework_id,controls,self.repository.list_evidence(tenant_id,framework_id))
    def audit_summary(self,tenant_id,framework_id,controls): return self.audit_engine.summarize(self.audit_readiness(tenant_id,framework_id,controls),self.repository.list_drifts(tenant_id,framework_id))
