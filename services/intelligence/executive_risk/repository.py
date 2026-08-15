class ExecutiveRiskRepository:
    def __init__(self): self.assets={}; self.assessments={}; self.findings={}
    def save_asset(self,x): self.assets[(x.tenant_id,x.asset_id)]=x; return x
    def get_asset(self,i,t): return self.assets.get((t,i))
    def list_assets(self,t): return [x for (tenant,_),x in self.assets.items() if tenant==t]
    def save_assessment(self,x): self.assessments[(x.tenant_id,x.assessment_id)]=x; return x
    def save_finding(self,x): self.findings[(x.tenant_id,x.finding_id)]=x; return x
    def list_findings(self,t): return [x for (tenant,_),x in self.findings.items() if tenant==t]
