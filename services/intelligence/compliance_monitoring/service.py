from .repository import ComplianceMonitoringRepository
from .monitor import ComplianceMonitor
from .drift import DriftDetector
from .evidence import EvidenceTracker
from .audit import AuditIntelligence
class ComplianceMonitoringService:
    def __init__(self,repository=None,audit=None): self.repository=repository or ComplianceMonitoringRepository(); self.monitor=ComplianceMonitor(); self.drift=DriftDetector(); self.evidence=EvidenceTracker(); self.audit_engine=AuditIntelligence(); self.audit=audit
    def record_snapshot(self,tenant_id,framework_id,controls):
        x=self.monitor.snapshot(tenant_id,framework_id,controls); self.repository.save_snapshot(x); return x
    def record_evidence(self,tenant_id,framework_id,control_id,reference,source=""):
        x=self.evidence.record(tenant_id,framework_id,control_id,reference,source); self.repository.save_evidence(x); return x
    def detect_drift(self,tenant_id,framework_id,previous,current):
        result=self.drift.compare(tenant_id,framework_id,previous,current)
        for x in result:self.repository.save_drift(x)
        return result
    def audit_readiness(self,tenant_id,framework_id,controls): return self.evidence.readiness(tenant_id,framework_id,controls,self.repository.list_evidence(tenant_id,framework_id))
    def audit_summary(self,tenant_id,framework_id,controls): return self.audit_engine.summarize(self.audit_readiness(tenant_id,framework_id,controls),self.repository.list_drifts(tenant_id,framework_id))
