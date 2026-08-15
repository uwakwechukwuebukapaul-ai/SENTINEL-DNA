class ComplianceMonitoringRepository:
    def __init__(self): self.snapshots={}; self.evidence={}; self.drifts={}
    def save_snapshot(self,x): self.snapshots[(x.tenant_id,x.snapshot_id)]=x; return x
    def list_snapshots(self,t,framework_id=None): return [x for (tenant,_),x in self.snapshots.items() if tenant==t and (framework_id is None or x.framework_id==framework_id)]
    def save_evidence(self,x): self.evidence[(x.tenant_id,x.evidence_id)]=x; return x
    def list_evidence(self,t,f=None): return [x for (tenant,_),x in self.evidence.items() if tenant==t and (f is None or x.framework_id==f)]
    def save_drift(self,x): self.drifts[(x.tenant_id,x.drift_id)]=x; return x
    def list_drifts(self,t,f=None): return [x for (tenant,_),x in self.drifts.items() if tenant==t and (f is None or x.framework_id==f)]
